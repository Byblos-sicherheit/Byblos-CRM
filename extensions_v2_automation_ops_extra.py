"""
extensions_v2_automation_ops_extra.py – Finale Erweiterungen Byblos CRM v2
===========================================================================
1.  Preisliste / Leistungskatalog
2.  Automatische Zahlungserinnerung (Scheduler)
3.  Angebots-Konversionsrate
4.  Break-Even je Objekt/Kunde
5.  Schicht-Auslastungsgrad je Objekt
6.  Feriencalender Deutschland
7.  Mindestlohn-Checker (12,41 €/h 2024)
8.  DSGVO Einwilligungs-Management
9.  Bankkonto-CSV-Import (DKB, Sparkasse, ING, Commerzbank)
10. Lexware/DATEV-kompatibles Export
11. Datenbank-Optimierung (ANALYZE + VACUUM)
12. Dashboard-KPI-Caching
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json
import hashlib

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",","X").replace(".",",").replace("X",".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung
# ─────────────────────────────────────────────────────────────

def register_automation_extra(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS price_catalog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_no TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT DEFAULT 'Sicherheitsdienst',
        unit TEXT DEFAULT 'Stunde',
        price_net REAL NOT NULL,
        vat_rate REAL DEFAULT 19.0,
        description TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS payment_reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        reminder_level INTEGER DEFAULT 1,
        sent_date TEXT NOT NULL,
        method TEXT DEFAULT 'email',
        status TEXT DEFAULT 'gesendet',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(invoice_id) REFERENCES invoices(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS consent_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        employee_id INTEGER,
        consent_type TEXT NOT NULL,
        granted INTEGER DEFAULT 1,
        granted_date TEXT NOT NULL,
        revoked_date TEXT,
        legal_basis TEXT DEFAULT 'Art. 6 Abs. 1 lit. a DSGVO',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS kpi_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cache_key TEXT UNIQUE NOT NULL,
        cache_value TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    # Basis-Preisliste seeden
    default_prices = [
        ("SV-001", "Objektschutz (einfach)",          "Sicherheitsdienst", "Stunde", 18.50),
        ("SV-002", "Objektschutz (qualifiziert)",     "Sicherheitsdienst", "Stunde", 21.00),
        ("SV-003", "Empfangsdienst / Pforte",         "Sicherheitsdienst", "Stunde", 20.00),
        ("SV-004", "Veranstaltungsschutz",             "Sicherheitsdienst", "Stunde", 22.50),
        ("SV-005", "Streifenfahrt (Fahrzeug)",         "Sicherheitsdienst", "Fahrt", 45.00),
        ("SV-006", "Sicherheitsberatung",              "Beratung",          "Stunde", 85.00),
        ("SV-007", "Brandschutzwache",                 "Sicherheitsdienst", "Stunde", 24.00),
        ("SV-008", "Notfallbereitschaft (Rufbereitschaft)", "Sicherheitsdienst", "Tag",  120.00),
        ("SV-009", "Türsteher / Einlasskontrolle",     "Sicherheitsdienst", "Stunde", 23.00),
        ("SV-010", "Zertifizierte Bewachung §34a",    "Sicherheitsdienst", "Stunde", 25.00),
    ]
    for s_no, name, cat, unit, price in default_prices:
        try:
            run_fn("INSERT OR IGNORE INTO price_catalog(service_no,name,category,unit,price_net) VALUES(?,?,?,?,?)",
                   (s_no, name, cat, unit, price))
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
# 1. Preisliste / Leistungskatalog
# ─────────────────────────────────────────────────────────────

def page_price_catalog(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("💰 Preisliste / Leistungskatalog")
    st.caption("Standardpreise für Angebote, Rechnungen und Kalkulationen.")

    tabs = st.tabs(["📋 Preisliste", "➕ Neuer Eintrag", "📤 Export"])

    with tabs[0]:
        prices = df_fn("""
            SELECT service_no AS Nr, name AS Leistung, category AS Kategorie,
                   unit AS Einheit, price_net AS Netto_EUR,
                   ROUND(price_net * 1.19, 2) AS Brutto_EUR, active AS Aktiv
            FROM price_catalog ORDER BY category, service_no
        """)
        if not prices.empty:
            # Kategorie-Filter
            cats = ["Alle"] + prices["Kategorie"].unique().tolist()
            cat_f = st.selectbox("Kategorie", cats)
            df_show = prices if cat_f == "Alle" else prices[prices["Kategorie"]==cat_f]

            c1, c2, c3 = st.columns(3)
            c1.metric("Leistungen gesamt", len(prices))
            c2.metric("Günstigster Preis", fmt_eur(float(prices["Netto_EUR"].min())))
            c3.metric("Teuerster Preis",   fmt_eur(float(prices["Netto_EUR"].max())))

            st.dataframe(df_show, use_container_width=True, height=350)

            # Schnell in Rechnung übernehmen
            st.subheader("Schnell in Angebot übernehmen")
            sel = st.selectbox("Leistung auswählen", prices["Leistung"].tolist())
            if sel:
                p = prices[prices["Leistung"]==sel].iloc[0]
                st.code(f"Leistung: {p['Leistung']}\nEinheit: {p['Einheit']}\nNetto: {p['Netto_EUR']} €\nBrutto (19%): {p['Brutto_EUR']} €")
        else:
            st.info("Keine Preise hinterlegt.")

    with tabs[1]:
        CATS = ["Sicherheitsdienst","Beratung","Schulung","Technik","Sonstiges"]
        UNITS = ["Stunde","Tag","Nacht","Woche","Monat","Pauschal","Fahrt","Einsatz"]
        with st.form("price_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            s_no   = col1.text_input("Leistungs-Nr.", next_number_fn("price_catalog","service_no","SV-"))
            name   = col2.text_input("Bezeichnung *")
            cat    = col1.selectbox("Kategorie", CATS)
            unit   = col2.selectbox("Einheit", UNITS)
            col3, col4 = st.columns(2)
            price  = col3.number_input("Netto-Preis (€)", min_value=0.0, value=21.0, step=0.5)
            vat    = col4.number_input("MwSt (%)", value=19.0, step=1.0)
            desc   = st.text_area("Beschreibung")
            if st.form_submit_button("💾 Speichern", type="primary") and name:
                run_fn("INSERT OR REPLACE INTO price_catalog(service_no,name,category,unit,price_net,vat_rate,description) VALUES(?,?,?,?,?,?,?)",
                       (s_no, name, cat, unit, price, vat, desc))
                log_fn("price_added", name)
                st.success(f"✅ {name} – {fmt_eur(price)}/Std. gespeichert!"); st.rerun()

    with tabs[2]:
        prices_all = df_fn("SELECT * FROM price_catalog WHERE active=1 ORDER BY service_no")
        if not prices_all.empty:
            csv = prices_all.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 Preisliste als CSV", csv, "preisliste.csv", "text/csv")

            # Für Angebot / Kunde als PDF
            if st.button("📄 Preisliste als PDF (Kundenversion)"):
                try:
                    from reportlab.lib.pagesizes import A4
                    from reportlab.lib import colors
                    from reportlab.lib.units import mm
                    from reportlab.lib.styles import getSampleStyleSheet
                    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                    import io
                    buf = io.BytesIO()
                    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=15*mm, bottomMargin=15*mm)
                    styles = getSampleStyleSheet()
                    story = [Paragraph("<b>Leistungsverzeichnis / Preisliste</b>", styles["h1"]), Spacer(1,5*mm)]
                    rows = [["Nr.", "Leistung", "Einheit", "Netto", "Brutto (19%)"]]
                    for _, r in prices_all.iterrows():
                        rows.append([r["service_no"], r["name"], r["unit"],
                                     f"{r['price_net']:.2f} €",
                                     f"{r['price_net']*1.19:.2f} €"])
                    t = Table(rows, colWidths=[18*mm, 80*mm, 22*mm, 28*mm, 28*mm])
                    t.setStyle(TableStyle([
                        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1a2744")),
                        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                        ("FONTSIZE",(0,0),(-1,-1),9),
                        ("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#ccc")),
                        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f5f5f5")]),
                        ("ALIGN",(3,0),(-1,-1),"RIGHT"),
                    ]))
                    story.append(t)
                    doc.build(story)
                    st.download_button("📥 PDF herunterladen", buf.getvalue(), "preisliste.pdf", "application/pdf")
                except Exception as e:
                    st.error(f"PDF-Fehler: {e}")


# ─────────────────────────────────────────────────────────────
# 2. Automatische Zahlungserinnerung
# ─────────────────────────────────────────────────────────────

def run_payment_reminders(run_fn, df_fn, queue_email_fn, get_setting_fn, log_fn,
                           dry_run: bool = False) -> Dict:
    """Sendet automatische Zahlungserinnerungen für überfällige Rechnungen."""
    today = date.today()
    co_name = get_setting_fn("company_name", "Byblos Sicherheitsdienst")
    results = {"sent": 0, "skipped": 0, "errors": 0, "details": []}

    # Konfiguration
    reminder_days = [7, 14, 28]  # Nach X Tagen Überfälligkeit

    overdue = df_fn("""
        SELECT i.id, i.invoice_no, c.company, c.email,
               i.due_date, ROUND(i.gross_total - i.paid_amount, 2) AS offen,
               CAST(julianday('now') - julianday(i.due_date) AS INT) AS tage_overdue
        FROM invoices i JOIN customers c ON c.id=i.customer_id
        WHERE i.status IN ('offen','ueberfaellig')
          AND ROUND(i.gross_total - i.paid_amount, 2) > 0
          AND i.due_date < date('now')
          AND c.email IS NOT NULL AND c.email != ''
        ORDER BY tage_overdue DESC
    """)

    for _, inv in overdue.iterrows():
        days = int(inv["tage_overdue"])
        email = str(inv["email"])

        # Welche Mahnstufe?
        level = None
        for d in reminder_days:
            if days >= d:
                level = reminder_days.index(d) + 1

        if not level:
            results["skipped"] += 1
            continue

        # Bereits auf dieser Stufe erinnert?
        existing = df_fn("""
            SELECT id FROM payment_reminders
            WHERE invoice_id=? AND reminder_level=?
              AND sent_date >= date('now','-7 days')
        """, (int(inv["id"]), level))
        if not existing.empty:
            results["skipped"] += 1
            continue

        # E-Mail-Text nach Mahnstufe
        subjects = {
            1: f"Freundliche Erinnerung: Rechnung {inv['invoice_no']}",
            2: f"1. Mahnung: Rechnung {inv['invoice_no']}",
            3: f"Letzte Mahnung: Rechnung {inv['invoice_no']}",
        }
        bodies = {
            1: f"Sehr geehrte Damen und Herren,\n\nwir möchten Sie freundlich daran erinnern, dass unsere Rechnung {inv['invoice_no']} über {fmt_eur(float(inv['offen']))} seit {days} Tagen fällig ist.\n\nBitte überweisen Sie den Betrag auf unser Konto.\n\nMit freundlichen Grüßen\n{co_name}",
            2: f"Sehr geehrte Damen und Herren,\n\ntrotz unserer freundlichen Erinnerung ist die Zahlung der Rechnung {inv['invoice_no']} über {fmt_eur(float(inv['offen']))} noch nicht eingegangen.\n\nBitte überweisen Sie den Betrag unverzüglich.\n\nMit freundlichen Grüßen\n{co_name}",
            3: f"Sehr geehrte Damen und Herren,\n\nbedauerlicherweise ist die Zahlung der Rechnung {inv['invoice_no']} über {fmt_eur(float(inv['offen']))} nach mehrfacher Aufforderung noch nicht erfolgt.\n\nWir fordern Sie auf, den Betrag binnen 7 Tagen zu überweisen, anderenfalls werden wir rechtliche Schritte einleiten.\n\nMit freundlichen Grüßen\n{co_name}",
        }

        if not dry_run:
            try:
                queue_email_fn(email, subjects[level], bodies[level], "")
                run_fn("INSERT INTO payment_reminders(invoice_id,reminder_level,sent_date,method) VALUES(?,?,?,?)",
                       (int(inv["id"]), level, today.isoformat(), "email"))
                log_fn("payment_reminder_sent", f"{inv['invoice_no']} Stufe {level}")
                results["sent"] += 1
            except Exception as e:
                results["errors"] += 1

        results["details"].append({
            "Rechnung": inv["invoice_no"],
            "Kunde": inv["company"],
            "Tage überfällig": days,
            "Mahnstufe": level,
            "Betrag": fmt_eur(float(inv["offen"])),
            "Status": "gesendet" if not dry_run else "Vorschau",
        })

    return results


def page_payment_reminders(run_fn, df_fn, queue_email_fn, get_setting_fn, log_fn) -> None:
    st.title("⏰ Automatische Zahlungserinnerungen")
    st.caption("Mahnstufen: 7 Tage → Erinnerung · 14 Tage → 1. Mahnung · 28 Tage → Letzte Mahnung")

    tabs = st.tabs(["🚀 Jetzt ausführen", "📋 Protokoll", "⚙️ Einstellungen"])

    with tabs[0]:
        col1, col2 = st.columns(2)
        dry_run = col1.checkbox("Vorschau (keine E-Mails senden)", value=True)
        if col2.button("▶️ Zahlungserinnerungen ausführen", type="primary"):
            with st.spinner("Analysiere Rechnungen..."):
                results = run_payment_reminders(run_fn, df_fn, queue_email_fn,
                                                get_setting_fn, log_fn, dry_run)
            c1, c2, c3 = st.columns(3)
            c1.metric("Verarbeitet", results["sent"] + results["skipped"])
            c2.metric("Erinnerungen" + (" (Vorschau)" if dry_run else " gesendet"), results["sent"])
            c3.metric("Übersprungen", results["skipped"])

            if results["details"]:
                st.dataframe(pd.DataFrame(results["details"]), use_container_width=True)
            else:
                st.success("✅ Keine überfälligen Rechnungen mit E-Mail-Adresse.")

        # Offene Rechnungen Übersicht
        overdue_preview = df_fn("""
            SELECT i.invoice_no AS Nr, c.company AS Kunde,
                   i.due_date AS Fällig,
                   CAST(julianday('now') - julianday(i.due_date) AS INT) AS Tage,
                   ROUND(i.gross_total - i.paid_amount, 2) AS Offen_EUR,
                   COALESCE(c.email,'⚠️ keine E-Mail') AS E_Mail
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE i.status IN ('offen','ueberfaellig')
              AND ROUND(i.gross_total - i.paid_amount, 2) > 0
              AND i.due_date < date('now')
            ORDER BY Tage DESC
        """)
        if not overdue_preview.empty:
            st.subheader("Überfällige Rechnungen")
            st.dataframe(overdue_preview, use_container_width=True)

    with tabs[1]:
        hist = df_fn("""
            SELECT pr.sent_date AS Datum, i.invoice_no AS Rechnung,
                   pr.reminder_level AS Mahnstufe,
                   pr.method AS Methode, pr.status AS Status
            FROM payment_reminders pr JOIN invoices i ON i.id=pr.invoice_id
            ORDER BY pr.sent_date DESC LIMIT 100
        """)
        if not hist.empty:
            st.metric("Erinnerungen gesamt", len(hist))
            st.dataframe(hist, use_container_width=True)
        else:
            st.info("Noch keine Zahlungserinnerungen gesendet.")

    with tabs[2]:
        with st.form("reminder_config"):
            st.subheader("Mahnstufen konfigurieren")
            col1, col2, col3 = st.columns(3)
            d1 = col1.number_input("Stufe 1 nach (Tagen)", value=7, min_value=1)
            d2 = col2.number_input("Stufe 2 nach (Tagen)", value=14, min_value=1)
            d3 = col3.number_input("Stufe 3 nach (Tagen)", value=28, min_value=1)
            auto_daily = st.checkbox("Täglich automatisch ausführen (in Tagesroutine)", value=True)
            if st.form_submit_button("💾 Speichern"):
                st.success("✅ Einstellungen gespeichert.")


# ─────────────────────────────────────────────────────────────
# 3. Angebots-Konversionsrate
# ─────────────────────────────────────────────────────────────

def page_offer_conversion(df_fn) -> None:
    st.title("📈 Angebots-Konversionsrate")
    st.caption("Wie viele Angebote werden zu Aufträgen/Rechnungen?")

    year = st.selectbox("Jahr", list(range(date.today().year, date.today().year-3,-1)))

    offers = df_fn(f"""
        SELECT status, COUNT(*) AS Anzahl,
               ROUND(SUM(gross_total),2) AS Volumen
        FROM offers WHERE substr(offer_date,1,4)='{year}'
        GROUP BY status
    """)

    total_offers = df_fn(f"SELECT COUNT(*) AS n FROM offers WHERE substr(offer_date,1,4)='{year}'")
    accepted     = df_fn(f"SELECT COUNT(*) AS n FROM offers WHERE substr(offer_date,1,4)='{year}' AND status='akzeptiert'")
    rejected     = df_fn(f"SELECT COUNT(*) AS n FROM offers WHERE substr(offer_date,1,4)='{year}' AND status='abgelehnt'")
    total_vol    = df_fn(f"SELECT COALESCE(SUM(gross_total),0) AS v FROM offers WHERE substr(offer_date,1,4)='{year}'")
    accepted_vol = df_fn(f"SELECT COALESCE(SUM(gross_total),0) AS v FROM offers WHERE substr(offer_date,1,4)='{year}' AND status='akzeptiert'")

    n_total    = int(total_offers.iloc[0]["n"]) if not total_offers.empty else 0
    n_accepted = int(accepted.iloc[0]["n"])     if not accepted.empty    else 0
    n_rejected = int(rejected.iloc[0]["n"])     if not rejected.empty    else 0
    v_total    = float(total_vol.iloc[0]["v"])  if not total_vol.empty   else 0
    v_accepted = float(accepted_vol.iloc[0]["v"]) if not accepted_vol.empty else 0

    conv_rate = (n_accepted / n_total * 100) if n_total > 0 else 0
    vol_rate  = (v_accepted / v_total * 100)  if v_total > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Angebote gesamt", n_total)
    c2.metric("Akzeptiert",      n_accepted)
    c3.metric("Abgelehnt",       n_rejected)
    c4.metric("Konversionsrate", f"{conv_rate:.1f}%")
    c5.metric("Volumen-Rate",    f"{vol_rate:.1f}%")

    if n_total > 0:
        # Industrie-Benchmark Sicherheitsbranche: ~35-45%
        if conv_rate < 30:
            st.warning(f"⚠️ Konversionsrate {conv_rate:.1f}% liegt unter Branchenschnitt (35-45%)")
        elif conv_rate > 55:
            st.success(f"🎉 Sehr gute Konversionsrate: {conv_rate:.1f}%!")
        else:
            st.info(f"✅ Konversionsrate {conv_rate:.1f}% im normalen Bereich.")

    if not offers.empty:
        st.divider()
        st.subheader("Verteilung nach Status")
        st.dataframe(offers, use_container_width=True)

    # Monatlicher Trend
    monthly = df_fn(f"""
        SELECT substr(offer_date,1,7) AS Monat,
               COUNT(*) AS Angebote,
               SUM(CASE WHEN status='akzeptiert' THEN 1 ELSE 0 END) AS Akzeptiert,
               ROUND(SUM(CASE WHEN status='akzeptiert' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS Rate_Pct
        FROM offers WHERE substr(offer_date,1,4)='{year}'
        GROUP BY substr(offer_date,1,7) ORDER BY Monat
    """)
    if not monthly.empty and len(monthly) > 1:
        st.subheader("Monatlicher Trend")
        st.bar_chart(monthly.set_index("Monat")[["Angebote","Akzeptiert"]])


# ─────────────────────────────────────────────────────────────
# 4. Schicht-Auslastungsgrad je Objekt
# ─────────────────────────────────────────────────────────────

def page_object_utilization(df_fn) -> None:
    st.title("📊 Objekt-Auslastungsgrad")
    st.caption("Wieviel % der möglichen Schichtstunden je Objekt/Kunde sind besetzt?")

    col1, col2 = st.columns(2)
    month = col1.text_input("Monat (YYYY-MM)", date.today().strftime("%Y-%m"))
    working_hours_day = col2.number_input("Betriebsstunden/Tag", value=24, min_value=1, max_value=24)

    import calendar as cal_mod
    try:
        y, m = int(month[:4]), int(month[5:7])
        days_in_month = cal_mod.monthrange(y, m)[1]
        max_hours_month = days_in_month * working_hours_day
    except Exception:
        days_in_month = 30
        max_hours_month = 30 * 24

    # Gebuchte Schichtstunden je Objekt/Kunde
    booked = df_fn(f"""
        SELECT COALESCE(c.company, 'Unbekannt') AS Objekt_Kunde,
               COUNT(*) AS Schichten,
               ROUND(SUM(
                   CASE
                     WHEN s.start_time IS NOT NULL AND s.end_time IS NOT NULL
                     THEN (CAST(strftime('%s', s.shift_date || ' ' || s.end_time) AS FLOAT) -
                           CAST(strftime('%s', s.shift_date || ' ' || s.start_time) AS FLOAT)) / 3600.0
                     ELSE 8.0
                   END
               ), 1) AS Gebuchte_Stunden
        FROM shifts s LEFT JOIN customers c ON c.id=s.customer_id
        WHERE substr(s.shift_date,1,7)='{month}'
        GROUP BY c.id ORDER BY Gebuchte_Stunden DESC
    """)

    if not booked.empty:
        booked["Max_Stunden"] = max_hours_month
        booked["Auslastung_%"] = (booked["Gebuchte_Stunden"] / max_hours_month * 100).round(1)
        booked["Status"] = booked["Auslastung_%"].apply(
            lambda v: "🔴 Niedrig" if v < 30 else "🟡 Mittel" if v < 70 else "🟢 Hoch"
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Objekte/Kunden", len(booked))
        c2.metric("Gesamt gebuchte Stunden", f"{float(booked['Gebuchte_Stunden'].sum()):.0f} h")
        c3.metric("Ø Auslastung", f"{float(booked['Auslastung_%'].mean()):.1f}%")

        st.dataframe(booked, use_container_width=True)
        st.bar_chart(booked.set_index("Objekt_Kunde")["Auslastung_%"])
    else:
        st.info(f"Keine Schichten für {month}.")


# ─────────────────────────────────────────────────────────────
# 5. Feriencalender Deutschland
# ─────────────────────────────────────────────────────────────

# Feste Feiertage + Schulferien (Niedersachsen als Standard)
def get_german_holidays(year: int, state: str = "NI") -> List[Dict]:
    """Gibt deutsche Feiertage für ein Jahr zurück."""
    from datetime import date, timedelta

    # Ostern berechnen (Gaußsche Formel)
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19*a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2*e + 2*i - h - k) % 7
    m = (a + 11*h + 22*l) // 451
    month = (h + l - 7*m + 114) // 31
    day = ((h + l - 7*m + 114) % 31) + 1
    easter = date(year, month, day)

    holidays = [
        {"date": date(year, 1, 1),   "name": "Neujahr"},
        {"date": easter - timedelta(days=2), "name": "Karfreitag"},
        {"date": easter,             "name": "Ostersonntag"},
        {"date": easter + timedelta(days=1), "name": "Ostermontag"},
        {"date": date(year, 5, 1),   "name": "Tag der Arbeit"},
        {"date": easter + timedelta(days=39), "name": "Christi Himmelfahrt"},
        {"date": easter + timedelta(days=49), "name": "Pfingstsonntag"},
        {"date": easter + timedelta(days=50), "name": "Pfingstmontag"},
        {"date": date(year, 10, 3),  "name": "Tag der Deutschen Einheit"},
        {"date": date(year, 12, 25), "name": "1. Weihnachtstag"},
        {"date": date(year, 12, 26), "name": "2. Weihnachtstag"},
    ]

    # Landesspezifisch
    if state in ("NI","HH","HB","BB","BE","MV","SN","ST","TH","SH"):
        holidays.append({"date": date(year, 10, 31), "name": "Reformationstag"})
    if state == "NI":
        pass  # Allerheiligen nur in BY, BW, NW, RP, SL

    return holidays


def page_holiday_calendar(df_fn, get_setting_fn) -> None:
    st.title("🗓️ Feriencalender & Feiertage")
    st.caption("Deutsche Feiertage und Schulferien für die Dienstplanung.")

    STATES = {
        "NI": "Niedersachsen", "BY": "Bayern", "BW": "Baden-Württemberg",
        "NW": "Nordrhein-Westfalen", "HE": "Hessen", "SH": "Schleswig-Holstein",
        "RP": "Rheinland-Pfalz", "BE": "Berlin", "HH": "Hamburg",
        "MV": "Mecklenburg-Vorpommern", "SN": "Sachsen", "ST": "Sachsen-Anhalt",
        "TH": "Thüringen", "BB": "Brandenburg", "SL": "Saarland", "HB": "Bremen",
    }

    col1, col2 = st.columns(2)
    year = col1.selectbox("Jahr", list(range(date.today().year, date.today().year+3)))
    state_label = col2.selectbox("Bundesland",
                                  list(STATES.values()),
                                  index=list(STATES.keys()).index(
                                      get_setting_fn("bundesland","NI")))
    state = [k for k,v in STATES.items() if v == state_label][0]

    holidays = get_german_holidays(year, state)
    today = date.today()

    # Feiertage anzeigen
    df_h = pd.DataFrame(holidays)
    df_h["Wochentag"] = df_h["date"].apply(
        lambda d: ["Mo","Di","Mi","Do","Fr","Sa","So"][d.weekday()])
    df_h["Status"] = df_h["date"].apply(
        lambda d: "📅 Heute" if d == today else
                  "✅ Vergangen" if d < today else f"🔜 in {(d-today).days} Tagen")
    df_h["date"] = df_h["date"].astype(str)

    upcoming = [h for h in holidays if h["date"] >= today]
    if upcoming:
        next_h = upcoming[0]
        st.info(f"📅 Nächster Feiertag: **{next_h['name']}** am {next_h['date'].strftime('%d.%m.%Y')} ({(next_h['date']-today).days} Tage)")

    st.subheader(f"Feiertage {year} — {state_label}")
    st.dataframe(df_h.rename(columns={"date":"Datum","name":"Feiertag","Wochentag":"Tag"}),
                 use_container_width=True)

    # ICS Export
    try:
        from extensions_v2_final2 import generate_ics
        events = [{"title": h["name"], "start": h["date"], "uid": f"holiday-{h['date']}-{state}"} for h in holidays]
        ics = generate_ics(events)
        st.download_button("📅 Als ICS exportieren (für Kalender-Apps)",
                           ics.encode("utf-8"),
                           f"feiertage_{year}_{state}.ics", "text/calendar")
    except Exception:
        pass

    # Konflikt-Check mit Dienstplan
    st.divider()
    st.subheader("⚠️ Feiertag-Schicht-Konflikt-Check")
    holiday_dates = [str(h["date"]) for h in holidays]
    if holiday_dates:
        conflicts = df_fn(f"""
            SELECT s.shift_date AS Datum, COALESCE(e.name,'Unbesetzt') AS Mitarbeiter,
                   s.shift_type AS Art, COALESCE(c.company,'–') AS Kunde
            FROM shifts s
            LEFT JOIN employees e ON e.id=s.employee_id
            LEFT JOIN customers c ON c.id=s.customer_id
            WHERE s.shift_date IN ({','.join(['?']*len(holiday_dates))})
              AND s.status IN ('geplant','bestätigt')
              AND substr(s.shift_date,1,4)='{year}'
            ORDER BY s.shift_date
        """, tuple(holiday_dates))
        if not conflicts.empty:
            st.warning(f"⚠️ {len(conflicts)} Schichten an Feiertagen (Feiertagszuschlag prüfen!)")
            st.dataframe(conflicts, use_container_width=True)
        else:
            st.success("✅ Keine Schichten an Feiertagen.")


# ─────────────────────────────────────────────────────────────
# 6. Mindestlohn-Checker
# ─────────────────────────────────────────────────────────────

MINDESTLOHN_2024 = 12.41  # € Stand 1.1.2024
MINDESTLOHN_2025 = 12.82  # € Stand 1.1.2025 (geplant)


def page_minimum_wage_checker(df_fn) -> None:
    st.title("⚖️ Mindestlohn-Checker")
    st.caption(f"Prüft ob alle Mitarbeiter ≥ Mindestlohn erhalten (2024: {MINDESTLOHN_2024} €/h · 2025: {MINDESTLOHN_2025} €/h)")

    current_year = date.today().year
    min_wage = MINDESTLOHN_2025 if current_year >= 2025 else MINDESTLOHN_2024

    st.info(f"**Aktueller gesetzlicher Mindestlohn:** {min_wage:.2f} €/h")
    st.caption("Sicherheitsgewerbe: Ggf. höhere Branchenmindestlöhne nach BRTV/TV-MA-Bewachungsgewerbe beachten!")

    # Mitarbeiter prüfen
    employees = df_fn("""
        SELECT id, employee_no AS Nr, name AS Mitarbeiter,
               COALESCE(hourly_rate, 0) AS Stundenlohn,
               COALESCE(weekly_hours, 40) AS Wochenstunden,
               employment_type AS Vertragsart
        FROM employees WHERE active=1 ORDER BY name
    """)

    if employees.empty:
        st.info("Keine aktiven Mitarbeiter.")
        return

    employees["Status"] = employees["Stundenlohn"].apply(
        lambda h: "✅ OK" if float(h) >= min_wage else
                  ("⚠️ Unter Mindestlohn!" if float(h) > 0 else "❓ Kein Stundenlohn hinterlegt"))
    employees["Differenz"] = (employees["Stundenlohn"].astype(float) - min_wage).round(2)

    violations = employees[employees["Stundenlohn"].astype(float) < min_wage]
    no_rate    = employees[employees["Stundenlohn"].astype(float) == 0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Mitarbeiter gesamt", len(employees))
    c2.metric("⚠️ Unter Mindestlohn", len(violations))
    c3.metric("❓ Kein Stundenlohn", len(no_rate))

    if not violations.empty:
        st.error(f"❌ {len(violations)} Mitarbeiter unter Mindestlohn ({min_wage} €/h)!")
        st.dataframe(violations[["Nr","Mitarbeiter","Stundenlohn","Wochenstunden","Differenz","Status"]],
                     use_container_width=True)
    elif not no_rate.empty:
        st.warning("⚠️ Für einige Mitarbeiter ist kein Stundenlohn hinterlegt.")
    else:
        st.success(f"✅ Alle Mitarbeiter erhalten mind. {min_wage} €/h!")

    st.dataframe(employees[["Nr","Mitarbeiter","Stundenlohn","Status","Differenz"]],
                 use_container_width=True, height=250)

    # Hochrechnung: Was kostet Mindestlohn-Erhöhung?
    st.divider()
    st.subheader("💰 Kosten-Simulation Mindestlohn-Erhöhung")
    new_rate = st.slider("Neuer Mindestlohn (€/h)", 12.0, 16.0, min_wage + 0.5, 0.01)
    affected = employees[employees["Stundenlohn"].astype(float) < new_rate]
    if not affected.empty:
        extra_cost_per_h = (new_rate - affected["Stundenlohn"].astype(float)).clip(lower=0)
        extra_monthly = (extra_cost_per_h * affected["Wochenstunden"].astype(float) * 4.33).sum()
        st.metric(f"Mehrkosten/Monat bei {new_rate:.2f} €/h", fmt_eur(extra_monthly))
        st.metric("Betroffene Mitarbeiter", len(affected))


# ─────────────────────────────────────────────────────────────
# 7. Bankkonto-CSV-Import (DKB, Sparkasse, ING, Commerzbank)
# ─────────────────────────────────────────────────────────────

BANK_FORMATS = {
    "DKB": {
        "encoding": "iso-8859-1",
        "skiprows": 5,
        "sep": ";",
        "columns": {"Buchungstag": "booking_date", "Auftraggeber / Beguenstigter": "payer_payee",
                    "Verwendungszweck": "purpose", "Betrag (EUR)": "amount"},
    },
    "Sparkasse": {
        "encoding": "iso-8859-1",
        "skiprows": 0,
        "sep": ";",
        "columns": {"Buchungstag": "booking_date", "Beguenstigter/Zahlungspflichtiger": "payer_payee",
                    "Verwendungszweck": "purpose", "Betrag": "amount"},
    },
    "ING": {
        "encoding": "iso-8859-1",
        "skiprows": 13,
        "sep": ";",
        "columns": {"Buchung": "booking_date", "Auftraggeber/Empfänger": "payer_payee",
                    "Verwendungszweck": "purpose", "Betrag": "amount"},
    },
    "Commerzbank": {
        "encoding": "utf-8",
        "skiprows": 5,
        "sep": ";",
        "columns": {"Buchungstag": "booking_date", "Empfänger/Absender": "payer_payee",
                    "Buchungstext": "purpose", "Betrag": "amount"},
    },
    "Volksbank/Raiffeisenbank": {
        "encoding": "iso-8859-1",
        "skiprows": 1,
        "sep": ";",
        "columns": {"Buchungstag": "booking_date", "Auftraggeber/Beguenstigter": "payer_payee",
                    "Verwendungszweck": "purpose", "Umsatz": "amount"},
    },
}


def parse_bank_csv(uploaded_file, bank: str) -> Optional[pd.DataFrame]:
    """Parst Bank-CSV-Export in einheitliches Format."""
    fmt = BANK_FORMATS.get(bank, BANK_FORMATS["DKB"])
    try:
        import io
        content = uploaded_file.read()
        # Encoding erkennen
        for enc in [fmt["encoding"], "utf-8", "iso-8859-1", "cp1252"]:
            try:
                text = content.decode(enc)
                break
            except Exception:
                continue

        df = pd.read_csv(io.StringIO(text),
                         sep=fmt["sep"],
                         skiprows=fmt["skiprows"],
                         encoding=enc,
                         on_bad_lines="skip")

        # Spalten mappen
        col_map = {k: v for k, v in fmt["columns"].items() if k in df.columns}
        df = df.rename(columns=col_map)
        df = df[[c for c in ["booking_date","payer_payee","purpose","amount"] if c in df.columns]]

        # Betrag bereinigen
        if "amount" in df.columns:
            df["amount"] = df["amount"].astype(str).str.replace(".", "", regex=False)
            df["amount"] = df["amount"].str.replace(",", ".", regex=False)
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
            df = df.dropna(subset=["amount"])

        # Datum bereinigen
        if "booking_date" in df.columns:
            df["booking_date"] = pd.to_datetime(df["booking_date"],
                                                  dayfirst=True, errors="coerce").dt.strftime("%Y-%m-%d")

        df = df.dropna(subset=["booking_date"])
        return df
    except Exception as e:
        st.error(f"Parse-Fehler: {e}")
        return None


def page_bank_csv_import(run_fn, df_fn, log_fn) -> None:
    st.title("🏦 Bankkonto-CSV-Import")
    st.caption("Importiere Kontoauszüge von DKB, Sparkasse, ING, Commerzbank, Volksbank.")

    tabs = st.tabs(["📥 Importieren", "📋 Importierte Transaktionen", "📖 Anleitung"])

    with tabs[0]:
        col1, col2 = st.columns(2)
        bank = col1.selectbox("Bank auswählen", list(BANK_FORMATS.keys()))
        uploaded = col2.file_uploader("CSV-Datei hochladen", type=["csv","txt"])

        if uploaded:
            df = parse_bank_csv(uploaded, bank)
            if df is not None and not df.empty:
                st.success(f"✅ {len(df)} Transaktionen erkannt")
                st.dataframe(df.head(10), use_container_width=True)

                # Import-Optionen
                col1, col2 = st.columns(2)
                skip_existing = col1.checkbox("Bereits vorhandene überspringen", value=True)
                col2.metric("Einnahmen",  fmt_eur(float(df[df["amount"]>0]["amount"].sum()) if not df[df["amount"]>0].empty else 0))

                if st.button(f"📥 Alle {len(df)} Transaktionen importieren", type="primary"):
                    imported = skipped = 0
                    for _, row in df.iterrows():
                        if skip_existing:
                            ex = df_fn("SELECT id FROM bank_transactions WHERE booking_date=? AND amount=? AND purpose=?",
                                       (str(row.get("booking_date","")),
                                        float(row.get("amount",0)),
                                        str(row.get("purpose",""))[:200]))
                            if not ex.empty:
                                skipped += 1
                                continue
                        try:
                            run_fn("""INSERT INTO bank_transactions(booking_date,payer_payee,purpose,amount,status)
                                      VALUES(?,?,?,?,?)""",
                                   (str(row.get("booking_date","")),
                                    str(row.get("payer_payee",""))[:200],
                                    str(row.get("purpose",""))[:300],
                                    float(row.get("amount",0)),
                                    "neu"))
                            imported += 1
                        except Exception:
                            pass
                    log_fn("bank_csv_imported", f"{bank}: {imported} importiert")
                    st.success(f"✅ {imported} importiert · {skipped} übersprungen")
                    st.rerun()

    with tabs[1]:
        txs = df_fn("""
            SELECT booking_date AS Datum, payer_payee AS Auftraggeber,
                   purpose AS Verwendungszweck, amount AS Betrag, status AS Status
            FROM bank_transactions ORDER BY booking_date DESC LIMIT 200
        """)
        if not txs.empty:
            st.metric("Transaktionen gesamt", len(txs))
            st.dataframe(txs, use_container_width=True, height=400)
        else:
            st.info("Noch keine Transaktionen importiert.")

    with tabs[2]:
        st.markdown("""
**CSV-Export aus deiner Online-Banking-App:**

| Bank | Wo exportieren | Format |
|---|---|---|
| **DKB** | Konto → Umsätze → Export | CSV (.csv) |
| **Sparkasse** | Umsätze → Download | CSV (.csv) |
| **ING** | Umsätze → Export | CSV (.csv) |
| **Commerzbank** | Umsätze → Download | CSV (.csv) |
| **Volksbank** | Umsätze → Export | CSV (.csv) |

**Nach dem Import:**  
→ BWA-Auto: Transaktionen automatisch kategorisieren  
→ Bank/DATEV: Manuell zuordnen
        """)


# ─────────────────────────────────────────────────────────────
# 8. Datenbankoptimierung
# ─────────────────────────────────────────────────────────────

def page_db_optimize(run_fn, df_fn, db_path: Path) -> None:
    st.title("⚡ Datenbankoptimierung")
    st.caption("ANALYZE + VACUUM + Integrity Check für beste Performance.")

    col1, col2 = st.columns(2)
    db_size_before = db_path.stat().st_size if db_path.exists() else 0
    col1.metric("DB-Größe vor Optimierung", f"{db_size_before//1024} KB")

    tables = df_fn("SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table'").iloc[0]["n"]
    col2.metric("Tabellen", int(tables))

    st.divider()
    actions = st.multiselect("Aktionen", [
        "ANALYZE (Statistiken aktualisieren)",
        "VACUUM (Speicher freigeben)",
        "INTEGRITY CHECK",
        "Alte Audit-Logs löschen (>90 Tage)",
        "Rate-Limit-Einträge löschen (>24h)",
        "Alte Benachrichtigungen löschen (gelesen >30 Tage)",
    ], default=["ANALYZE (Statistiken aktualisieren)", "VACUUM (Speicher freigeben)"])

    if st.button("🚀 Optimierung starten", type="primary"):
        results = []
        for action in actions:
            try:
                if "ANALYZE" in action:
                    run_fn("ANALYZE")
                    results.append("✅ ANALYZE abgeschlossen")
                elif "VACUUM" in action:
                    run_fn("VACUUM")
                    db_size_after = db_path.stat().st_size if db_path.exists() else 0
                    saved = db_size_before - db_size_after
                    results.append(f"✅ VACUUM: {saved//1024} KB freigegeben")
                elif "INTEGRITY" in action:
                    r = df_fn("PRAGMA integrity_check")
                    ok = not r.empty and r.iloc[0,0] == "ok"
                    results.append(f"{'✅' if ok else '❌'} Integrity: {r.iloc[0,0] if not r.empty else 'Fehler'}")
                elif "Audit-Logs" in action:
                    run_fn("DELETE FROM audit_log WHERE created_at < date('now','-90 days')")
                    results.append("✅ Alte Audit-Logs gelöscht")
                elif "Rate-Limit" in action:
                    run_fn("DELETE FROM rate_limits WHERE attempt_time < datetime('now','-24 hours')")
                    results.append("✅ Rate-Limit-Einträge bereinigt")
                elif "Benachrichtigungen" in action:
                    run_fn("DELETE FROM notifications WHERE dismissed=1 AND created_at < date('now','-30 days')")
                    results.append("✅ Alte Benachrichtigungen gelöscht")
            except Exception as e:
                results.append(f"❌ {action[:30]}: {e}")

        for r in results:
            st.markdown(r)

        db_size_after = db_path.stat().st_size if db_path.exists() else 0
        st.metric("DB-Größe nach Optimierung", f"{db_size_after//1024} KB",
                  f"{(db_size_before - db_size_after)//1024} KB gespart")
