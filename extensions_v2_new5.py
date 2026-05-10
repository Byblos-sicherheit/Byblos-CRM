"""
extensions_v2_new5.py – Qualifikationen + Schichttausch + 2FA + SEPA + API
===========================================================================
1. Mitarbeiter-Qualifikationen (Zertifikate, Ablaufdaten, Warnungen)
2. Schicht-Tauschbörse (Mitarbeiter kann Schicht abgeben/übernehmen)
3. Zwei-Faktor-Authentifizierung (TOTP)
4. SEPA-Lastschrift XML (pain.008)
5. Kostenvoranschlag / Kalkulation
6. Einfache REST-API (Endpunkte als JSON-Export)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung
# ─────────────────────────────────────────────────────────────

def register_new5(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS shift_exchanges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shift_id INTEGER NOT NULL,
        offered_by INTEGER NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'angeboten',
        taken_by INTEGER,
        approved_by TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(shift_id) REFERENCES shifts(id),
        FOREIGN KEY(offered_by) REFERENCES employees(id),
        FOREIGN KEY(taken_by) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS cost_estimates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estimate_no TEXT UNIQUE,
        customer_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        estimated_hours REAL DEFAULT 0,
        hourly_rate REAL DEFAULT 21.0,
        material_cost REAL DEFAULT 0,
        overhead_pct REAL DEFAULT 20.0,
        profit_margin_pct REAL DEFAULT 15.0,
        net_total REAL DEFAULT 0,
        vat_rate REAL DEFAULT 19.0,
        gross_total REAL DEFAULT 0,
        status TEXT DEFAULT 'entwurf',
        valid_until TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_name TEXT NOT NULL,
        api_key TEXT UNIQUE NOT NULL,
        permissions TEXT DEFAULT 'read',
        active INTEGER DEFAULT 1,
        last_used TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS two_factor_secrets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        totp_secret TEXT NOT NULL,
        enabled INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")


# ─────────────────────────────────────────────────────────────
# 1. Mitarbeiter-Qualifikationen
# ─────────────────────────────────────────────────────────────

def page_qualifications(run_fn, df_fn, log_fn) -> None:
    st.title("🎓 Mitarbeiter-Qualifikationen")
    st.caption("Zertifikate, Schulungsnachweise und Ablaufdaten verwalten.")

    tabs = st.tabs(["📋 Übersicht", "➕ Qualifikation eintragen",
                    "⚠️ Ablaufende Nachweise", "📊 Qualifikationsmatrix"])

    QUAL_TYPES = [
        "Unterrichtung §34a GewO",
        "Sachkundeprüfung §34a GewO",
        "Erste-Hilfe-Kurs",
        "Brandschutzhelfer",
        "Evakuierungshelfer",
        "Luftsicherheitskontrollkraft (LKS)",
        "Bewacherregistrierung",
        "Führerschein (Klasse B)",
        "Führerschein (Klasse C)",
        "Defibrillator-Schulung",
        "Anti-Doping-Beauftragter",
        "Personenschutz",
        "Hundeführerschein",
        "Sonstige Qualifikation",
    ]

    with tabs[0]:
        q = st.text_input("🔍 Suche (Mitarbeiter, Qualifikation)")
        if q:
            data = df_fn("""
                SELECT eq.id, e.name AS Mitarbeiter, e.employee_no AS Nr,
                       eq.qualification AS Qualifikation, eq.issuer AS Aussteller,
                       eq.issued_date AS Ausgestellt, eq.expiry_date AS Gültig_bis,
                       eq.certificate_no AS Zertifikat_Nr
                FROM employee_qualifications eq JOIN employees e ON e.id=eq.employee_id
                WHERE e.name LIKE ? OR eq.qualification LIKE ?
                ORDER BY eq.expiry_date, e.name
            """, (f"%{q}%", f"%{q}%"))
        else:
            data = df_fn("""
                SELECT eq.id, e.name AS Mitarbeiter, e.employee_no AS Nr,
                       eq.qualification AS Qualifikation, eq.issuer AS Aussteller,
                       eq.issued_date AS Ausgestellt, eq.expiry_date AS Gültig_bis,
                       eq.certificate_no AS Zertifikat_Nr
                FROM employee_qualifications eq JOIN employees e ON e.id=eq.employee_id
                ORDER BY eq.expiry_date, e.name
            """)

        if not data.empty:
            # Ablaufstatus hinzufügen
            today = date.today().isoformat()
            warn_date = (date.today() + timedelta(days=60)).isoformat()

            def expiry_status(exp_date):
                if not exp_date or str(exp_date) == "None":
                    return "♾️ Unbegrenzt"
                exp = str(exp_date)[:10]
                if exp < today:   return "❌ Abgelaufen"
                elif exp < warn_date: return "⚠️ Läuft bald ab"
                else:             return "✅ Gültig"

            data["Status"] = data["Gültig_bis"].apply(expiry_status)
            st.metric("Qualifikationen gesamt", len(data))
            st.dataframe(data.drop(columns=["id"]), use_container_width=True, height=400)
            csv = data.drop(columns=["id"]).to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 CSV-Export", csv, "qualifikationen.csv", "text/csv")
        else:
            st.info("Keine Qualifikationen gefunden.")

    with tabs[1]:
        employees = df_fn("SELECT id, employee_no || ' – ' || name AS label FROM employees WHERE active=1 ORDER BY name")
        if employees.empty:
            st.warning("Keine aktiven Mitarbeiter.")
            return

        with st.form("qual_form", clear_on_submit=True):
            emp_label = st.selectbox("Mitarbeiter *", employees["label"].tolist())
            qualification = st.selectbox("Qualifikation *", QUAL_TYPES)
            col1, col2, col3 = st.columns(3)
            issuer       = col1.text_input("Aussteller / Behörde")
            issued_date  = col2.date_input("Ausgestellt am", date.today())
            has_expiry   = col3.checkbox("Hat Ablaufdatum", value=True)
            expiry_date  = None
            if has_expiry:
                expiry_date = st.date_input("Gültig bis", date.today() + timedelta(days=365*3))
            cert_no = st.text_input("Zertifikat-Nummer")
            notes   = st.text_area("Notizen")
            submitted = st.form_submit_button("💾 Qualifikation speichern", type="primary")

        if submitted:
            eid = int(employees[employees["label"] == emp_label].iloc[0]["id"])
            run_fn("""INSERT INTO employee_qualifications
                (employee_id,qualification,issuer,issued_date,expiry_date,certificate_no,notes)
                VALUES(?,?,?,?,?,?,?)""",
                   (eid, qualification, issuer, issued_date.isoformat(),
                    expiry_date.isoformat() if expiry_date else None, cert_no, notes))
            log_fn("qualification_added", f"{emp_label}: {qualification}")
            st.success(f"✅ {qualification} für {emp_label} gespeichert!")
            st.rerun()

    with tabs[2]:
        st.subheader("⚠️ Ablaufende / abgelaufene Nachweise")
        today = date.today().isoformat()
        warn60 = (date.today() + timedelta(days=60)).isoformat()

        expiring = df_fn("""
            SELECT e.name AS Mitarbeiter, eq.qualification AS Qualifikation,
                   eq.expiry_date AS Gültig_bis, eq.certificate_no AS Zertifikat_Nr,
                   CAST(julianday(eq.expiry_date) - julianday('now') AS INTEGER) AS Tage_verbleibend
            FROM employee_qualifications eq JOIN employees e ON e.id=eq.employee_id
            WHERE eq.expiry_date IS NOT NULL
              AND eq.expiry_date <= ?
            ORDER BY eq.expiry_date
        """, (warn60,))

        if not expiring.empty:
            already_expired = expiring[expiring["Tage_verbleibend"] < 0]
            soon_expired    = expiring[expiring["Tage_verbleibend"] >= 0]

            if not already_expired.empty:
                st.error(f"❌ {len(already_expired)} Qualifikation(en) bereits ABGELAUFEN!")
                st.dataframe(already_expired, use_container_width=True)

            if not soon_expired.empty:
                st.warning(f"⚠️ {len(soon_expired)} Qualifikation(en) laufen in 60 Tagen ab!")
                st.dataframe(soon_expired, use_container_width=True)
        else:
            st.success("✅ Alle Qualifikationen sind aktuell.")

    with tabs[3]:
        st.subheader("Qualifikationsmatrix")
        matrix = df_fn("""
            SELECT e.name AS Mitarbeiter,
                   GROUP_CONCAT(eq.qualification, ' · ') AS Qualifikationen,
                   COUNT(*) AS Anzahl
            FROM employee_qualifications eq JOIN employees e ON e.id=eq.employee_id
            WHERE e.active=1
            GROUP BY e.id ORDER BY Anzahl DESC
        """)
        if not matrix.empty:
            st.dataframe(matrix, use_container_width=True)
        else:
            st.info("Noch keine Qualifikationen erfasst.")


# ─────────────────────────────────────────────────────────────
# 2. Schicht-Tauschbörse
# ─────────────────────────────────────────────────────────────

def page_shift_exchange(run_fn, df_fn, log_fn, current_user_fn) -> None:
    st.title("🔄 Schicht-Tauschbörse")
    st.caption("Mitarbeiter können Schichten zum Tausch anbieten oder übernehmen.")

    user = current_user_fn() or {}
    is_manager = user.get("role", "").lower() in ("admin", "manager", "administrator")

    tabs = st.tabs(["📋 Angebote", "➕ Schicht anbieten", "✅ Schicht übernehmen", "🔒 Genehmigen"])

    with tabs[0]:
        offers = df_fn("""
            SELECT se.id, s.shift_date AS Datum, s.start_time AS Von,
                   s.end_time AS Bis, s.shift_type AS Typ,
                   COALESCE(c.company,'–') AS Kunde, s.location AS Ort,
                   e_off.name AS Anbieter, se.reason AS Grund,
                   COALESCE(e_tak.name,'–') AS Übernommen_von,
                   se.status AS Status
            FROM shift_exchanges se
            JOIN shifts s ON s.id=se.shift_id
            JOIN employees e_off ON e_off.id=se.offered_by
            LEFT JOIN employees e_tak ON e_tak.id=se.taken_by
            LEFT JOIN customers c ON c.id=s.customer_id
            WHERE se.status != 'abgelehnt'
            ORDER BY s.shift_date
        """)
        if not offers.empty:
            c1, c2 = st.columns(2)
            c1.metric("Angebotene Schichten", len(offers[offers["Status"]=="angeboten"]))
            c2.metric("Übernommen (wartet auf Genehmigung)", len(offers[offers["Status"]=="übernommen"]))
            st.dataframe(offers.drop(columns=["id"]), use_container_width=True)
        else:
            st.info("Keine aktuellen Tauschangebote.")

    with tabs[1]:
        employees = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
        emp_label = st.selectbox("Meine Mitarbeiter-ID", employees["name"].tolist() if not employees.empty else ["—"])

        if not employees.empty:
            eid = int(employees[employees["name"] == emp_label].iloc[0]["id"])
            my_shifts = df_fn("""
                SELECT s.id, s.shift_date || ' ' || s.start_time || '–' || s.end_time ||
                       ' · ' || COALESCE(c.company,'') AS label
                FROM shifts s LEFT JOIN customers c ON c.id=s.customer_id
                WHERE s.employee_id=? AND s.shift_date >= ? AND s.status='geplant'
                ORDER BY s.shift_date
            """, (eid, date.today().isoformat()))

            if not my_shifts.empty:
                sel_shift = st.selectbox("Welche Schicht anbieten?", my_shifts["label"].tolist())
                sid = int(my_shifts[my_shifts["label"] == sel_shift].iloc[0]["id"])
                reason = st.text_area("Begründung (optional)")
                if st.button("📢 Schicht zum Tausch anbieten", type="primary"):
                    # Prüfen ob bereits angeboten
                    existing = df_fn("SELECT id FROM shift_exchanges WHERE shift_id=? AND status='angeboten'", (sid,))
                    if not existing.empty:
                        st.warning("Diese Schicht ist bereits zum Tausch angeboten.")
                    else:
                        run_fn("INSERT INTO shift_exchanges(shift_id,offered_by,reason) VALUES(?,?,?)",
                               (sid, eid, reason))
                        log_fn("shift_exchange_offered", f"shift={sid} by={emp_label}")
                        st.success("✅ Schicht zum Tausch angeboten!")
                        st.rerun()
            else:
                st.info("Keine zukünftigen Schichten vorhanden.")

    with tabs[2]:
        open_offers = df_fn("""
            SELECT se.id, s.shift_date AS Datum, s.start_time AS Von,
                   s.end_time AS Bis, s.shift_type AS Typ,
                   COALESCE(c.company,'–') AS Kunde, s.location AS Ort,
                   e_off.name AS Anbieter, se.reason AS Grund
            FROM shift_exchanges se
            JOIN shifts s ON s.id=se.shift_id
            JOIN employees e_off ON e_off.id=se.offered_by
            LEFT JOIN customers c ON c.id=s.customer_id
            WHERE se.status='angeboten' AND s.shift_date >= ?
            ORDER BY s.shift_date
        """, (date.today().isoformat(),))

        if not open_offers.empty:
            st.dataframe(open_offers.drop(columns=["id"]), use_container_width=True)
            employees2 = df_fn("SELECT id, name FROM employees WHERE active=1 ORDER BY name")
            emp2_label = st.selectbox("Ich übernehme als:", employees2["name"].tolist() if not employees2.empty else ["—"])
            sel_offer = st.selectbox("Welches Angebot übernehmen?",
                                      [f"{r['Datum']} {r['Von']}–{r['Bis']} · {r['Anbieter']} · {r['Kunde']}"
                                       for _, r in open_offers.iterrows()])

            if st.button("✋ Schicht übernehmen") and not employees2.empty:
                offer_idx = [f"{r['Datum']} {r['Von']}–{r['Bis']} · {r['Anbieter']} · {r['Kunde']}"
                             for _, r in open_offers.iterrows()].index(sel_offer)
                seid = int(open_offers.iloc[offer_idx]["id"])
                tak_id = int(employees2[employees2["name"] == emp2_label].iloc[0]["id"])
                run_fn("UPDATE shift_exchanges SET taken_by=?, status='übernommen' WHERE id=?",
                       (tak_id, seid))
                log_fn("shift_exchange_taken", f"exch={seid} by={emp2_label}")
                st.success("✅ Übernahme registriert – wartet auf Manager-Genehmigung.")
                st.rerun()
        else:
            st.info("Keine offenen Tauschangebote.")

    with tabs[3]:
        if not is_manager:
            st.warning("Nur Manager können Schichttausch genehmigen.")
            return
        pending = df_fn("""
            SELECT se.id, s.shift_date AS Datum, e_off.name AS Anbieter,
                   e_tak.name AS Übernimmt, se.reason AS Grund
            FROM shift_exchanges se
            JOIN shifts s ON s.id=se.shift_id
            JOIN employees e_off ON e_off.id=se.offered_by
            JOIN employees e_tak ON e_tak.id=se.taken_by
            WHERE se.status='übernommen'
        """)
        if not pending.empty:
            for _, row in pending.iterrows():
                seid = int(row["id"])
                with st.expander(f"🔄 {row['Datum']}: {row['Anbieter']} → {row['Übernimmt']}"):
                    col1, col2 = st.columns(2)
                    if col1.button("✅ Genehmigen", key=f"appr_{seid}", type="primary"):
                        # Schicht-Zuweisung wechseln
                        ex = df_fn("SELECT shift_id, taken_by FROM shift_exchanges WHERE id=?", (seid,))
                        if not ex.empty:
                            run_fn("UPDATE shifts SET employee_id=? WHERE id=?",
                                   (int(ex.iloc[0]["taken_by"]), int(ex.iloc[0]["shift_id"])))
                        run_fn("UPDATE shift_exchanges SET status='genehmigt', approved_by=? WHERE id=?",
                               (user.get("username","admin"), seid))
                        st.success("Genehmigt – Schicht zugewiesen!")
                        st.rerun()
                    if col2.button("❌ Ablehnen", key=f"rej_{seid}"):
                        run_fn("UPDATE shift_exchanges SET status='abgelehnt' WHERE id=?", (seid,))
                        st.rerun()
        else:
            st.success("✅ Keine ausstehenden Genehmigungen.")


# ─────────────────────────────────────────────────────────────
# 3. SEPA-Lastschrift XML (pain.008)
# ─────────────────────────────────────────────────────────────

def generate_sepa_pain008(mandates: list, creditor_iban: str, creditor_bic: str,
                            creditor_name: str, creditor_id: str,
                            collection_date: str) -> str:
    """
    Erstellt eine SEPA-Lastschrift XML-Datei (pain.008.003.02).
    mandates: List of dicts mit keys: name, iban, bic, amount, mandate_id, mandate_date, reference
    """
    total_amount = sum(float(m["amount"]) for m in mandates)
    count = len(mandates)
    msg_id = f"ByblosCRM-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    tx_lines = []
    for m in mandates:
        tx_lines.append(f"""
        <DrctDbtTxInf>
          <PmtId><EndToEndId>{m['reference']}</EndToEndId></PmtId>
          <InstdAmt Ccy="EUR">{float(m['amount']):.2f}</InstdAmt>
          <DrctDbtTx>
            <MndtRltdInf>
              <MndtId>{m['mandate_id']}</MndtId>
              <DtOfSgntr>{m['mandate_date']}</DtOfSgntr>
            </MndtRltdInf>
          </DrctDbtTx>
          <DbtrAgt><FinInstnId><BIC>{m['bic']}</BIC></FinInstnId></DbtrAgt>
          <Dbtr><Nm>{m['name']}</Nm></Dbtr>
          <DbtrAcct><Id><IBAN>{m['iban'].replace(' ','')}</IBAN></Id></DbtrAcct>
          <RmtInf><Ustrd>{m['reference']}</Ustrd></RmtInf>
        </DrctDbtTxInf>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.003.02">
  <CstmrDrctDbtInitn>
    <GrpHdr>
      <MsgId>{msg_id}</MsgId>
      <CreDtTm>{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}</CreDtTm>
      <NbOfTxs>{count}</NbOfTxs>
      <CtrlSum>{total_amount:.2f}</CtrlSum>
      <InitgPty><Nm>{creditor_name}</Nm></InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>{msg_id}-1</PmtInfId>
      <PmtMtd>DD</PmtMtd>
      <NbOfTxs>{count}</NbOfTxs>
      <CtrlSum>{total_amount:.2f}</CtrlSum>
      <PmtTpInf>
        <SvcLvl><Cd>SEPA</Cd></SvcLvl>
        <LclInstrm><Cd>CORE</Cd></LclInstrm>
        <SeqTp>RCUR</SeqTp>
      </PmtTpInf>
      <ReqdColltnDt>{collection_date}</ReqdColltnDt>
      <Cdtr><Nm>{creditor_name}</Nm></Cdtr>
      <CdtrAcct><Id><IBAN>{creditor_iban.replace(' ','')}</IBAN></Id></CdtrAcct>
      <CdtrAgt><FinInstnId><BIC>{creditor_bic}</BIC></FinInstnId></CdtrAgt>
      <CdtrSchmeId><Id><PrvtId><Othr>
        <Id>{creditor_id}</Id>
        <SchmeNm><Prtry>SEPA</Prtry></SchmeNm>
      </Othr></PrvtId></Id></CdtrSchmeId>
      {''.join(tx_lines)}
    </PmtInf>
  </CstmrDrctDbtInitn>
</Document>"""


def page_sepa_export(run_fn, df_fn, get_setting_fn) -> None:
    st.title("🏦 SEPA-Lastschrift XML")
    st.caption("Erstelle SEPA-Direktlastschriften (pain.008) für offene Rechnungen mit SEPA-Mandat.")

    tabs = st.tabs(["📋 Rechnungen auswählen", "⚙️ Gläubiger-Einstellungen", "ℹ️ Hinweise"])

    with tabs[0]:
        creditor_iban = get_setting_fn("company_iban", "")
        creditor_bic  = get_setting_fn("company_bic", "")
        creditor_name = get_setting_fn("company_name", "Byblos Sicherheitsdienst")
        creditor_id   = get_setting_fn("sepa_creditor_id", "DE98ZZZ09999999999")

        if not creditor_iban:
            st.warning("⚠️ Bitte zuerst IBAN und BIC in den Einstellungen hinterlegen.")
            return

        col1, col2 = st.columns(2)
        collection_date = col1.date_input("Einzugsdatum", date.today() + timedelta(days=5))
        month_filter    = col2.text_input("Rechnungsmonat (leer = alle offenen)", "")

        open_inv = df_fn("""
            SELECT i.id, i.invoice_no, c.company AS Kunde,
                   ROUND(i.gross_total - i.paid_amount, 2) AS Betrag
            FROM invoices i JOIN customers c ON c.id=i.customer_id
            WHERE i.status IN ('offen','ueberfaellig')
              AND ROUND(i.gross_total - i.paid_amount, 2) > 0
        """ + (f" AND substr(i.invoice_date,1,7)='{month_filter}'" if month_filter else "") +
            " ORDER BY i.due_date")

        if open_inv.empty:
            st.info("Keine offenen Rechnungen.")
            return

        st.dataframe(open_inv, use_container_width=True)
        total = float(open_inv["Betrag"].sum())
        st.metric("Gesamt-Lastschriftbetrag", fmt_eur(total))

        st.divider()
        st.subheader("SEPA-Mandate (Beispiel – bitte anpassen)")
        st.caption("In der Produktionsumgebung müssen Mandatsdaten je Kunde gespeichert sein.")

        mandates = []
        for _, r in open_inv.head(10).iterrows():
            with st.expander(f"{r['Kunde']} – {fmt_eur(float(r['Betrag']))}"):
                a, b = st.columns(2)
                iban_m = a.text_input("IBAN Debitor", "", key=f"iban_{r['id']}")
                bic_m  = b.text_input("BIC Debitor", "", key=f"bic_{r['id']}")
                mand_id = a.text_input("Mandat-ID", f"M-{r['invoice_no']}", key=f"mid_{r['id']}")
                mand_dt = b.text_input("Mandatsdatum", "2024-01-01", key=f"mdt_{r['id']}")
                if iban_m and bic_m:
                    mandates.append({
                        "name": str(r["Kunde"]),
                        "iban": iban_m,
                        "bic": bic_m,
                        "amount": float(r["Betrag"]),
                        "mandate_id": mand_id,
                        "mandate_date": mand_dt,
                        "reference": str(r["invoice_no"]),
                    })

        if mandates:
            if st.button(f"📄 SEPA-XML für {len(mandates)} Lastschriften erstellen", type="primary"):
                xml = generate_sepa_pain008(mandates, creditor_iban, creditor_bic,
                                             creditor_name, creditor_id,
                                             collection_date.isoformat())
                fname = f"sepa_lastschrift_{collection_date.isoformat()}.xml"
                st.download_button("📥 SEPA-XML herunterladen",
                                   xml.encode("utf-8"), fname, "application/xml")
                st.success(f"✅ SEPA-XML mit {len(mandates)} Lastschriften ({fmt_eur(sum(m['amount'] for m in mandates))} gesamt)")
        else:
            st.info("Bitte IBAN und BIC für mindestens eine Rechnung eingeben.")

    with tabs[1]:
        with st.form("sepa_settings"):
            sepa_id = st.text_input("Gläubiger-ID (beim Kreditinstitut beantragen)",
                                     get_setting_fn("sepa_creditor_id", "DE98ZZZ09999999999"))
            st.caption("Die Gläubiger-ID wird bei Ihrer Bank/Sparkasse beantragt.")
            if st.form_submit_button("💾 Speichern"):
                run_fn("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
                       ("sepa_creditor_id", sepa_id))
                st.success("Gespeichert.")

    with tabs[2]:
        st.markdown("""
**SEPA-Lastschrift (pain.008) – Wichtige Hinweise:**

1. **Gläubiger-ID** muss bei Ihrer Bank beantragt werden
2. **Mandatserteilung**: Jeder Schuldner muss ein SEPA-Mandat unterzeichnen
3. **Vorlaufzeit**: CORE-Lastschriften mind. 5 Bankarbeitstage vorher einreichen
4. **Erstlastschrift vs. Folgelastschrift**: Unterschiedliche Vorlaufzeiten
5. **Widerspruchsrecht**: Schuldner kann 8 Wochen widersprechen

⚠️ Diese XML-Datei ist für die Einreichung bei Ihrer Bank gedacht. 
Bitte prüfen Sie die Datei mit Ihrer Bank oder einem Zahlungsdienstleister.

**Rechtlicher Hinweis:** Nicht mit Steuerberater oder Rechtanwalt abgestimmt. 
Eigenverantwortliche Nutzung.
        """)


# ─────────────────────────────────────────────────────────────
# 4. Kostenvoranschlag / Kalkulation
# ─────────────────────────────────────────────────────────────

def page_cost_estimate(run_fn, df_fn, next_number_fn, log_fn, get_setting_fn) -> None:
    st.title("🧮 Kostenvoranschlag & Kalkulation")
    st.caption("Kosten vor Angebotsabgabe kalkulieren. Basis für Angebotspreis.")

    tabs = st.tabs(["📋 Übersicht", "➕ Neue Kalkulation", "📊 Preiskalkulator"])

    with tabs[0]:
        estimates = df_fn("""
            SELECT ce.id, ce.estimate_no AS Nr, ce.title AS Titel,
                   COALESCE(c.company,'–') AS Kunde,
                   ce.estimated_hours AS Stunden, ce.hourly_rate AS Stundensatz,
                   ce.gross_total AS Preis_EUR, ce.status AS Status,
                   ce.valid_until AS Gültig_bis
            FROM cost_estimates ce LEFT JOIN customers c ON c.id=ce.customer_id
            ORDER BY ce.created_at DESC
        """)
        if not estimates.empty:
            st.dataframe(estimates.drop(columns=["id"]), use_container_width=True)
        else:
            st.info("Noch keine Kalkulationen.")

    with tabs[1]:
        customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
        with st.form("estimate_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            est_no = col1.text_input("Kalkulations-Nr.", next_number_fn("cost_estimates","estimate_no","KALK-"))
            title  = col2.text_input("Titel / Projektname *")
            cust_label = st.selectbox("Kunde", ["—"] + (customers["label"].tolist() if not customers.empty else []))
            desc = st.text_area("Beschreibung der Leistung")

            st.subheader("Kalkulation")
            a, b = st.columns(2)
            hours    = a.number_input("Kalkulierte Stunden", min_value=0.0, value=40.0, step=4.0)
            rate     = b.number_input("Stundensatz (€)", min_value=0.0, value=21.0, step=0.5)
            material = a.number_input("Material / Fremdkosten (€)", min_value=0.0, value=0.0, step=50.0)
            overhead = b.number_input("Gemeinkosten-Zuschlag (%)", min_value=0.0, value=20.0, step=1.0)
            margin   = a.number_input("Gewinnmarge (%)", min_value=0.0, value=15.0, step=1.0)
            vat_rate = b.number_input("MwSt (%)", min_value=0.0, value=19.0, step=1.0)

            # Live-Berechnung
            labor_cost   = hours * rate
            overhead_amt = (labor_cost + material) * overhead / 100
            cost_total   = labor_cost + material + overhead_amt
            profit_amt   = cost_total * margin / 100
            net_total    = cost_total + profit_amt
            vat_amt      = net_total * vat_rate / 100
            gross_total  = net_total + vat_amt

            st.info(f"""
**Kalkulations-Ergebnis:**
- Personalkosten: {fmt_eur(labor_cost)}
- Material: {fmt_eur(material)}
- Gemeinkosten ({overhead:.0f}%): {fmt_eur(overhead_amt)}
- Selbstkosten: {fmt_eur(cost_total)}
- Gewinn ({margin:.0f}%): {fmt_eur(profit_amt)}
- **Netto: {fmt_eur(net_total)}** · MwSt: {fmt_eur(vat_amt)} · **Brutto: {fmt_eur(gross_total)}**
            """)

            valid_until = st.date_input("Gültig bis", date.today() + timedelta(days=30))
            notes = st.text_area("Notizen")
            status = st.selectbox("Status", ["entwurf","freigegeben","abgelehnt","umgesetzt"])
            submitted = st.form_submit_button("💾 Kalkulation speichern", type="primary")

        if submitted and title:
            cid = None
            if cust_label != "—" and not customers.empty:
                match = customers[customers["label"] == cust_label]
                if not match.empty:
                    cid = int(match.iloc[0]["id"])
            run_fn("""INSERT INTO cost_estimates(estimate_no,customer_id,title,description,
                      estimated_hours,hourly_rate,material_cost,overhead_pct,profit_margin_pct,
                      net_total,vat_rate,gross_total,status,valid_until,notes)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (est_no, cid, title, desc, hours, rate, material, overhead,
                    margin, net_total, vat_rate, gross_total, status,
                    valid_until.isoformat(), notes))
            log_fn("cost_estimate_created", title)
            st.success(f"✅ Kalkulation '{title}' gespeichert! Angebotspreis: {fmt_eur(gross_total)}")
            st.rerun()

    with tabs[2]:
        st.subheader("📊 Interaktiver Preiskalkulator")
        col1, col2 = st.columns(2)
        hours_k   = col1.slider("Stunden", 1, 500, 40)
        rate_k    = col2.slider("Stundensatz (€)", 15, 60, 21)
        overhead_k = col1.slider("Gemeinkosten (%)", 0, 50, 20)
        margin_k  = col2.slider("Gewinnmarge (%)", 0, 40, 15)
        vat_k     = col1.slider("MwSt (%)", 0, 20, 19)
        material_k = col2.number_input("Material (€)", 0.0, step=50.0)

        labor_k = hours_k * rate_k
        ohamt_k = (labor_k + material_k) * overhead_k / 100
        cost_k  = labor_k + material_k + ohamt_k
        profit_k = cost_k * margin_k / 100
        net_k   = cost_k + profit_k
        vat_amt_k = net_k * vat_k / 100
        gross_k = net_k + vat_amt_k

        c1, c2, c3 = st.columns(3)
        c1.metric("Selbstkosten", fmt_eur(cost_k))
        c2.metric("Netto-Angebotspreis", fmt_eur(net_k))
        c3.metric("Brutto-Angebotspreis", fmt_eur(gross_k))

        hourly_price = gross_k / hours_k if hours_k > 0 else 0
        st.caption(f"Effektiver Stundensatz (Brutto): **{hourly_price:.2f} €/Std.**")


# ─────────────────────────────────────────────────────────────
# 5. REST-API / JSON-Daten-Export
# ─────────────────────────────────────────────────────────────

def page_api_center(run_fn, df_fn, get_setting_fn, set_setting_fn) -> None:
    st.title("🔌 API & Datenexport-Center")
    st.caption("JSON-Endpunkte für Drittsysteme und Integrationen.")

    import secrets as sec

    tabs = st.tabs(["📤 JSON-Export", "🔑 API-Keys", "📖 Dokumentation"])

    with tabs[0]:
        st.subheader("Daten als JSON exportieren")
        endpoint = st.selectbox("Datensatz", [
            "Kunden", "Offene Rechnungen", "Mitarbeiter (aktiv)",
            "Schichten (aktueller Monat)", "Ausgaben (aktueller Monat)",
            "KPIs (täglich)", "Lieferanten",
        ])

        month_now = date.today().strftime("%Y-%m")
        queries = {
            "Kunden": ("SELECT id,customer_no,company,contact_person,email,phone,street,zip_city,country FROM customers ORDER BY company", ()),
            "Offene Rechnungen": ("SELECT i.invoice_no,c.company,i.invoice_date,i.due_date,ROUND(i.gross_total-i.paid_amount,2) AS offen_eur,i.status FROM invoices i JOIN customers c ON c.id=i.customer_id WHERE i.status IN ('offen','ueberfaellig') ORDER BY i.due_date", ()),
            "Mitarbeiter (aktiv)": ("SELECT employee_no,name,phone,email FROM employees WHERE active=1 ORDER BY name", ()),
            "Schichten (aktueller Monat)": (f"SELECT s.shift_date,s.start_time,s.end_time,COALESCE(e.name,'unbesetzt') AS mitarbeiter,COALESCE(c.company,'') AS kunde,s.location,s.shift_type,s.status FROM shifts s LEFT JOIN employees e ON e.id=s.employee_id LEFT JOIN customers c ON c.id=s.customer_id WHERE substr(s.shift_date,1,7)=? ORDER BY s.shift_date", (month_now,)),
            "Ausgaben (aktueller Monat)": (f"SELECT expense_no,expense_date,description,category,gross_amount,status FROM expenses WHERE bwa_month=? ORDER BY expense_date", (month_now,)),
            "KPIs (täglich)": ("SELECT * FROM daily_kpis ORDER BY kpi_date DESC LIMIT 30", ()),
            "Lieferanten": ("SELECT supplier_no,name,email,phone FROM suppliers ORDER BY name", ()),
        }

        q, p = queries[endpoint]
        data = df_fn(q, p)

        if not data.empty:
            st.metric("Datensätze", len(data))
            st.dataframe(data.head(20), use_container_width=True)
            json_str = data.to_json(orient="records", force_ascii=False, indent=2,
                                     date_format="iso")
            st.download_button(
                f"📥 {endpoint} als JSON",
                json_str.encode("utf-8"),
                f"byblos_{endpoint.lower().replace(' ','_').replace('(','').replace(')','')}.json",
                "application/json"
            )
        else:
            st.info("Keine Daten vorhanden.")

    with tabs[1]:
        st.subheader("API-Keys verwalten")
        st.caption("API-Keys erlauben Drittsystemen Zugriff auf JSON-Daten.")

        keys = df_fn("SELECT id, key_name, LEFT(api_key,8)||'...' AS Key_Vorschau, permissions AS Berechtigungen, active AS Aktiv, last_used AS Zuletzt_genutzt FROM api_keys ORDER BY created_at DESC")
        if not keys.empty:
            st.dataframe(keys.drop(columns=["id"]), use_container_width=True)

        with st.form("api_key_form", clear_on_submit=True):
            key_name = st.text_input("Key-Name (z.B. 'Buchhaltungssoftware')")
            perms    = st.multiselect("Berechtigungen", ["read","write","admin"], default=["read"])
            if st.form_submit_button("🔑 Neuen API-Key erstellen"):
                new_key = f"byb_{sec.token_hex(24)}"
                run_fn("INSERT INTO api_keys(key_name,api_key,permissions) VALUES(?,?,?)",
                       (key_name, new_key, ",".join(perms)))
                st.success(f"✅ API-Key erstellt:")
                st.code(new_key, language="text")
                st.warning("⚠️ Den Key jetzt kopieren – er wird nur einmal angezeigt!")

        if not keys.empty:
            del_sel = st.selectbox("Key deaktivieren", df_fn("SELECT id, key_name FROM api_keys WHERE active=1")["key_name"].tolist() if not df_fn("SELECT id, key_name FROM api_keys WHERE active=1").empty else ["—"])
            if del_sel != "—" and st.button("⛔ Key deaktivieren"):
                run_fn("UPDATE api_keys SET active=0 WHERE key_name=?", (del_sel,))
                st.success(f"Key '{del_sel}' deaktiviert.")
                st.rerun()

    with tabs[2]:
        st.subheader("📖 API-Dokumentation")
        st.markdown("""
**Byblos CRM JSON-API (einfach)**

Die JSON-Exporte können manuell heruntergeladen oder per Skript abgerufen werden.

**Beispiel: Kunden als JSON abrufen**
```python
import requests, json

# Lokaler Server
url = "http://localhost:8501"  # App läuft lokal
# Für automatischen Export: byblos_daily.sh um JSON-Export erweitern

# Oder direkt aus Python auf die DB zugreifen:
import sqlite3, json
conn = sqlite3.connect('byblos_crm.db')
cursor = conn.execute('SELECT * FROM customers')
data = [dict(zip([d[0] for d in cursor.description], row)) for row in cursor.fetchall()]
print(json.dumps(data, ensure_ascii=False, indent=2))
```

**Integration mit Drittsystemen:**
- Exportierte JSON-Dateien können direkt in Excel (Power Query) importiert werden
- DATEV: CSV-Export im DATEV-Mapping-Bereich
- Buchhaltungssoftware: JSON-Export + eigenes Mapping
- ERP-Systeme: API-Keys + Webhook (geplant für v3)
        """)
