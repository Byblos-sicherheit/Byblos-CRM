"""Tests für CRM Stufe 1 (Sparten, 80-km-Radius, Dublettenprüfung). Nur synthetische Testdaten."""
import sqlite3

import pytest

import crm_stage1 as s1

BASE_SCHEMA = """CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT, customer_no TEXT UNIQUE, company TEXT NOT NULL,
    contact_person TEXT, email TEXT, phone TEXT, street TEXT, zip_city TEXT,
    country TEXT DEFAULT 'Deutschland', notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""

# 10 synthetische Datensätze: (Firma, E-Mail, Website, Straße, PLZ Ort, Sparte)
TEN = [
    ("Muster Logistik GmbH", "info@muster-logistik.example", "", "Hafenweg 1", "38440 Wolfsburg", "Sicherheit"),
    ("Beispiel Lager AG", "kontakt@beispiel-lager.example", "", "Industriestr. 5", "38518 Gifhorn", "Sicherheit"),
    ("Testbau GmbH & Co. KG", "", "www.testbau.example", "Bauhof 3", "38100 Braunschweig", "Sicherheit"),
    ("Solarpark Nord UG", "betrieb@solarpark-nord.example", "", "Feldweg 9", "29378 Wittingen", "Sicherheit"),
    ("Hausverwaltung Sonne", "verwaltung@hv-sonne.example", "", "Lindenallee 12", "38448 Wolfsburg", "Facility"),
    ("Praxis am Markt", "praxis@gmail.com", "", "Markt 2", "38459 Bahrdorf", "Facility"),
    ("Kita Regenbogen e.V.", "kita@regenbogen.example", "", "Schulweg 4", "38474 Tülau", "Facility"),
    ("Autohaus Ost OHG", "service@autohaus-ost.example", "", "Ringstraße 20", "38350 Helmstedt", "Facility"),
    ("Gewerbepark West", "", "gewerbepark-west.example", "Am Park 1", "38446 Wolfsburg", "Beide"),
    ("Privatkunde Meier", "meier@web.de", "", "Dorfstr. 7", "38474 Tülau", "Unbekannt"),
]


@pytest.fixture
def db():
    c = sqlite3.connect(":memory:")
    c.execute(BASE_SCHEMA)
    s1.ensure_columns(c)
    yield c
    c.close()


def insert(c, company, email="", website="", street="", zip_city="", sparte="Unbekannt"):
    c.execute("INSERT INTO customers(company,email,website,street,zip_city,sparte) VALUES(?,?,?,?,?,?)",
              (company, email, website, street, zip_city, sparte))


def test_ensure_columns_is_idempotent(db):
    s1.ensure_columns(db)
    cols = {r[1] for r in db.execute("PRAGMA table_info(customers)")}
    assert set(s1.NEW_COLUMNS) <= cols


def test_existing_rows_default_to_unbekannt():
    c = sqlite3.connect(":memory:")
    c.execute(BASE_SCHEMA)
    c.execute("INSERT INTO customers(company) VALUES('Altkunde')")
    s1.ensure_columns(c)
    assert c.execute("SELECT sparte FROM customers").fetchone()[0] == "Unbekannt"


def test_ten_records_without_duplicates_and_separate_sparten(db):
    for rec in TEN:
        assert s1.find_duplicates(db, *rec[:5]) == [], rec[0]
        insert(db, *rec)
    assert db.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 10
    counts = dict(db.execute("SELECT sparte, COUNT(*) FROM customers GROUP BY sparte"))
    assert counts == {"Sicherheit": 4, "Facility": 4, "Beide": 1, "Unbekannt": 1}


@pytest.mark.parametrize("candidate,reason", [
    (("MUSTER LOGISTIK", "", "", "", ""), "Firmenname"),
    (("Muster-Logistik GmbH & Co. KG", "", "", "", ""), "Firmenname"),
    (("Andere Firma", "INFO@muster-logistik.example", "", "", ""), "E-Mail"),
    (("Andere Firma", "chef@muster-logistik.example", "", "", ""), "Domain"),
    (("Andere Firma", "", "https://www.testbau.example/kontakt", "", ""), "Domain"),
    (("Andere Firma", "", "", "Industriestraße 5", "38518 Gifhorn"), "Adresse"),
])
def test_duplicates_detected(db, candidate, reason):
    for rec in TEN:
        insert(db, *rec)
    hits = s1.find_duplicates(db, *candidate)
    assert hits and reason in hits[0][2]


def test_freemail_domain_is_not_a_duplicate(db):
    for rec in TEN:
        insert(db, *rec)
    assert s1.find_duplicates(db, "Ganz Neu", "jemand@gmail.com") == []


def test_exclude_id_allows_editing_same_record(db):
    insert(db, *TEN[0])
    cid = db.execute("SELECT id FROM customers").fetchone()[0]
    assert s1.find_duplicates(db, TEN[0][0], exclude_id=cid) == []


@pytest.mark.parametrize("lat,lon,expected", [
    (52.4227, 10.7865, "im Radius"),      # Wolfsburg, ~18 km
    (52.2689, 10.5268, "im Radius"),      # Braunschweig, ~42 km
    (52.574, 9.770, "Grenzfall – Straßenentfernung prüfen"),  # gleiche Breite, ~75 km West
    (53.5511, 9.9937, "außerhalb"),       # Hamburg, ~125 km
])
def test_radius_status(lat, lon, expected):
    assert s1.radius_status(s1.distance_from_base(lat, lon)) == expected


def test_radius_boundaries():
    assert s1.radius_status(None) == "unbekannt"
    assert s1.radius_status(70.0) == "im Radius"
    assert s1.radius_status(70.1).startswith("Grenzfall")
    assert s1.radius_status(80.0).startswith("Grenzfall")
    assert s1.radius_status(80.1) == "außerhalb"


def test_haversine_known_distance():
    # Hamburg – Hannover Luftlinie ca. 132 km
    assert 125 < s1.haversine_km(53.5511, 9.9937, 52.3759, 9.7320) < 140


@pytest.mark.parametrize("values,expected", [
    ([], "SD-0001"),
    (["SD-001", "SD-002", "SD-0004", "SD-0005"], "SD-0006"),  # gemischte Altnummern: Textsortierung lieferte SD-0003
    (["SD-0003", "SD-002"], "SD-0004"),
    (["SD-abc", None, ""], "SD-0001"),
])
def test_next_number_uses_numeric_maximum(values, expected):
    from numbering import next_number_from
    assert next_number_from(values, "SD-") == expected


def test_geocode_empty_address_returns_none():
    assert s1.geocode("", "") is None


def test_api_rejects_duplicate_and_invalid_sparte(tmp_path, monkeypatch):
    fastapi_testclient = pytest.importorskip("fastapi.testclient")
    import api_server

    db_file = tmp_path / "api.db"
    c = sqlite3.connect(db_file)
    c.execute(BASE_SCHEMA)
    c.execute("CREATE TABLE api_keys (key_name TEXT, api_key TEXT, permissions TEXT, active INTEGER, last_used TEXT)")
    c.execute("INSERT INTO api_keys VALUES ('test', 'test-key', 'all', 1, NULL)")
    c.commit()
    c.close()
    monkeypatch.setattr(api_server, "DB_PATH", db_file)
    client = fastapi_testclient.TestClient(api_server.app)
    headers = {"X-API-Key": "test-key"}
    body = {"company": "Muster Logistik GmbH", "email": "info@muster-logistik.example", "sparte": "Sicherheit"}

    assert client.post("/api/v1/customers", json=body, headers=headers).status_code == 201
    dup = client.post("/api/v1/customers", json={**body, "company": "Muster Logistik"}, headers=headers)
    assert dup.status_code == 409
    assert client.post("/api/v1/customers", json={"company": "Neu", "sparte": "Glasreinigung"}, headers=headers).status_code == 422
