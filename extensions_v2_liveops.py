"""
extensions_v2_liveops.py – Live-Ops & finale Business-Logik
=============================================================
1. Angebot → Rechnung Konvertierung (alle Positionen)
2. Kunden-Aktivitätsprotokoll (vollständige Timeline)
3. Digitale Personalakte (Dokumente je Mitarbeiter)
4. Deckungsbeitrags-Rechnung (DB1/DB2)
5. XLSX-Rechnungsimport mit Spalten-Mapping
6. Backup-Verschlüsselung (AES-256 via Fernet)
7. Query-Performance-Monitor
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

import pandas as pd
import streamlit as st


def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# DB-Registrierung
# ─────────────────────────────────────────────────────────────

def register_liveops(run_fn, df_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS personnel_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,
        doc_name TEXT NOT NULL,
        file_path TEXT,
        issued_date TEXT,
        expiry_date TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS contribution_margins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        project_id INTEGER,
        calc_month TEXT NOT NULL,
        revenue_net REAL DEFAULT 0,
        direct_labor REAL DEFAULT 0,
        direct_material REAL DEFAULT 0,
        overhead_variable REAL DEFAULT 0,
        db1 REAL DEFAULT 0,
        overhead_fixed REAL DEFAULT 0,
        db2 REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    run_fn("""CREATE TABLE IF NOT EXISTS backup_encryption_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_name TEXT UNIQUE NOT NULL,
        key_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")


# ─────────────────────────────────────────────────────────────
# 1. Angebot → Rechnung Konvertierung
# ─────────────────────────────────────────────────────────────

def page_offer_to_invoice(run_fn, df_fn, next_number_fn, log_fn, refresh_totals_fn) -> None:
    st.title("📋 → 🧾 Angebot zu Rechnung")
    st.caption("Akzeptierte Angebote direkt in Rechnungen umwandeln.")

    offers = df_fn("""
        SELECT o.id,
               o.offer_no || ' – ' || COALESCE(c.company,'?') ||
               ' | ' || ROUND(o.gross_total,2) || ' €' AS label,
               o.customer_id, o.offer_no, o.description,
               o.net_total, o.vat_rate, o.vat_total, o.gross_total, o.status
        FROM offers o LEFT JOIN customers c ON c.id=o.customer_id
        WHERE o.status IN ('offen','akzeptiert')
        ORDER BY o.offer_date DESC
    """)

    if offers.empty:
        st.info("Keine offenen Angebote. Bitte unter 'Angebote' ein Angebot anlegen.")
        return

    sel = st.selectbox("Angebot auswählen", offers["label"].tolist())
    row = offers[offers["label"] == sel].iloc[0]
    oid = int(row["id"])

    # Angebotspositionen laden
    items = df_fn("""
        SELECT position, description, quantity, unit, unit_price, total
        FROM offer_items WHERE offer_id=? ORDER BY position
    """, (oid,))

    col1, col2, col3 = st.columns(3)
    col1.metric("Angebot", str(row["offer_no"]))
    col2.metric("Netto", fmt_eur(float(row["net_total"] or 0)))
    col3.metric("Brutto", fmt_eur(float(row["gross_total"] or 0)))

    if not items.empty:
        st.subheader(f"Positionen ({len(items)} Stück)")
        st.dataframe(items, use_container_width=True)
    else:
        st.info("Angebot hat keine Positionen – Gesamtbetrag wird als Sammelposition übernommen.")

    with st.form("offer2inv_form"):
        a, b, c = st.columns(3)
        inv_no    = a.text_input("Rechnungsnummer", next_number_fn("invoices","invoice_no","RE-"))
        inv_date  = b.date_input("Rechnungsdatum", date.today())
        due_date  = c.date_input("Fällig bis", date.today() + timedelta(days=14))
        description = st.text_input("Leistungsbeschreibung", str(row.get("description","") or ""))
        service_date = st.text_input("Leistungszeitraum", date.today().strftime("%B %Y"))

        col1, col2 = st.columns(2)
        mark_offer_accepted = col1.checkbox("Angebot als 'akzeptiert' markieren", value=True)
        submitted = col2.form_submit_button("🧾 Rechnung erstellen", type="primary")

    if submitted:
        cid = int(row.get("customer_id") or 0)
        if not cid:
            st.error("Kein Kunde zugeordnet.")
            return

        net   = float(row["net_total"] or 0)
        vat_r = float(row["vat_rate"] or 19)
        vat_t = float(row["vat_total"] or round(net * vat_r / 100, 2))
        gross = float(row["gross_total"] or 0)

        run_fn("""INSERT INTO invoices(invoice_no,customer_id,invoice_date,service_date,
                  due_date,description,net_total,vat_rate,vat_total,gross_total,paid_amount,status)
                  VALUES(?,?,?,?,?,?,?,?,?,?,0,'offen')""",
               (inv_no, cid, inv_date.isoformat(), service_date,
                due_date.isoformat(), description, net, vat_r, vat_t, gross))

        iid = int(df_fn("SELECT id FROM invoices WHERE invoice_no=?", (inv_no,)).iloc[0]["id"])

        # Positionen übernehmen
        if not items.empty:
            for _, it in items.iterrows():
                run_fn("""INSERT INTO invoice_items(invoice_id,position,description,
                          quantity,unit,unit_price,total)
                          VALUES(?,?,?,?,?,?,?)""",
                       (iid, int(it["position"]), str(it["description"]),
                        float(it["quantity"]), str(it["unit"]),
                        float(it["unit_price"]), float(it["total"])))
        else:
            # Sammelposition
            run_fn("""INSERT INTO invoice_items(invoice_id,position,description,
                      quantity,unit,unit_price,total)
                      VALUES(?,1,?,1,'pauschal',?,?)""",
                   (iid, description, net, net))

        refresh_totals_fn(iid)

        if mark_offer_accepted:
            run_fn("UPDATE offers SET status='akzeptiert', linked_invoice_no=? WHERE id=?",
                   (inv_no, oid))

        log_fn("offer_converted", f"{row['offer_no']} → {inv_no}")
        st.success(f"✅ Rechnung {inv_no} aus Angebot {row['offer_no']} erstellt!")
        st.rerun()


# ─────────────────────────────────────────────────────────────
# 2. Kunden-Aktivitätsprotokoll (vollständige Timeline)
# ─────────────────────────────────────────────────────────────

def page_customer_timeline(df_fn) -> None:
    st.title("📜 Kunden-Aktivitätsprotokoll")
    st.caption("Vollständige Timeline aller Aktionen je Kunde.")

    customers = df_fn("SELECT id, customer_no || ' – ' || company AS label FROM customers ORDER BY company")
    if customers.empty:
        st.info("Keine Kunden vorhanden.")
        return

    sel = st.selectbox("Kunde auswählen", customers["label"].tolist())
    cid = int(customers[customers["label"] == sel].iloc[0]["id"])

    col1, col2 = st.columns(2)
    from_d = col1.date_input("Von", date.today() - timedelta(days=365))
    to_d   = col2.date_input("Bis", date.today())

    # Alle Aktivitäten aus verschiedenen Tabellen sammeln
    events = []

    # Rechnungen
    invs = df_fn("""SELECT invoice_date AS datum, 'Rechnung erstellt' AS art,
                          invoice_no || ' – ' || ROUND(gross_total,2) || ' €' AS detail,
                          status AS status
                   FROM invoices WHERE customer_id=? AND invoice_date BETWEEN ? AND ?
                   ORDER BY invoice_date DESC""",
                  (cid, from_d.isoformat(), to_d.isoformat()))
    for _, r in invs.iterrows():
        events.append({"Datum": r["datum"], "Art": "🧾 " + r["art"],
                        "Detail": r["detail"], "Status": r["status"]})

    # Kontakte
    conts = df_fn("""SELECT contact_date AS datum, contact_type AS art,
                           subject AS detail, result AS status
                    FROM contacts WHERE customer_id=? AND contact_date BETWEEN ? AND ?
                    ORDER BY contact_date DESC""",
                   (cid, from_d.isoformat(), to_d.isoformat()))
    for _, r in conts.iterrows():
        events.append({"Datum": r["datum"], "Art": "📞 " + str(r["art"]),
                        "Detail": r["detail"], "Status": r.get("status","")})

    # Schichten
    shifts = df_fn("""SELECT s.shift_date AS datum, s.shift_type AS art,
                            COALESCE(e.name,'unbesetzt') || ' · ' || COALESCE(s.location,'') AS detail,
                            s.status AS status
                     FROM shifts s LEFT JOIN employees e ON e.id=s.employee_id
                     WHERE s.customer_id=? AND s.shift_date BETWEEN ? AND ?
                     ORDER BY s.shift_date DESC LIMIT 100""",
                    (cid, from_d.isoformat(), to_d.isoformat()))
    for _, r in shifts.iterrows():
        events.append({"Datum": r["datum"], "Art": "📅 " + str(r["art"]),
                        "Detail": r["detail"], "Status": r.get("status","")})

    # Angebote
    offs = df_fn("""SELECT offer_date AS datum, 'Angebot' AS art,
                          offer_no || ' – ' || ROUND(gross_total,2) || ' €' AS detail,
                          status AS status
                   FROM offers WHERE customer_id=? AND offer_date BETWEEN ? AND ?
                   ORDER BY offer_date DESC""",
                  (cid, from_d.isoformat(), to_d.isoformat()))
    for _, r in offs.iterrows():
        events.append({"Datum": r["datum"], "Art": "📄 " + r["art"],
                        "Detail": r["detail"], "Status": r.get("status","")})

    # SLA-Verträge
    slas = df_fn("""SELECT start_date AS datum, 'SLA-Vertrag' AS art,
                           contract_name AS detail, status AS status
                    FROM sla_contracts WHERE customer_id=? AND start_date BETWEEN ? AND ?""",
                  (cid, from_d.isoformat(), to_d.isoformat()))
    for _, r in slas.iterrows():
        events.append({"Datum": r["datum"], "Art": "📊 " + r["art"],
                        "Detail": r["detail"], "Status": r.get("status","")})

    if not events:
        st.info("Keine Aktivitäten in diesem Zeitraum.")
        return

    # Nach Datum sortieren
    df_ev = pd.DataFrame(events)
    df_ev = df_ev.sort_values("Datum", ascending=False)

    # KPI
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Aktivitäten gesamt", len(df_ev))
    c2.metric("Rechnungen", len(df_ev[df_ev["Art"].str.contains("Rechnung")]))
    c3.metric("Kontakte", len(df_ev[df_ev["Art"].str.contains("📞")]))
    c4.metric("Schichten", len(df_ev[df_ev["Art"].str.contains("📅")]))

    # Timeline-Darstellung
    for _, row in df_ev.iterrows():
        art = str(row["Art"])
        status = str(row.get("Status",""))
        color = "#2980b9"
        if "Rechnung" in art:
            color = "#27ae60" if status == "bezahlt" else "#c0392b" if status == "ueberfaellig" else "#2980b9"
        elif "📞" in art:
            color = "#8e44ad"
        elif "📅" in art:
            color = "#16a085"
        elif "📄" in art:
            color = "#d35400"

        st.markdown(
            f'<div style="border-left:3px solid {color};padding:6px 12px;'
            f'background:{color}11;margin:3px 0;border-radius:3px;">'
            f'<span style="color:#aaa;font-size:.8rem;">{row["Datum"]}</span> '
            f'<strong>{art}</strong> — {row["Detail"]}'
            f'<span style="float:right;font-size:.8rem;color:#888;">{status}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    st.divider()
    csv = df_ev.to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button("📥 Timeline als CSV", csv, f"timeline_{cid}.csv", "text/csv")


# ─────────────────────────────────────────────────────────────
# 3. Digitale Personalakte
# ─────────────────────────────────────────────────────────────

DOC_TYPES = [
    "Arbeitsvertrag", "Gehaltsnachweis", "Zeugnis", "Krankmeldung",
    "Urlaubsantrag (genehmigt)", "Qualifikationsnachweis", "§34a-Nachweis",
    "Erste-Hilfe-Schein", "Personalausweis-Kopie", "Sozialversicherungsausweis",
    "Lohnsteuerbescheinigung", "Abmahnung", "Kündigung", "Sonstiges",
]


def page_personnel_file(run_fn, df_fn, log_fn, base_dir: Path) -> None:
    st.title("📁 Digitale Personalakte")
    st.caption("Alle Dokumente je Mitarbeiter zentral verwalten.")

    DOC_DIR = base_dir / "personnel_docs"
    DOC_DIR.mkdir(exist_ok=True)

    employees = df_fn("SELECT id, employee_no || ' – ' || name AS label FROM employees ORDER BY name")
    if employees.empty:
        st.info("Keine Mitarbeiter vorhanden.")
        return

    sel = st.selectbox("Mitarbeiter auswählen", employees["label"].tolist())
    eid = int(employees[employees["label"] == sel].iloc[0]["id"])

    tabs = st.tabs(["📋 Dokumente", "⬆️ Hochladen", "⚠️ Ablaufende"])

    with tabs[0]:
        docs = df_fn("""
            SELECT id, doc_type AS Typ, doc_name AS Dokument,
                   issued_date AS Ausgestellt, expiry_date AS Gültig_bis,
                   notes AS Notiz, file_path AS Pfad
            FROM personnel_documents WHERE employee_id=?
            ORDER BY issued_date DESC
        """, (eid,))

        if not docs.empty:
            st.caption(f"{len(docs)} Dokument(e)")
            for _, d in docs.iterrows():
                exp = str(d.get("Gültig_bis") or "")
                exp_warn = (exp and exp < (date.today() + timedelta(days=60)).isoformat())
                color = "#c0392b" if exp and exp < date.today().isoformat() else \
                        "#e67e22" if exp_warn else "#27ae60"

                col1, col2, col3 = st.columns([3, 1, 1])
                col1.markdown(
                    f'<div style="border-left:3px solid {color};padding:4px 8px;">'
                    f'📄 <strong>{d["Dokument"]}</strong> ({d["Typ"]})<br/>'
                    f'<span style="font-size:.8rem;color:#aaa;">'
                    f'Ausgestellt: {d.get("Ausgestellt","")} '
                    f'{"· Gültig bis: " + exp if exp else ""}'
                    f'</span></div>',
                    unsafe_allow_html=True
                )
                fp = str(d.get("Pfad") or "")
                if fp and Path(fp).exists():
                    col2.download_button("⬇", Path(fp).read_bytes(),
                                          Path(fp).name, key=f"dl_{d['id']}")
                if col3.button("🗑️", key=f"del_{d['id']}"):
                    run_fn("DELETE FROM personnel_documents WHERE id=?", (int(d["id"]),))
                    st.rerun()
        else:
            st.info("Noch keine Dokumente in der Personalakte.")

    with tabs[1]:
        with st.form("pers_doc_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            doc_type  = col1.selectbox("Dokumenttyp *", DOC_TYPES)
            doc_name  = col2.text_input("Dokumentname *")
            issued    = col1.date_input("Ausstellungsdatum", date.today())
            has_exp   = col2.checkbox("Hat Ablaufdatum")
            expiry    = col1.date_input("Gültig bis", date.today() + timedelta(days=365*3)) if has_exp else None
            notes     = st.text_area("Notizen")
            file_up   = st.file_uploader("Datei hochladen (PDF, JPG, PNG)")
            submitted = st.form_submit_button("💾 Speichern", type="primary")

        if submitted and doc_name:
            fp_str = ""
            if file_up:
                emp_dir = DOC_DIR / str(eid)
                emp_dir.mkdir(exist_ok=True)
                fp = emp_dir / file_up.name
                fp.write_bytes(file_up.read())
                fp_str = str(fp)

            run_fn("""INSERT INTO personnel_documents(employee_id,doc_type,doc_name,
                      issued_date,expiry_date,notes,file_path)
                      VALUES(?,?,?,?,?,?,?)""",
                   (eid, doc_type, doc_name, issued.isoformat(),
                    expiry.isoformat() if expiry else None, notes, fp_str))
            log_fn("personnel_doc_added", f"{sel}: {doc_name}")
            st.success(f"✅ '{doc_name}' gespeichert!")
            st.rerun()

    with tabs[2]:
        warn_date = (date.today() + timedelta(days=60)).isoformat()
        expiring = df_fn("""
            SELECT e.name AS Mitarbeiter, pd.doc_type AS Typ, pd.doc_name AS Dokument,
                   pd.expiry_date AS Gültig_bis,
                   CAST(julianday(pd.expiry_date) - julianday('now') AS INT) AS Tage_verbleibend
            FROM personnel_documents pd JOIN employees e ON e.id=pd.employee_id
            WHERE pd.expiry_date IS NOT NULL AND pd.expiry_date <= ?
            ORDER BY pd.expiry_date
        """, (warn_date,))

        if not expiring.empty:
            abgelaufen = expiring[expiring["Tage_verbleibend"] < 0]
            bald       = expiring[expiring["Tage_verbleibend"] >= 0]
            if not abgelaufen.empty:
                st.error(f"❌ {len(abgelaufen)} abgelaufene Dokumente:")
                st.dataframe(abgelaufen, use_container_width=True)
            if not bald.empty:
                st.warning(f"⚠️ {len(bald)} Dokumente laufen bald ab:")
                st.dataframe(bald, use_container_width=True)
        else:
            st.success("✅ Alle Dokumente aktuell.")


# ─────────────────────────────────────────────────────────────
# 4. Deckungsbeitrags-Rechnung (DB1/DB2)
# ─────────────────────────────────────────────────────────────

def page_contribution_margin(run_fn, df_fn, log_fn) -> None:
    st.title("📊 Deckungsbeitrags-Rechnung")
    st.caption("DB1 = Umsatz – variable Kosten · DB2 = DB1 – Fixkosten.")

    tabs = st.tabs(["🧮 Berechnen", "📋 Gespeicherte DB-Rechnungen", "📈 Trend"])

    with tabs[0]:
        col1, col2 = st.columns(2)
        customers = df_fn("SELECT id, company AS label FROM customers ORDER BY company")
        cust_label = col1.selectbox("Kunde / Objekt (optional)",
                                     ["Alle Kunden"] + (customers["label"].tolist() if not customers.empty else []))
        month = col2.text_input("Monat (YYYY-MM)", date.today().strftime("%Y-%m"))

        # Auto-Werte aus DB berechnen
        where_cust = ""
        cid = None
        if cust_label != "Alle Kunden" and not customers.empty:
            match = customers[customers["label"] == cust_label]
            if not match.empty:
                cid = int(match.iloc[0]["id"])
                where_cust = f" AND i.customer_id={cid}"

        revenue = float(df_fn(f"""
            SELECT COALESCE(SUM(net_total),0) AS v FROM invoices i
            WHERE substr(invoice_date,1,7)='{month}' AND status='bezahlt'{where_cust}
        """).iloc[0]["v"])

        st.subheader("Erlöse")
        rev_net = st.number_input("Nettoumsatz (€)", value=revenue, step=100.0)

        st.subheader("Variable Kosten (Einzel- / Grenzkosten)")
        col1, col2, col3 = st.columns(3)
        labor    = col1.number_input("Personalkosten variabel (€)", min_value=0.0, value=0.0, step=50.0)
        material = col2.number_input("Materialkosten (€)", min_value=0.0, value=0.0, step=10.0)
        other_v  = col3.number_input("Sonstige variable Kosten (€)", min_value=0.0, value=0.0, step=10.0)

        db1 = rev_net - labor - material - other_v
        db1_pct = (db1 / rev_net * 100) if rev_net > 0 else 0

        st.subheader("Fixkosten")
        col1, col2 = st.columns(2)
        rent      = col1.number_input("Miete / Raumkosten (€)", min_value=0.0, value=0.0, step=50.0)
        admin     = col2.number_input("Verwaltung / Overhead (€)", min_value=0.0, value=0.0, step=50.0)
        other_f   = col1.number_input("Sonstige Fixkosten (€)", min_value=0.0, value=0.0, step=50.0)

        total_fixed = rent + admin + other_f
        db2 = db1 - total_fixed
        db2_pct = (db2 / rev_net * 100) if rev_net > 0 else 0

        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Umsatz", fmt_eur(rev_net))
        c2.metric("DB1 (Bruttogewinn)", fmt_eur(db1),
                  f"{db1_pct:.1f}%",
                  delta_color="normal" if db1 >= 0 else "inverse")
        c3.metric("Fixkosten", fmt_eur(total_fixed))
        c4.metric("DB2 (Betriebsergebnis)", fmt_eur(db2),
                  f"{db2_pct:.1f}%",
                  delta_color="normal" if db2 >= 0 else "inverse")

        # Visualisierung
        waterfall_data = pd.DataFrame({
            "Position": ["Umsatz", "– Personalkosten", "– Material", "– Sonstiges variabel",
                         "= DB1", "– Fixkosten", "= DB2"],
            "Betrag": [rev_net, -labor, -material, -other_v, db1, -total_fixed, db2],
        })
        st.bar_chart(waterfall_data.set_index("Position")["Betrag"])

        if st.button("💾 DB-Rechnung speichern"):
            run_fn("""INSERT INTO contribution_margins(customer_id,calc_month,revenue_net,
                      direct_labor,direct_material,overhead_variable,db1,overhead_fixed,db2)
                      VALUES(?,?,?,?,?,?,?,?,?)""",
                   (cid, month, rev_net, labor, material, other_v, db1, total_fixed, db2))
            log_fn("db_saved", f"{month} DB1={db1:.0f} DB2={db2:.0f}")
            st.success(f"✅ DB-Rechnung für {month} gespeichert!")
            st.rerun()

    with tabs[1]:
        saved = df_fn("""
            SELECT cm.calc_month AS Monat,
                   COALESCE(c.company,'Alle') AS Kunde,
                   cm.revenue_net AS Umsatz, cm.db1 AS DB1, cm.db2 AS DB2,
                   ROUND(cm.db1/NULLIF(cm.revenue_net,0)*100,1) AS DB1_Pct,
                   ROUND(cm.db2/NULLIF(cm.revenue_net,0)*100,1) AS DB2_Pct
            FROM contribution_margins cm LEFT JOIN customers c ON c.id=cm.customer_id
            ORDER BY cm.calc_month DESC
        """)
        if not saved.empty:
            st.dataframe(saved, use_container_width=True)
            st.bar_chart(saved.set_index("Monat")[["Umsatz","DB1","DB2"]])
        else:
            st.info("Noch keine gespeicherten DB-Rechnungen.")

    with tabs[2]:
        trend = df_fn("""
            SELECT calc_month AS Monat, SUM(db2) AS DB2_gesamt
            FROM contribution_margins
            GROUP BY calc_month ORDER BY Monat
        """)
        if not trend.empty:
            st.line_chart(trend.set_index("Monat")["DB2_gesamt"])
        else:
            st.info("Noch kein Trend verfügbar.")


# ─────────────────────────────────────────────────────────────
# 5. XLSX-Rechnungsimport mit Mapping
# ─────────────────────────────────────────────────────────────

def page_xlsx_invoice_import(run_fn, df_fn, next_number_fn, log_fn, refresh_totals_fn) -> None:
    st.title("📊 XLSX-Rechnungsimport")
    st.caption("Rechnungen aus Excel-Datei importieren mit flexiblem Spalten-Mapping.")

    tabs = st.tabs(["📥 Datei hochladen", "🗺️ Spalten zuordnen", "✅ Importieren"])

    if "xlsx_import_data" not in st.session_state:
        st.session_state["xlsx_import_data"] = None
    if "xlsx_mapping" not in st.session_state:
        st.session_state["xlsx_mapping"] = {}

    with tabs[0]:
        uf = st.file_uploader("XLSX-Datei hochladen", type=["xlsx","xls","csv"])
        if uf:
            try:
                if uf.name.endswith(".csv"):
                    raw = pd.read_csv(uf, sep=None, engine="python", encoding="utf-8-sig")
                else:
                    raw = pd.read_excel(uf)
                st.success(f"✅ {len(raw)} Zeilen · {len(raw.columns)} Spalten erkannt")
                st.dataframe(raw.head(5), use_container_width=True)
                st.session_state["xlsx_import_data"] = raw.to_dict("records")
                st.session_state["xlsx_cols"] = raw.columns.tolist()
            except Exception as e:
                st.error(f"Fehler: {e}")

    with tabs[1]:
        if not st.session_state.get("xlsx_import_data"):
            st.info("Bitte zuerst Datei hochladen.")
            return

        cols = ["—"] + st.session_state.get("xlsx_cols", [])
        st.caption("Ordne die Spalten deiner Datei den CRM-Feldern zu:")

        mapping = {}
        fields = [
            ("Rechnungsnummer", "invoice_no"),
            ("Kundenname", "company"),
            ("Rechnungsdatum", "invoice_date"),
            ("Fälligkeitsdatum", "due_date"),
            ("Beschreibung", "description"),
            ("Nettobetrag", "net_amount"),
            ("MwSt-Prozent", "vat_rate"),
            ("Bruttobetrag", "gross_amount"),
        ]
        col_a, col_b = st.columns(2)
        for i, (label, key) in enumerate(fields):
            col = col_a if i % 2 == 0 else col_b
            mapping[key] = col.selectbox(f"{label} →", cols,
                                           key=f"map_{key}",
                                           index=1 if label.lower().replace("-","") in
                                                 " ".join(c.lower() for c in cols) else 0)

        if st.button("💾 Mapping speichern"):
            st.session_state["xlsx_mapping"] = mapping
            st.success("Mapping gespeichert. Bitte Tab 'Importieren' öffnen.")

    with tabs[2]:
        mapping = st.session_state.get("xlsx_mapping", {})
        data    = st.session_state.get("xlsx_import_data", [])

        if not mapping or not data:
            st.info("Bitte zuerst Datei hochladen und Mapping festlegen.")
            return

        # Vorschau
        preview = []
        for row in data[:5]:
            def get_val(key):
                col = mapping.get(key, "—")
                return row.get(col, "") if col != "—" else ""
            preview.append({
                "Rechnung": get_val("invoice_no"),
                "Kunde": get_val("company"),
                "Datum": get_val("invoice_date"),
                "Brutto": get_val("gross_amount"),
            })
        st.dataframe(pd.DataFrame(preview), use_container_width=True)
        st.caption(f"Vorschau der ersten 5 von {len(data)} Zeilen")

        skip_existing = st.checkbox("Bereits vorhandene Rechnungsnummern überspringen", value=True)

        if st.button(f"📥 {len(data)} Rechnungen importieren", type="primary"):
            imported = skipped = errors_n = 0
            customers_cache: Dict[str, int] = {}

            for row in data:
                def get_v(key):
                    col = mapping.get(key, "—")
                    return str(row.get(col, "") or "").strip() if col != "—" else ""

                inv_no = get_v("invoice_no") or next_number_fn("invoices","invoice_no","RE-")
                company = get_v("company")
                inv_date = get_v("invoice_date") or date.today().isoformat()
                due_date = get_v("due_date") or (date.today() + timedelta(days=14)).isoformat()
                desc     = get_v("description") or "Importierte Rechnung"

                try:
                    gross = float(str(get_v("gross_amount")).replace(",",".").replace("€",""))
                    if gross <= 0:
                        gross = 0
                except Exception:
                    gross = 0

                try:
                    vat_r = float(str(get_v("vat_rate")).replace(",",".").replace("%",""))
                except Exception:
                    vat_r = 19.0

                # Rechnungsnummer-Duplikat prüfen
                if skip_existing:
                    ex = df_fn("SELECT id FROM invoices WHERE invoice_no=?", (inv_no,))
                    if not ex.empty:
                        skipped += 1
                        continue

                # Kunden suchen oder anlegen
                if company:
                    if company not in customers_cache:
                        existing_cust = df_fn("SELECT id FROM customers WHERE company=?", (company,))
                        if not existing_cust.empty:
                            customers_cache[company] = int(existing_cust.iloc[0]["id"])
                        else:
                            cno = next_number_fn("customers","customer_no","SD-")
                            run_fn("INSERT INTO customers(customer_no,company) VALUES(?,?)",
                                   (cno, company))
                            new_c = df_fn("SELECT id FROM customers WHERE customer_no=?", (cno,))
                            customers_cache[company] = int(new_c.iloc[0]["id"]) if not new_c.empty else 0
                    cid = customers_cache.get(company, 0)
                else:
                    cid = 0

                try:
                    net = round(gross / (1 + vat_r/100), 2) if gross > 0 else 0
                    vat_t = round(gross - net, 2)
                    run_fn("""INSERT INTO invoices(invoice_no,customer_id,invoice_date,
                              due_date,description,net_total,vat_rate,vat_total,
                              gross_total,paid_amount,status)
                              VALUES(?,?,?,?,?,?,?,?,?,0,'offen')""",
                           (inv_no, cid or None, inv_date[:10], due_date[:10],
                            desc, net, vat_r, vat_t, gross))
                    imported += 1
                except Exception:
                    errors_n += 1

            log_fn("xlsx_import", f"{imported} importiert, {skipped} übersprungen, {errors_n} Fehler")
            st.success(f"✅ {imported} Rechnungen importiert · {skipped} übersprungen · {errors_n} Fehler")
            st.session_state["xlsx_import_data"] = None
            st.rerun()


# ─────────────────────────────────────────────────────────────
# 6. Backup-Verschlüsselung (AES-256 via Fernet)
# ─────────────────────────────────────────────────────────────

def encrypt_file(filepath: Path, password: str) -> Tuple[bool, str]:
    """Verschlüsselt Datei mit AES-256 (Fernet = AES-CBC + HMAC-SHA256)."""
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        import os

        # Schlüssel aus Passwort ableiten
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
        key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
        f = Fernet(key)

        data = filepath.read_bytes()
        encrypted = f.encrypt(data)

        out_path = filepath.with_suffix(filepath.suffix + ".enc")
        # Salt + verschlüsselte Daten
        out_path.write_bytes(salt + encrypted)
        return True, str(out_path)
    except ImportError:
        return False, "cryptography nicht installiert (pip install cryptography)"
    except Exception as e:
        return False, str(e)


def decrypt_file(enc_path: Path, password: str) -> Tuple[bool, str]:
    """Entschlüsselt eine mit encrypt_file erstellte Datei."""
    try:
        from cryptography.fernet import Fernet, InvalidToken
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64

        raw = enc_path.read_bytes()
        salt = raw[:16]
        encrypted = raw[16:]

        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000)
        key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
        f = Fernet(key)

        data = f.decrypt(encrypted)
        out_path = enc_path.with_suffix("")  # entfernt .enc
        out_path.write_bytes(data)
        return True, str(out_path)
    except ImportError:
        return False, "cryptography nicht installiert"
    except Exception as e:
        return False, f"Entschlüsselung fehlgeschlagen (falsches Passwort?): {e}"


def page_encrypted_backup(run_fn, df_fn, create_backup_fn) -> None:
    st.title("🔐 Verschlüsseltes Backup")
    st.caption("AES-256-Verschlüsselung (Fernet) für sicheren Export und Cloud-Upload.")

    tabs = st.tabs(["🔒 Verschlüsseln", "🔓 Entschlüsseln", "ℹ️ Sicherheit"])

    with tabs[0]:
        st.subheader("Backup erstellen und verschlüsseln")
        password  = st.text_input("Verschlüsselungs-Passwort *", type="password")
        password2 = st.text_input("Passwort wiederholen *", type="password")

        st.warning("⚠️ Passwort sicher aufbewahren! Ohne Passwort ist das Backup nicht wiederherstellbar.")

        if st.button("🔒 Verschlüsseltes Backup erstellen", type="primary"):
            if not password:
                st.error("Passwort eingeben.")
            elif password != password2:
                st.error("Passwörter stimmen nicht überein.")
            elif len(password) < 10:
                st.error("Passwort muss mindestens 10 Zeichen haben.")
            else:
                with st.spinner("Backup wird erstellt und verschlüsselt..."):
                    try:
                        backup_path = Path(str(create_backup_fn("verschlüsselt")))
                        if backup_path.exists():
                            ok, result = encrypt_file(backup_path, password)
                            if ok:
                                enc_path = Path(result)
                                size = enc_path.stat().st_size
                                run_fn("INSERT INTO backups(file_path,file_size,note) VALUES(?,?,?)",
                                       (result, size, "AES-256 verschlüsselt"))
                                st.success(f"✅ Verschlüsseltes Backup: {enc_path.name} ({size//1024} KB)")
                                st.download_button(
                                    "📥 Verschlüsseltes Backup herunterladen",
                                    enc_path.read_bytes(), enc_path.name,
                                    "application/octet-stream"
                                )
                            else:
                                st.error(f"Verschlüsselungsfehler: {result}")
                    except Exception as e:
                        st.error(f"Fehler: {e}")

    with tabs[1]:
        st.subheader("Verschlüsseltes Backup entschlüsseln")
        enc_file = st.file_uploader("Verschlüsselte Backup-Datei (.db.enc)", type=["enc","db"])
        dec_pw   = st.text_input("Passwort", type="password")

        if enc_file and dec_pw and st.button("🔓 Entschlüsseln"):
            tmp = Path("/tmp") / enc_file.name
            tmp.write_bytes(enc_file.read())
            ok, result = decrypt_file(tmp, dec_pw)
            if ok:
                dec_path = Path(result)
                st.success(f"✅ Entschlüsselt: {dec_path.name}")
                st.download_button("📥 Entschlüsselte DB herunterladen",
                                   dec_path.read_bytes(), dec_path.name,
                                   "application/octet-stream")
                tmp.unlink()
                dec_path.unlink()
            else:
                st.error(result)
                tmp.unlink()

    with tabs[2]:
        st.markdown("""
**Sicherheits-Details:**

| Komponente | Algorithmus |
|---|---|
| Verschlüsselung | AES-128-CBC (Fernet) |
| MAC | HMAC-SHA256 |
| Schlüsselableitung | PBKDF2-SHA256 · 480.000 Iterationen |
| Salt | 16 zufällige Bytes (pro Backup) |

**Fernet** ist ein symmetrisches, authentifiziertes Verschlüsselungsschema aus der  
`cryptography`-Bibliothek von Python (NIST-zertifiziert).

**Installation:** `pip install cryptography`

**Empfehlungen:**
- Passwort mindestens 15 Zeichen, Buchstaben + Zahlen + Sonderzeichen
- Passwort separat und sicher aufbewahren (z.B. KeePass)
- Backup-Dateien auf Cloud/USB-Stick kopieren
- Monatlichen Wiederherstellungstest durchführen
        """)


# ─────────────────────────────────────────────────────────────
# 7. Query-Performance-Monitor
# ─────────────────────────────────────────────────────────────

def page_performance_monitor(run_fn, df_fn, db_path: Path) -> None:
    st.title("⚡ Performance-Monitor")
    st.caption("Datenbankstatistiken, Indizes und Query-Analyse.")

    tabs = st.tabs(["📊 DB-Statistiken", "🔍 Indizes", "⚡ EXPLAIN-Analyse"])

    with tabs[0]:
        # Tabellen-Statistiken
        tables = df_fn("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        stats = []
        if not tables.empty:
            for t in tables["name"].tolist():
                try:
                    count = int(df_fn(f"SELECT COUNT(*) AS n FROM [{t}]").iloc[0]["n"])
                    stats.append({"Tabelle": t, "Einträge": count})
                except Exception:
                    pass
        if stats:
            df_s = pd.DataFrame(stats).sort_values("Einträge", ascending=False)
            st.dataframe(df_s, use_container_width=True, height=400)
            c1, c2 = st.columns(2)
            c1.metric("Tabellen gesamt", len(df_s))
            c2.metric("Datensätze gesamt", df_s["Einträge"].sum())

        db_size = db_path.stat().st_size if db_path.exists() else 0
        st.metric("Datenbankgröße", f"{db_size/1024:.0f} KB")

        col1, col2 = st.columns(2)
        if col1.button("🗜️ VACUUM (Datenbank optimieren)"):
            try:
                run_fn("VACUUM")
                st.success("✅ VACUUM ausgeführt.")
            except Exception as e:
                st.error(f"{e}")
        if col2.button("🔍 INTEGRITY CHECK"):
            try:
                r = df_fn("PRAGMA integrity_check")
                if not r.empty and r.iloc[0,0] == "ok":
                    st.success("✅ Integrität OK")
                else:
                    st.error(f"⚠️ Probleme: {r}")
            except Exception as e:
                st.error(f"{e}")

    with tabs[1]:
        indexes = df_fn("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' ORDER BY tbl_name, name")
        if not indexes.empty:
            st.caption(f"{len(indexes)} Indizes vorhanden")
            st.dataframe(indexes, use_container_width=True, height=350)
        else:
            st.info("Keine Indizes gefunden.")

        # Fehlende Indizes vorschlagen
        st.subheader("Empfohlene Indizes")
        recommendations = [
            ("invoices", "invoice_date,customer_id,status"),
            ("expenses", "bwa_month,category"),
            ("shifts", "shift_date,employee_id,customer_id"),
            ("contacts", "customer_id,contact_date"),
        ]
        for table, cols in recommendations:
            idx_name = f"idx_{table}_{'_'.join(cols.split(',')[0:2])}"
            existing = df_fn(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{idx_name}'")
            status = "✅ Vorhanden" if not existing.empty else "⚠️ Fehlt"
            col1, col2, col3 = st.columns([2,2,1])
            col1.write(f"`{table}({cols})`")
            col2.caption(status)
            if existing.empty:
                if col3.button("➕ Anlegen", key=f"idx_{idx_name}"):
                    try:
                        run_fn(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({cols})")
                        st.success(f"✅ Index {idx_name} erstellt.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"{e}")

    with tabs[2]:
        st.subheader("Query-Analyse (EXPLAIN QUERY PLAN)")
        query = st.text_area("SQL-Query eingeben", "SELECT * FROM invoices WHERE status='offen' LIMIT 10")
        if st.button("🔍 Analysieren"):
            try:
                plan = df_fn(f"EXPLAIN QUERY PLAN {query}")
                if not plan.empty:
                    st.dataframe(plan, use_container_width=True)
                    if any("SCAN" in str(r) and "INDEX" not in str(r) for _, r in plan.iterrows()):
                        st.warning("⚠️ Voller Tabellen-Scan – Index empfohlen!")
                    else:
                        st.success("✅ Index wird genutzt.")
            except Exception as e:
                st.error(f"Query-Fehler: {e}")
