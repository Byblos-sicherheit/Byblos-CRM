"""
extensions_v2_new3.py – DATEV-Mapping + Benachrichtigungen + Betrieb
=====================================================================
1. DATEV-Konten-Mapping (SKR03/SKR04 vollständig editierbar)
2. Telegram / E-Mail Push-Benachrichtigungen
3. Erweiterte Rechnungs-PDF mit GiroCode-QR
4. Betriebskosten-Dashboard (Kosten je Schicht, Marge)
5. Objektverwaltung (Einsatzorte mit SLA-Verknüpfung)
6. Qualitätssicherungs-Checklisten (digital, mit Unterschrift)
7. Notfall-Kontaktliste
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung
# ─────────────────────────────────────────────────────────────

def register_new3(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS datev_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bwa_category TEXT UNIQUE NOT NULL,
        skr03_account TEXT,
        skr04_account TEXT,
        account_name TEXT,
        tax_key TEXT DEFAULT '',
        notes TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS notification_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel TEXT NOT NULL,
        recipient TEXT,
        message TEXT,
        status TEXT DEFAULT 'pending',
        sent_at TEXT,
        error TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS quality_checklists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        checklist_date TEXT NOT NULL,
        location TEXT,
        employee_id INTEGER,
        customer_id INTEGER,
        checklist_type TEXT DEFAULT 'Schichtbeginn',
        items_json TEXT,
        signature TEXT,
        status TEXT DEFAULT 'offen',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS emergency_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT,
        phone TEXT NOT NULL,
        phone2 TEXT,
        email TEXT,
        customer_id INTEGER,
        availability TEXT DEFAULT '24/7',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    # Seed Standard-DATEV-Konten (SKR03)
    defaults = [
        ("Wareneinsatz / Fremdleistungen", "4000", "5000", "Fremdleistungen", ""),
        ("Personal / Löhne",              "4100", "6000", "Löhne und Gehälter", ""),
        ("Raumkosten / Miete",            "4200", "6310", "Miete", "VSt 19%"),
        ("Versicherungen / Beiträge",     "4300", "6300", "Versicherungen", ""),
        ("Fahrzeugkosten",                "4400", "6520", "Kfz-Kosten", "VSt 19%"),
        ("Werbung / Marketing",           "4500", "6600", "Werbekosten", "VSt 19%"),
        ("Reisekosten / Verpflegung",     "4600", "6650", "Reisekosten", "VSt 19%"),
        ("Bürobedarf / Telefon / Software","4700", "6805", "Bürobedarf", "VSt 19%"),
        ("Rechts- und Beratungskosten",   "4800", "6825", "Rechtsberatung", "VSt 19%"),
        ("Sonstige betriebliche Aufwendungen","4900","6900","Sonstige Kosten",""),
        ("Kfz-Kosten",                    "4530", "6520", "Kfz-Kosten lfd.", "VSt 19%"),
        ("Bürokosten",                    "4910", "6805", "Bürokosten", "VSt 19%"),
        ("Kommunikation",                 "4920", "6815", "Telefon/Internet", "VSt 19%"),
        ("Energie",                       "4240", "6350", "Energie", "VSt 19%"),
        ("Betriebsausstattung",           "4980", "6855", "Betriebsausstattung", "VSt 19%"),
        ("IT-Kosten",                     "4980", "6860", "EDV-Kosten", "VSt 19%"),
        ("Finanzkosten",                  "4970", "7300", "Bankgebühren", ""),
        ("Personalentwicklung",           "4145", "6020", "Aus-/Fortbildung", "VSt 19%"),
        ("Personalkosten",                "4100", "6000", "Personalkosten", ""),
        ("Beratungskosten",               "4970", "6825", "Beratungskosten", "VSt 19%"),
        ("Marketing",                     "4610", "6600", "Marketing", "VSt 19%"),
    ]
    for cat, skr03, skr04, name, tax in defaults:
        try:
            run_fn("""INSERT OR IGNORE INTO datev_accounts(bwa_category,skr03_account,skr04_account,account_name,tax_key)
                      VALUES(?,?,?,?,?)""", (cat, skr03, skr04, name, tax))
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
# 1. DATEV-Konten-Mapping
# ─────────────────────────────────────────────────────────────

def page_datev_mapping(run_fn, df_fn) -> None:
    st.title("🏦 DATEV-Konten-Mapping")
    st.caption("SKR03/SKR04-Konten je BWA-Kostenart. "
               "Bitte mit Steuerberater abstimmen vor produktivem Einsatz.")

    tabs = st.tabs(["📋 Kontenplan", "✏️ Bearbeiten", "📤 DATEV-Export mit Konten"])

    with tabs[0]:
        accounts = df_fn("""
            SELECT bwa_category AS Kostenart, skr03_account AS SKR03,
                   skr04_account AS SKR04, account_name AS Kontobezeichnung,
                   tax_key AS Steuerschlüssel, notes AS Notiz
            FROM datev_accounts ORDER BY skr03_account
        """)
        if not accounts.empty:
            st.dataframe(accounts, use_container_width=True)
            csv = accounts.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 Kontenplan CSV", csv, "datev_kontenplan.csv", "text/csv")
        else:
            st.info("Kein Kontenplan vorhanden. Bitte 'Standardkonten laden' klicken.")
            if st.button("📥 SKR03-Standardkonten laden"):
                register_new3(run_fn, df_fn)
                st.success("Standardkonten geladen!")
                st.rerun()

    with tabs[1]:
        accounts_edit = df_fn("SELECT id, bwa_category AS label FROM datev_accounts ORDER BY bwa_category")
        if accounts_edit.empty:
            st.info("Keine Konten vorhanden.")
            return

        sel = st.selectbox("Kostenart bearbeiten", accounts_edit["label"].tolist())
        aid = int(accounts_edit[accounts_edit["label"] == sel].iloc[0]["id"])
        row = df_fn("SELECT * FROM datev_accounts WHERE id=?", (aid,)).iloc[0].to_dict()

        with st.form("datev_edit"):
            a, b, c = st.columns(3)
            skr03 = a.text_input("SKR03-Konto", str(row.get("skr03_account", "")))
            skr04 = b.text_input("SKR04-Konto", str(row.get("skr04_account", "")))
            name  = c.text_input("Kontobezeichnung", str(row.get("account_name", "")))
            tax   = a.text_input("Steuerschlüssel", str(row.get("tax_key", "")))
            notes = st.text_area("Notizen", str(row.get("notes", "") or ""))
            if st.form_submit_button("💾 Speichern", type="primary"):
                run_fn("""UPDATE datev_accounts SET skr03_account=?,skr04_account=?,
                          account_name=?,tax_key=?,notes=?,updated_at=datetime('now')
                          WHERE id=?""", (skr03, skr04, name, tax, notes, aid))
                st.success("✅ Konto aktualisiert!")
                st.rerun()

        # Neue Kostenart hinzufügen
        st.divider()
        with st.form("datev_new"):
            st.subheader("Neue Kostenart anlegen")
            a2, b2, c2, d2 = st.columns(4)
            new_cat  = a2.text_input("Kostenart *")
            new_s03  = b2.text_input("SKR03-Konto")
            new_s04  = c2.text_input("SKR04-Konto")
            new_name = d2.text_input("Bezeichnung")
            if st.form_submit_button("➕ Hinzufügen") and new_cat:
                run_fn("INSERT OR IGNORE INTO datev_accounts(bwa_category,skr03_account,skr04_account,account_name) VALUES(?,?,?,?)",
                       (new_cat, new_s03, new_s04, new_name))
                st.success(f"'{new_cat}' hinzugefügt.")
                st.rerun()

    with tabs[2]:
        st.subheader("DATEV-Export mit korrekten Konten")
        col1, col2, col3 = st.columns(3)
        month  = col1.text_input("Monat", date.today().strftime("%Y-%m"))
        skr    = col2.selectbox("Kontenrahmen", ["SKR03", "SKR04"])
        format_type = col3.selectbox("Format", ["DATEV-ähnlich CSV", "DATEV-ähnlich Excel"])

        if st.button("📊 Export erstellen", type="primary"):
            acct_col = "skr03_account" if skr == "SKR03" else "skr04_account"

            inv_export = df_fn(f"""
                SELECT i.invoice_date AS Belegdatum,
                       i.invoice_no AS Belegfeld1,
                       ROUND(i.net_total,2) AS Umsatz_netto,
                       ROUND(i.vat_total,2) AS Steuer,
                       ROUND(i.gross_total,2) AS Umsatz_brutto,
                       i.vat_rate AS MwSt_Satz,
                       '8400' AS Konto,
                       '10000' AS Gegenkonto,
                       'S' AS SollHaben,
                       i.description AS Buchungstext,
                       c.company AS Kunde_Name
                FROM invoices i JOIN customers c ON c.id=i.customer_id
                WHERE substr(i.invoice_date,1,7)=?
                ORDER BY i.invoice_date
            """, (month,))

            exp_export = df_fn(f"""
                SELECT e.expense_date AS Belegdatum,
                       e.expense_no AS Belegfeld1,
                       ROUND(e.net_amount,2) AS Umsatz_netto,
                       ROUND(e.vat_amount,2) AS Vorsteuer,
                       ROUND(e.gross_amount,2) AS Umsatz_brutto,
                       e.vat_rate AS MwSt_Satz,
                       COALESCE(da.{acct_col},'4900') AS Konto,
                       '1200' AS Gegenkonto,
                       'H' AS SollHaben,
                       e.description AS Buchungstext,
                       COALESCE(s.name,'') AS Lieferant_Name
                FROM expenses e
                LEFT JOIN suppliers s ON s.id=e.supplier_id
                LEFT JOIN datev_accounts da ON da.bwa_category=e.category
                WHERE substr(e.expense_date,1,7)=?
                ORDER BY e.expense_date
            """, (month,))

            if not inv_export.empty or not exp_export.empty:
                c1, c2 = st.columns(2)
                c1.metric("Rechnungen", len(inv_export))
                c2.metric("Ausgaben", len(exp_export))

                if format_type == "DATEV-ähnlich CSV":
                    combined = pd.concat([inv_export, exp_export], ignore_index=True, sort=False)
                    csv = combined.to_csv(index=False, sep=";").encode("utf-8-sig")
                    st.download_button(f"📥 DATEV-CSV {month} ({skr})", csv,
                                       f"datev_{skr}_{month}.csv", "text/csv")
                else:
                    from io import BytesIO
                    buf = BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        if not inv_export.empty:
                            inv_export.to_excel(writer, sheet_name=f"Erlöse_{month}", index=False)
                        if not exp_export.empty:
                            exp_export.to_excel(writer, sheet_name=f"Aufwände_{month}", index=False)
                    buf.seek(0)
                    st.download_button(f"📥 DATEV-Excel {month} ({skr})", buf.read(),
                                       f"datev_{skr}_{month}.xlsx",
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("Keine Daten für diesen Monat.")


# ─────────────────────────────────────────────────────────────
# 2. Push-Benachrichtigungen (Telegram / E-Mail)
# ─────────────────────────────────────────────────────────────

def send_telegram(token: str, chat_id: str, message: str) -> tuple[bool, str]:
    """Sendet eine Telegram-Nachricht via Bot-API."""
    try:
        import urllib.request, json
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": message,
                           "parse_mode": "Markdown"}).encode("utf-8")
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                return True, "Gesendet"
            return False, str(result.get("description", "Unbekannter Fehler"))
    except Exception as e:
        return False, str(e)


def page_notifications_setup(run_fn, df_fn, get_setting_fn, set_setting_fn) -> None:
    st.title("🔔 Push-Benachrichtigungen")
    st.caption("Automatische Benachrichtigungen bei wichtigen Ereignissen.")

    tabs = st.tabs([
        "⚙️ Einrichtung", "📨 Test senden", "📋 Protokoll", "🤖 Regeln"
    ])

    with tabs[0]:
        st.subheader("Telegram-Bot einrichten")
        with st.expander("📖 Schritt-für-Schritt Anleitung", expanded=False):
            st.markdown("""
1. **BotFather öffnen:** In Telegram @BotFather suchen
2. `/newbot` eingeben und Namen festlegen (z.B. "ByblosCRM Bot")
3. **Bot-Token** kopieren (Format: `123456789:AAF...`)
4. Bot in deinen Telegram-Chat einladen und `/start` senden
5. **Chat-ID** ermitteln: URL aufrufen:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   → `chat.id` aus der Antwort kopieren
            """)

        with st.form("telegram_form"):
            tg_token   = st.text_input("Telegram Bot-Token",
                                        get_setting_fn("telegram_token", ""),
                                        type="password")
            tg_chat_id = st.text_input("Chat-ID (Gruppe oder persönlich)",
                                        get_setting_fn("telegram_chat_id", ""))
            tg_enabled = st.checkbox("Telegram-Benachrichtigungen aktiv",
                                     value=get_setting_fn("telegram_enabled", "0") == "1")
            st.divider()
            st.subheader("E-Mail-Benachrichtigungen")
            notif_email = st.text_input("Benachrichtigungs-E-Mail",
                                         get_setting_fn("notification_email", ""))
            email_enabled = st.checkbox("E-Mail-Benachrichtigungen aktiv",
                                        value=get_setting_fn("email_notifications_enabled", "0") == "1")
            if st.form_submit_button("💾 Speichern", type="primary"):
                for k, v in [
                    ("telegram_token", tg_token),
                    ("telegram_chat_id", tg_chat_id),
                    ("telegram_enabled", "1" if tg_enabled else "0"),
                    ("notification_email", notif_email),
                    ("email_notifications_enabled", "1" if email_enabled else "0"),
                ]:
                    set_setting_fn(k, v)
                st.success("✅ Einstellungen gespeichert.")

        st.divider()
        st.subheader("Benachrichtigungs-Trigger konfigurieren")
        triggers = {
            "Neue überfällige Rechnung": "trigger_overdue",
            "Backup älter als 7 Tage":  "trigger_backup_old",
            "Schicht unbesetzt (24h vorher)": "trigger_unbesetzt",
            "Neue Rechnung erstellt":    "trigger_new_invoice",
            "Zahlung eingegangen":       "trigger_payment_received",
            "Neuer Mitarbeiter":         "trigger_new_employee",
        }
        with st.form("triggers_form"):
            for label, key in triggers.items():
                st.checkbox(label, value=get_setting_fn(key, "0") == "1", key=f"cb_{key}")
            if st.form_submit_button("💾 Trigger speichern"):
                for label, key in triggers.items():
                    val = "1" if st.session_state.get(f"cb_{key}", False) else "0"
                    set_setting_fn(key, val)
                st.success("✅ Trigger gespeichert.")

    with tabs[1]:
        st.subheader("Test-Nachricht senden")
        col1, col2 = st.columns(2)
        channel = col1.selectbox("Kanal", ["Telegram", "E-Mail"])
        msg = col2.text_area("Nachricht", "🛡️ *Byblos CRM* – Test-Benachrichtigung funktioniert!")

        if st.button("📨 Test senden", type="primary"):
            if channel == "Telegram":
                token   = get_setting_fn("telegram_token", "")
                chat_id = get_setting_fn("telegram_chat_id", "")
                if not token or not chat_id:
                    st.error("Bitte zuerst Token und Chat-ID eingeben.")
                else:
                    ok, result = send_telegram(token, chat_id, msg)
                    run_fn("INSERT INTO notification_log(channel,recipient,message,status,sent_at,error) VALUES(?,?,?,?,?,?)",
                           ("telegram", chat_id, msg, "gesendet" if ok else "fehler",
                            datetime.now().isoformat()[:19], "" if ok else result))
                    if ok:
                        st.success("✅ Telegram-Nachricht gesendet!")
                    else:
                        st.error(f"❌ Fehler: {result}")
            else:
                st.info("E-Mail-Test: Bitte E-Mail-Bereich > Tab 'Freitext-Mail' verwenden.")

    with tabs[2]:
        log = df_fn("""
            SELECT created_at AS Zeit, channel AS Kanal, recipient AS Empfänger,
                   LEFT(message,80) AS Nachricht, status AS Status, error AS Fehler
            FROM notification_log ORDER BY created_at DESC LIMIT 100
        """)
        if not log.empty:
            st.dataframe(log, use_container_width=True)
        else:
            st.info("Noch keine Benachrichtigungen gesendet.")

    with tabs[3]:
        st.subheader("Automatische Benachrichtigungs-Regeln")
        st.markdown("""
| Ereignis | Wann | Nachricht |
|---|---|---|
| 🔴 Überfällige Rechnung | Täglich 07:00 | Rechnung RE-XXX seit N Tagen überfällig |
| 📅 Unbesetzte Schicht | 24h vorher | Morgen: Schicht ohne Mitarbeiter! |
| 💾 Backup-Warnung | Tagesroutine | Kein Backup seit 7+ Tagen |
| 💰 Zahlung erhalten | Bei Buchung | Zahlung von Kunde X eingegangen |
| 🆕 Neue Rechnung | Bei Erstellung | Rechnung RE-XXX erstellt |

**Aktivierung:** Trigger in Tab 'Einrichtung' aktivieren, dann Tagesroutine ausführen.

**Telegram-Formatierung:** Markdown wird unterstützt.
- `*fett*` → **fett**
- `_kursiv_` → _kursiv_
- `` `code` `` → `code`
        """)


def notify_event(get_setting_fn, run_fn, event_type: str, message: str) -> None:
    """Sendet Benachrichtigung wenn Trigger aktiv. Wird intern aufgerufen."""
    if get_setting_fn(f"trigger_{event_type}", "0") != "1":
        return
    if get_setting_fn("telegram_enabled", "0") == "1":
        token   = get_setting_fn("telegram_token", "")
        chat_id = get_setting_fn("telegram_chat_id", "")
        if token and chat_id:
            ok, err = send_telegram(token, chat_id, message)
            try:
                run_fn("INSERT INTO notification_log(channel,recipient,message,status,sent_at,error) VALUES(?,?,?,?,?,?)",
                       ("telegram", chat_id, message, "gesendet" if ok else "fehler",
                        datetime.now().isoformat()[:19], "" if ok else err))
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────
# 3. Betriebskosten-Dashboard
# ─────────────────────────────────────────────────────────────

def page_operations_dashboard(df_fn) -> None:
    st.title("📊 Betriebskosten-Dashboard")
    st.caption("Kosten je Schicht, Marge je Kunde, Mitarbeiter-Effizienz.")

    tabs = st.tabs([
        "💰 Marge je Kunde", "⏱️ Kosten je Schicht",
        "👷 Mitarbeiter-Effizienz", "📈 Rentabilitäts-Cockpit"
    ])

    # ── Tab 0: Marge je Kunde ─────────────────────────────────
    with tabs[0]:
        st.subheader("Marge je Kunde (Umsatz vs. Personalkosten)")
        col1, col2 = st.columns(2)
        year  = col1.selectbox("Jahr", list(range(date.today().year, date.today().year - 3, -1)))
        month_f = col2.text_input("Monat (leer = ganzes Jahr)", "")

        where = f"AND substr(i.invoice_date,1,4)='{year}'"
        if month_f:
            where = f"AND substr(i.invoice_date,1,7)='{month_f}'"

        revenue_by_cust = df_fn(f"""
            SELECT c.company AS Kunde,
                   SUM(CASE WHEN i.status='bezahlt' THEN i.net_total ELSE 0 END) AS Umsatz_netto,
                   COUNT(i.id) AS Rechnungen
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE 1=1 {where}
            GROUP BY c.id ORDER BY Umsatz_netto DESC LIMIT 20
        """)

        # Schichten und Personal-Stunden je Kunde
        shifts_by_cust = df_fn(f"""
            SELECT COALESCE(c.company, 'Unbekannt') AS Kunde,
                   COUNT(s.id) AS Schichten,
                   SUM(
                       CAST((strftime('%s', CASE WHEN s.end_time < s.start_time
                           THEN date(s.shift_date,'+1 day') || ' ' || s.end_time
                           ELSE s.shift_date || ' ' || s.end_time END)
                       - strftime('%s', s.shift_date || ' ' || s.start_time)) AS REAL) / 3600.0
                   ) AS Std_gesamt
            FROM shifts s LEFT JOIN customers c ON c.id=s.customer_id
            WHERE s.status IN ('abgeschlossen','bestätigt','geplant')
            {"AND substr(s.shift_date,1,4)='" + str(year) + "'" if not month_f else
             "AND substr(s.shift_date,1,7)='" + month_f + "'"}
            GROUP BY c.id ORDER BY Std_gesamt DESC LIMIT 20
        """)

        if not revenue_by_cust.empty:
            if not shifts_by_cust.empty:
                merged = revenue_by_cust.merge(shifts_by_cust, on="Kunde", how="outer").fillna(0)
                # Angenommener Ø-Stundensatz Personalkosten
                avg_rate = 15.0
                merged["Personalkosten_Est"] = (merged["Std_gesamt"] * avg_rate).round(2)
                merged["Marge_Est_EUR"] = (merged["Umsatz_netto"] - merged["Personalkosten_Est"]).round(2)
                merged["Marge_Pct"] = ((merged["Marge_Est_EUR"] / merged["Umsatz_netto"].replace(0, 1)) * 100).round(1)
                st.caption(f"⚠️ Personalkosten basierend auf Ø {avg_rate:.2f} €/Std. (Schätzwert)")
                st.dataframe(merged, use_container_width=True)
                st.bar_chart(merged.set_index("Kunde")["Marge_Est_EUR"])
            else:
                st.dataframe(revenue_by_cust, use_container_width=True)
                st.bar_chart(revenue_by_cust.set_index("Kunde")["Umsatz_netto"])

    # ── Tab 1: Kosten je Schicht ──────────────────────────────
    with tabs[1]:
        st.subheader("Durchschnittliche Kosten je Schicht")
        month2 = st.text_input("Monat", date.today().strftime("%Y-%m"))

        total_shifts = df_fn("""
            SELECT COUNT(*) AS n FROM shifts
            WHERE substr(shift_date,1,7)=?
            AND status IN ('abgeschlossen','bestätigt','geplant')
        """, (month2,)).iloc[0]["n"]

        total_exp = df_fn("""
            SELECT COALESCE(SUM(gross_amount),0) AS v FROM expenses
            WHERE bwa_month=?
        """, (month2,)).iloc[0]["v"]

        total_rev = df_fn("""
            SELECT COALESCE(SUM(gross_total),0) AS v FROM invoices
            WHERE substr(invoice_date,1,7)=? AND status='bezahlt'
        """, (month2,)).iloc[0]["v"]

        if int(total_shifts or 0) > 0:
            cost_per_shift = float(total_exp or 0) / int(total_shifts)
            rev_per_shift  = float(total_rev or 0) / int(total_shifts)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Schichten", int(total_shifts))
            c2.metric("Ausgaben gesamt", fmt_eur(float(total_exp or 0)))
            c3.metric("Kosten je Schicht", fmt_eur(cost_per_shift))
            c4.metric("Umsatz je Schicht", fmt_eur(rev_per_shift))
        else:
            st.info("Keine Schichten in diesem Monat.")

        # Kosten-Breakdown je Kategorie
        breakdown = df_fn("""
            SELECT category AS Kostenart, SUM(gross_amount) AS Betrag
            FROM expenses WHERE bwa_month=?
            GROUP BY category ORDER BY Betrag DESC
        """, (month2,))
        if not breakdown.empty:
            st.bar_chart(breakdown.set_index("Kostenart")["Betrag"])

    # ── Tab 2: Mitarbeiter-Effizienz ──────────────────────────
    with tabs[2]:
        st.subheader("Mitarbeiter-Effizienz")
        year3 = st.selectbox("Jahr", list(range(date.today().year, date.today().year - 3, -1)), key="eff_year")

        eff = df_fn("""
            SELECT e.name AS Mitarbeiter,
                   COUNT(s.id) AS Schichten,
                   COUNT(DISTINCT s.customer_id) AS Verschiedene_Kunden,
                   SUM(CASE WHEN s.status='abgeschlossen' THEN 1 ELSE 0 END) AS Abgeschlossen,
                   SUM(CASE WHEN s.status='ausgefallen' THEN 1 ELSE 0 END) AS Ausgefallen,
                   ROUND(SUM(CASE WHEN s.status='abgeschlossen' THEN 1 ELSE 0 END) * 100.0
                         / NULLIF(COUNT(s.id),0), 1) AS Abschluss_Rate_Pct
            FROM shifts s JOIN employees e ON e.id=s.employee_id
            WHERE substr(s.shift_date,1,4)=?
            GROUP BY e.id ORDER BY Schichten DESC
        """, (str(year3),))

        if not eff.empty:
            st.dataframe(eff, use_container_width=True)
            st.bar_chart(eff.set_index("Mitarbeiter")["Schichten"])
        else:
            st.info("Keine Schichtdaten für dieses Jahr.")

    # ── Tab 3: Rentabilitäts-Cockpit ──────────────────────────
    with tabs[3]:
        st.subheader("📈 12-Monats-Rentabilitäts-Cockpit")
        months_12 = df_fn("""
            SELECT substr(invoice_date,1,7) AS Monat,
                   SUM(CASE WHEN status='bezahlt' THEN net_total ELSE 0 END) AS Umsatz_netto_bez
            FROM invoices
            WHERE invoice_date >= date('now','-12 months')
            GROUP BY substr(invoice_date,1,7) ORDER BY Monat
        """)
        exp_12 = df_fn("""
            SELECT bwa_month AS Monat, SUM(net_amount) AS Kosten_netto
            FROM expenses
            WHERE bwa_month >= strftime('%Y-%m', date('now','-12 months'))
            GROUP BY bwa_month ORDER BY Monat
        """)

        if not months_12.empty and not exp_12.empty:
            merged12 = months_12.merge(exp_12, on="Monat", how="outer").fillna(0)
            merged12["Gewinn_netto"] = merged12["Umsatz_netto_bez"] - merged12["Kosten_netto"]
            merged12["Marge_Pct"] = (
                merged12["Gewinn_netto"] / merged12["Umsatz_netto_bez"].replace(0, 1) * 100
            ).round(1)

            c1, c2, c3 = st.columns(3)
            c1.metric("Ø Monatsumsatz", fmt_eur(float(merged12["Umsatz_netto_bez"].mean())))
            c2.metric("Ø Monatskosten", fmt_eur(float(merged12["Kosten_netto"].mean())))
            c3.metric("Ø Marge", f"{float(merged12['Marge_Pct'].mean()):.1f}%")

            st.line_chart(merged12.set_index("Monat")[["Umsatz_netto_bez","Kosten_netto","Gewinn_netto"]])
            st.dataframe(merged12, use_container_width=True)
        else:
            st.info("Mindestens 3 Monate Daten für diese Auswertung erforderlich.")


# ─────────────────────────────────────────────────────────────
# 4. Qualitätssicherungs-Checklisten (digital)
# ─────────────────────────────────────────────────────────────

CHECKLIST_TEMPLATES = {
    "Schichtbeginn": [
        "Ausweis / Dienstausweis vorhanden",
        "Funkgerät voll aufgeladen und funktionsfähig",
        "Schutzausrüstung vollständig",
        "Einweisung am Objekt erhalten",
        "Übergabe vom Vordienst erfolgt",
        "Schlüssel übernommen",
        "Besonderheiten notiert",
    ],
    "Schichtende": [
        "Schlüssel übergeben",
        "Protokollbuch ausgefüllt",
        "Vorfälle dokumentiert",
        "Übergabe an Nachdienst erfolgt",
        "Funkgerät aufgeladen",
        "Keine Schäden festgestellt",
    ],
    "Revierdienst": [
        "Alle Kontrollpunkte abgegangen",
        "Alle Türen/Fenster geprüft",
        "Keine Unbefugten festgestellt",
        "Technische Anlagen geprüft",
        "Kontrollgänge dokumentiert",
        "Auffälligkeiten gemeldet",
    ],
    "Veranstaltung": [
        "Einlass kontrolliert",
        "Identitäten geprüft (ggf.)",
        "Verbotsitems kontrolliert",
        "Kapazitätsgrenzen eingehalten",
        "Notausgänge freigehalten",
        "Vorfälle protokolliert",
    ],
}


def page_quality_checklists(run_fn, df_fn, log_fn) -> None:
    st.title("✅ Qualitätssicherungs-Checklisten")

    tabs = st.tabs([
        "📋 Übersicht", "➕ Neue Checkliste", "📊 Auswertung"
    ])

    with tabs[0]:
        col1, col2 = st.columns(2)
        date_from = col1.date_input("Von", date.today() - timedelta(days=7))
        date_to   = col2.date_input("Bis", date.today())

        data = df_fn("""
            SELECT q.id, q.checklist_date AS Datum,
                   COALESCE(e.name,'–') AS Mitarbeiter,
                   COALESCE(c.company,'–') AS Kunde,
                   q.location AS Objekt, q.checklist_type AS Typ,
                   q.status AS Status, q.notes AS Notiz
            FROM quality_checklists q
            LEFT JOIN employees e ON e.id=q.employee_id
            LEFT JOIN customers c ON c.id=q.customer_id
            WHERE q.checklist_date BETWEEN ? AND ?
            ORDER BY q.checklist_date DESC
        """, (date_from.isoformat(), date_to.isoformat()))

        if not data.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Checklisten", len(data))
            c2.metric("Vollständig", len(data[data["Status"]=="vollständig"]))
            c3.metric("Offen", len(data[data["Status"]=="offen"]))
            st.dataframe(data.drop(columns=["id"]), use_container_width=True)
        else:
            st.info("Keine Checklisten in diesem Zeitraum.")

    with tabs[1]:
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        customers = df_fn("SELECT id, company FROM customers ORDER BY company")

        tpl_type = st.selectbox("Checklisten-Typ", list(CHECKLIST_TEMPLATES.keys()))
        items = CHECKLIST_TEMPLATES[tpl_type]

        col1, col2 = st.columns(2)
        emp_name = col1.selectbox("Mitarbeiter", ["—"] + (employees["name"].tolist() if not employees.empty else []))
        cust_name = col2.selectbox("Kunde / Objekt", ["—"] + (customers["company"].tolist() if not customers.empty else []))
        location = col1.text_input("Einsatzort")
        check_date = col2.date_input("Datum", date.today())

        st.subheader(f"Checkliste: {tpl_type}")
        checked_items = []
        all_ok = True
        for item in items:
            c = st.checkbox(item, value=False, key=f"chk_{item}")
            if c:
                checked_items.append(item)
            else:
                all_ok = False

        notes = st.text_area("Notizen / Auffälligkeiten")
        signature = st.text_input("Unterschrift (Kürzel / Name)")

        col1, col2 = st.columns(2)
        status = "vollständig" if all_ok and signature else "offen"
        st.info(f"Status: **{status}** · {len(checked_items)}/{len(items)} Punkte erledigt")

        if col1.button("💾 Checkliste speichern", type="primary"):
            import json
            eid = cid = None
            if emp_name != "—" and not employees.empty:
                match = employees[employees["name"] == emp_name]
                if not match.empty:
                    eid = int(match.iloc[0]["id"])
            if cust_name != "—" and not customers.empty:
                match = customers[customers["company"] == cust_name]
                if not match.empty:
                    cid = int(match.iloc[0]["id"])

            run_fn("""INSERT INTO quality_checklists(checklist_date,location,employee_id,customer_id,
                      checklist_type,items_json,signature,status,notes)
                      VALUES(?,?,?,?,?,?,?,?,?)""",
                   (check_date.isoformat(), location, eid, cid, tpl_type,
                    json.dumps({"template": items, "checked": checked_items}, ensure_ascii=False),
                    signature, status, notes))
            log_fn("checklist_saved", f"{tpl_type} {check_date} {emp_name}")
            st.success(f"✅ Checkliste gespeichert (Status: {status})")
            st.rerun()

    with tabs[2]:
        st.subheader("Checklisten-Auswertung")
        summary = df_fn("""
            SELECT checklist_type AS Typ,
                   COUNT(*) AS Gesamt,
                   SUM(CASE WHEN status='vollständig' THEN 1 ELSE 0 END) AS Vollständig,
                   SUM(CASE WHEN status='offen' THEN 1 ELSE 0 END) AS Offen,
                   ROUND(SUM(CASE WHEN status='vollständig' THEN 1 ELSE 0 END)*100.0/COUNT(*),1) AS Vollst_Rate
            FROM quality_checklists
            WHERE checklist_date >= date('now','-30 days')
            GROUP BY checklist_type
        """)
        if not summary.empty:
            st.dataframe(summary, use_container_width=True)
            st.bar_chart(summary.set_index("Typ")["Vollst_Rate"])


# ─────────────────────────────────────────────────────────────
# 5. Notfall-Kontaktliste
# ─────────────────────────────────────────────────────────────

def page_emergency_contacts(run_fn, df_fn, log_fn) -> None:
    st.title("🚨 Notfall-Kontakte")
    st.caption("Schneller Zugriff auf alle wichtigen Kontakte im Notfall.")

    tabs = st.tabs(["📋 Kontaktliste", "➕ Kontakt hinzufügen"])

    with tabs[0]:
        contacts = df_fn("""
            SELECT ec.id, ec.name AS Name, ec.role AS Funktion,
                   ec.phone AS Telefon, ec.phone2 AS Mobil,
                   ec.email AS E_Mail,
                   COALESCE(c.company,'–') AS Unternehmen,
                   ec.availability AS Erreichbarkeit
            FROM emergency_contacts ec
            LEFT JOIN customers c ON c.id=ec.customer_id
            ORDER BY ec.role, ec.name
        """)
        if not contacts.empty:
            st.metric("Notfall-Kontakte", len(contacts))
            # Große, gut lesbare Darstellung
            for _, row in contacts.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    col1.markdown(f"**🚨 {row['Name']}**  \n{row['Funktion']}")
                    col2.markdown(f"📞 `{row['Telefon']}`"
                                  + (f"  \n📱 `{row['Mobil']}`" if row.get('Mobil') else ""))
                    col3.markdown(f"{row['Erreichbarkeit']}")
                    st.divider()

            csv = contacts.drop(columns=["id"]).to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 Notfallliste exportieren", csv,
                               "notfall_kontakte.csv", "text/csv")
        else:
            st.info("Noch keine Notfall-Kontakte eingetragen.")

        # Schnell-Nummern
        st.subheader("🆘 Allgemeine Notrufnummern")
        st.markdown("""
| Dienst | Nummer |
|---|---|
| 🚒 Feuerwehr | **112** |
| 🚓 Polizei | **110** |
| 🚑 Notruf allgemein | **112** |
| 🏥 Giftnotruf | **0228 19240** |
| ⚡ Technische Hilfe (THW) | **0228 940-0** |
        """)

    with tabs[1]:
        customers = df_fn("SELECT id, company FROM customers ORDER BY company")
        with st.form("emergency_form", clear_on_submit=True):
            a, b = st.columns(2)
            name  = a.text_input("Name *")
            role  = b.text_input("Funktion / Position", "Ansprechpartner")
            phone = a.text_input("Telefon *")
            phone2 = b.text_input("Mobil / Alternativ")
            email = a.text_input("E-Mail")
            cust_name = b.selectbox("Unternehmen / Objekt", ["—"] + (customers["company"].tolist() if not customers.empty else []))
            avail = st.selectbox("Erreichbarkeit", ["24/7", "Mo-Fr 08-17h", "Mo-Fr 08-20h", "Mo-So 08-22h", "Nur Notfall"])
            notes = st.text_area("Notizen")
            submitted = st.form_submit_button("💾 Kontakt speichern", type="primary")

        if submitted and name and phone:
            cid = None
            if cust_name != "—" and not customers.empty:
                match = customers[customers["company"] == cust_name]
                if not match.empty:
                    cid = int(match.iloc[0]["id"])
            run_fn("INSERT INTO emergency_contacts(name,role,phone,phone2,email,customer_id,availability,notes) VALUES(?,?,?,?,?,?,?,?)",
                   (name, role, phone, phone2, email, cid, avail, notes))
            log_fn("emergency_contact_added", name)
            st.success(f"✅ Notfall-Kontakt '{name}' gespeichert!")
            st.rerun()
