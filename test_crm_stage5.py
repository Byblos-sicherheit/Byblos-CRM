"""Tests für CRM Stufe 5 (Rollen und Freigaben). Abnahme: Rollen- und Freigabeprüfung mit Testkonten."""
import ast
import re
from pathlib import Path

import pytest

import crm_stage5 as s5


def app_sections():
    """SECTIONS-Dict aus app.py lesen, ohne die Streamlit-App zu starten."""
    src = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    start = src.index("SECTIONS = {", src.index("def sidebar"))
    end = src.index("\n    }\n", start) + len("\n    }")
    return ast.literal_eval(src[start + len("SECTIONS = "):end].strip())


SECTIONS = app_sections()
SENSITIVE = ["Lohnabrechnung", "Personalakte", "Bank/DATEV", "UStVA", "Benutzer/Rechte", "Benutzer & Rollen",
             "Export/Backup", "Rollenmatrix", "DSGVO-Center", "Darlehen", "Lohnsteuer-Export"]

# Testkonten: (Rolle wie in users.role gespeichert, Seiten erlaubt, Seiten verboten)
ACCOUNTS = [
    ("Admin", ["Lohnabrechnung", "Benutzer/Rechte", "Rollenmatrix", "Export/Backup"], []),
    ("Buchhaltung", ["Rechnungen", "Lohnabrechnung", "Bank/DATEV", "UStVA", "Kunden"],
     ["Benutzer/Rechte", "Personalakte", "Einsatzplanung", "Rollenmatrix", "Export/Backup"]),
    ("Einsatzleitung", ["Einsatzplanung", "Dienstplan", "Personalakte", "Objekte", "Qualifikationen"],
     ["Lohnabrechnung", "Bank/DATEV", "Benutzer/Rechte", "UStVA"]),
    ("Vertrieb", ["Kunden", "Leads", "Posteingang", "Angebote"],
     ["Lohnabrechnung", "Personalakte", "Bank/DATEV", "Benutzer/Rechte", "Rechnungen"]),
    ("Mitarbeiter", ["Mein Bereich", "GPS-Stempeluhr"], SENSITIVE + ["Kunden", "Rechnungen", "Dashboard"]),
    ("Kunde/Portal", [], SENSITIVE + ["Kunden", "Mein Bereich"]),
]


def test_sections_parsed_from_app():
    assert "👥 CRM" in SECTIONS and len(SECTIONS) > 40


@pytest.mark.parametrize("role,allowed,denied", ACCOUNTS)
def test_test_accounts_see_only_their_pages(role, allowed, denied):
    for page in allowed:
        assert s5.can_access_page(role, SECTIONS, page), f"{role} sollte {page} sehen"
    for page in denied:
        assert not s5.can_access_page(role, SECTIONS, page), f"{role} darf {page} nicht sehen"


@pytest.mark.parametrize("raw,expected", [
    ("Admin", "Inhaber/Admin"), ("admin", "Inhaber/Admin"), ("Inhaber/Admin", "Inhaber/Admin"),
    ("Büro", "Buchhaltung"), ("Buchhalter", "Buchhaltung"), ("Disposition", "Einsatzleitung"),
    ("manager", "Einsatzleitung"), ("Lesen", "Mitarbeiter"), ("readonly", "Mitarbeiter"),
    ("", "Mitarbeiter"), (None, "Mitarbeiter"), ("Hacker", "Mitarbeiter"), ("  ADMIN ", "Inhaber/Admin"),
])
def test_legacy_and_unknown_roles_mapped(raw, expected):
    assert s5.canonical_role(raw) == expected


def test_unknown_role_gets_least_privilege():
    assert set(s5.allowed_sections("Hacker", SECTIONS)) == set(s5.allowed_sections("Mitarbeiter", SECTIONS))


def test_unlisted_sections_are_admin_only():
    unlisted = [s for s in SECTIONS if s not in s5.SECTION_ROLES]
    assert unlisted, "es gibt Admin-Bereiche"
    for role in s5.ROLES[1:]:
        assert not any(s5.can_access_section(role, s) for s in unlisted)


def test_section_roles_only_reference_existing_sections_and_roles():
    assert set(s5.SECTION_ROLES) <= set(SECTIONS)
    assert set().union(*s5.SECTION_ROLES.values()) <= set(s5.ROLES)


def test_admin_sees_everything():
    assert s5.allowed_sections("Admin", SECTIONS) == SECTIONS


def test_app_guards_navigation_twice():
    src = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
    assert "crm_stage5.allowed_sections(role, SECTIONS)" in src
    assert re.search(r"_nav_override.*\n.*\n.*_allowed_pages", src), "Prüfung nach Schnellaktion/Favorit fehlt"
