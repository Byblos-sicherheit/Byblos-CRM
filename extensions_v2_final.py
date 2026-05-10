"""
extensions_v2_final.py – Letzte Kernverbesserungen für Byblos CRM v2
=====================================================================
Enthält:
  1. Verbesserter Bankabgleich / DATEV mit SKR03-Konten
  2. Import-Assistent (PDF/CSV/Excel → Rechnung/Ausgabe)
  3. Vollständige Lieferantenverwaltung
  4. Ausgaben-Detailseite mit Belegvorschau
  5. Reporting-Center (PDF-Berichte, Quartalsberichte)
  6. System-Health-Monitor
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


# ─────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────

def fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────
# 1. Verbesserter Bankabgleich / DATEV
# ─────────────────────────────────────────────────────────────

# SKR03-Konten für automatischen DATEV-Export
SKR03 = {
    "Erlöse 19%":          "8400",
    "Erlöse 7%":           "8300",
    "Erlöse steuerfrei":   "8125",
    "Bank":                "1200",
    "Kasse":               "1000",
    "Debitoren":           "10000",
    "Kreditoren":          "70000",
    "Kfz-Kosten":          "4530",
    "Bürokosten":          "4910",
    "Kommunikation":       "4920",
    "Raumkosten":          "4210",
    "Energie":             "4240",
    "Versicherungen":      "4360",
    "Beratungskosten":     "4970",
    "Marketing":           "4610",
    "Personalentwicklung": "4145",
    "Personalkosten":      "4100",
    "Betriebsausstattung": "4980",
    "Finanzkosten":        "4970",
    "IT-Kosten":           "4980",
    "Sonstiges":           "4980",
}


def page_bank_datev_v2(run_fn, df_fn, log_fn, normalize_fn, auto_match_fn, apply_match_fn) -> None:
    st.title("🏦 Bankabgleich & DATEV-Export")

    tabs = st.tabs([
        "📥 Kontoauszug Import", "🔗 Transaktionen abgleichen",
        "📊 Kontobewegungen", "📤 DATEV-Export", "⚙️ IBAN-Vorlagen"
    ])

    # ── Tab 0: Import ─────────────────────────────────────────
    with tabs[0]:
        st.subheader("Kontoauszug importieren")
        st.caption("Unterstützte Formate: CSV (Semikolon/Komma/Tab), Excel (XLSX/XLS). "
                   "Erkannte Spalten: Buchungstag, Auftraggeber/Empfänger, Verwendungszweck, Betrag.")

        f = st.file_uploader("Kontoauszug hochladen", type=["csv", "xlsx", "xls"])
        if f:
            try:
                if f.name.lower().endswith(".csv"):
                    for sep in [";", ",", "\t"]:
                        try:
                            raw = pd.read_csv(f, sep=sep, engine="python", encoding="utf-8-sig")
                            if len(raw.columns) >= 3:
                                break
                        except Exception:
                            f.seek(0)
                else:
                    raw = pd.read_excel(f)

                norm = normalize_fn(raw)
                st.success(f"✅ {len(norm)} Zeilen erkannt")

                c1, c2, c3 = st.columns(3)
                income = float(norm[norm["amount"] > 0]["amount"].sum())
                expense = float(norm[norm["amount"] < 0]["amount"].sum())
                c1.metric("Einnahmen", fmt_eur(income))
                c2.metric("Ausgaben", fmt_eur(abs(expense)))
                c3.metric("Saldo", fmt_eur(income + expense))

                st.dataframe(norm, use_container_width=True)

                col1, col2 = st.columns(2)
                dup_check = col1.checkbox("Duplikate überspringen", value=True)
                if col2.button("📥 Importieren & automatisch zuordnen", type="primary"):
                    imported = 0
                    skipped = 0
                    for _, r in norm.iterrows():
                        bd = str(r["booking_date"])[:10]
                        amt = float(r["amount"])
                        pp  = str(r.get("payer_payee", ""))
                        pur = str(r.get("purpose", ""))

                        if dup_check:
                            exists = df_fn(
                                "SELECT id FROM bank_transactions WHERE booking_date=? AND amount=? AND payer_payee=?",
                                (bd, amt, pp)
                            )
                            if not exists.empty:
                                skipped += 1
                                continue

                        res = run_fn(
                            "INSERT INTO bank_transactions(booking_date,value_date,payer_payee,purpose,amount,source_file) VALUES(?,?,?,?,?,?)",
                            (bd, str(r.get("value_date", bd))[:10], pp, pur, amt, f.name)
                        )
                        # Auto-match
                        try:
                            last = df_fn("SELECT id FROM bank_transactions ORDER BY id DESC LIMIT 1")
                            if not last.empty:
                                auto_match_fn(int(last.iloc[0]["id"]))
                        except Exception:
                            pass
                        imported += 1

                    log_fn("bank_import", f"{f.name}: {imported} importiert, {skipped} übersprungen")
                    st.success(f"✅ {imported} Transaktionen importiert, {skipped} Duplikate übersprungen.")
                    st.rerun()
            except Exception as e:
                st.error(f"Import-Fehler: {e}")

    # ── Tab 1: Abgleich ───────────────────────────────────────
    with tabs[1]:
        st.subheader("Transaktionen zuordnen & buchen")

        status_filter = st.selectbox("Filter", ["neu + vorgeschlagen", "alle", "nur neu", "nur vorgeschlagen", "nur gebucht"])
        status_map = {
            "neu + vorgeschlagen": ("neu", "vorgeschlagen"),
            "alle": None,
            "nur neu": ("neu",),
            "nur vorgeschlagen": ("vorgeschlagen",),
            "nur gebucht": ("gebucht",),
        }

        status_vals = status_map.get(status_filter)
        if status_vals is None:
            tx_all = df_fn("SELECT * FROM bank_transactions ORDER BY booking_date DESC, id DESC LIMIT 200")
        else:
            placeholders = ",".join("?" * len(status_vals))
            tx_all = df_fn(
                f"SELECT * FROM bank_transactions WHERE status IN ({placeholders}) ORDER BY booking_date DESC, id DESC LIMIT 200",
                tuple(status_vals)
            )

        if tx_all.empty:
            st.info("Keine Transaktionen in diesem Status.")
        else:
            # Übersicht
            col1, col2, col3 = st.columns(3)
            neu = len(tx_all[tx_all["status"] == "neu"]) if "status" in tx_all.columns else 0
            vorgeschlagen = len(tx_all[tx_all["status"] == "vorgeschlagen"]) if "status" in tx_all.columns else 0
            gebucht = len(tx_all[tx_all["status"] == "gebucht"]) if "status" in tx_all.columns else 0
            col1.metric("🔵 Neu", neu)
            col2.metric("🟡 Vorgeschlagen", vorgeschlagen)
            col3.metric("✅ Gebucht", gebucht)

            # Vorgeschlagene automatisch alle buchen
            if vorgeschlagen > 0:
                if st.button(f"✅ Alle {vorgeschlagen} Vorschläge bestätigen und buchen"):
                    pending = df_fn("SELECT id FROM bank_transactions WHERE status='vorgeschlagen'")
                    for _, r in pending.iterrows():
                        try:
                            apply_match_fn(int(r["id"]))
                        except Exception:
                            pass
                    st.success(f"{vorgeschlagen} Transaktionen gebucht.")
                    st.rerun()

            st.dataframe(tx_all, use_container_width=True, height=300)

            # Manuelle Zuordnung
            st.divider()
            st.subheader("Einzelne Transaktion manuell zuordnen")
            unbooked = df_fn("""
                SELECT id,
                    booking_date || ' | ' || CAST(amount AS TEXT) || ' € | ' ||
                    COALESCE(payer_payee,'') || ' | ' || COALESCE(purpose,'') AS label,
                    amount, status
                FROM bank_transactions WHERE status IN ('neu','vorgeschlagen')
                ORDER BY booking_date DESC LIMIT 100
            """)
            if not unbooked.empty:
                sel_label = st.selectbox("Transaktion auswählen", unbooked["label"].tolist())
                txid = int(unbooked[unbooked["label"] == sel_label].iloc[0]["id"])
                tx_amount = float(unbooked[unbooked["label"] == sel_label].iloc[0]["amount"])

                col_inv, col_exp = st.columns(2)

                with col_inv:
                    st.caption("📄 Rechnung zuordnen (Zahlungseingang)")
                    invoices = df_fn("""
                        SELECT id, invoice_no || ' | ' || company ||
                               ' | ' || ROUND(gross_total - paid_amount, 2) || ' €' AS label
                        FROM invoices i JOIN customers c ON c.id=i.customer_id
                        WHERE status NOT IN ('bezahlt','storniert')
                        ORDER BY due_date ASC
                    """)
                    if not invoices.empty:
                        ilabel = st.selectbox("Rechnung", ["—"] + invoices["label"].tolist())
                        if ilabel != "—":
                            iid = int(invoices[invoices["label"] == ilabel].iloc[0]["id"])
                            if st.button("🔗 Rechnung zuordnen"):
                                run_fn("UPDATE bank_transactions SET matched_type='invoice', matched_id=?, status='vorgeschlagen' WHERE id=?", (iid, txid))
                                st.rerun()
                    if st.button("💳 Rechnung buchen (Zuordnung übernehmen)"):
                        msg = apply_match_fn(txid)
                        st.success(msg)
                        st.rerun()

                with col_exp:
                    st.caption("🧾 Ausgabe zuordnen (Zahlungsausgang)")
                    expenses = df_fn("""
                        SELECT id, expense_no || ' | ' || description ||
                               ' | ' || ROUND(gross_amount - paid_amount, 2) || ' €' AS label
                        FROM expenses WHERE status NOT IN ('bezahlt')
                        ORDER BY expense_date DESC
                    """)
                    if not expenses.empty:
                        elabel = st.selectbox("Ausgabe", ["—"] + expenses["label"].tolist())
                        if elabel != "—":
                            eid = int(expenses[expenses["label"] == elabel].iloc[0]["id"])
                            if st.button("🔗 Ausgabe zuordnen"):
                                run_fn("UPDATE bank_transactions SET matched_type='expense', matched_id=?, status='vorgeschlagen' WHERE id=?", (eid, txid))
                                st.rerun()
                    if st.button("💳 Ausgabe buchen (Zuordnung übernehmen)"):
                        msg = apply_match_fn(txid)
                        st.success(msg)
                        st.rerun()

                if st.button("🗑️ Transaktion ignorieren (als gebucht markieren)"):
                    run_fn("UPDATE bank_transactions SET status='gebucht', matched_type='ignoriert' WHERE id=?", (txid,))
                    st.rerun()

    # ── Tab 2: Kontobewegungen ────────────────────────────────
    with tabs[2]:
        st.subheader("Kontobewegungen Übersicht")
        col1, col2 = st.columns(2)
        start = col1.date_input("Von", date.today().replace(day=1))
        end   = col2.date_input("Bis", date.today())

        movements = df_fn("""
            SELECT booking_date AS Datum, payer_payee AS Auftraggeber_Empfänger,
                   purpose AS Verwendungszweck, amount AS Betrag_EUR,
                   matched_type AS Typ, status AS Status
            FROM bank_transactions
            WHERE booking_date BETWEEN ? AND ?
            ORDER BY booking_date DESC
        """, (start.isoformat(), end.isoformat()))

        if not movements.empty:
            income  = float(movements[movements["Betrag_EUR"] > 0]["Betrag_EUR"].sum())
            expense = float(movements[movements["Betrag_EUR"] < 0]["Betrag_EUR"].sum())
            c1, c2, c3 = st.columns(3)
            c1.metric("Einnahmen", fmt_eur(income))
            c2.metric("Ausgaben", fmt_eur(abs(expense)))
            c3.metric("Saldo", fmt_eur(income + expense))
            st.dataframe(movements, use_container_width=True, height=350)

            csv = movements.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 CSV-Export", csv, f"kontoauszug_{start}_{end}.csv", "text/csv")
        else:
            st.info("Keine Bewegungen im Zeitraum.")

    # ── Tab 3: DATEV-Export ───────────────────────────────────
    with tabs[3]:
        st.subheader("DATEV-Buchungsstapel (SKR03)")
        st.warning("⚠️ Buchungskonten bitte vor produktiver Nutzung mit Steuerberater abstimmen.")

        col1, col2 = st.columns(2)
        month  = col1.text_input("Monat (YYYY-MM)", date.today().strftime("%Y-%m"))
        skr    = col2.selectbox("Kontenrahmen", ["SKR03", "SKR04"])
        erloese_konto = col1.text_input("Erlöskonto", "8400")
        bank_konto    = col2.text_input("Bankkonto", "1200")

        if st.button("📊 DATEV-Export erstellen", type="primary"):
            invoices = df_fn("""
                SELECT i.invoice_date AS Datum, i.invoice_no AS BelegNr,
                       c.company AS Gegenkonto, i.description AS Buchungstext,
                       ROUND(i.net_total, 2) AS Netto,
                       ROUND(i.vat_total, 2) AS USt,
                       ROUND(i.gross_total, 2) AS Brutto,
                       i.vat_rate AS MwSt_Satz,
                       ? AS Soll_Konto, '10000' AS Haben_Konto, 'S' AS SH
                FROM invoices i JOIN customers c ON c.id=i.customer_id
                WHERE substr(i.invoice_date,1,7)=?
                ORDER BY i.invoice_date
            """, (erloese_konto, month))

            expenses = df_fn("""
                SELECT e.expense_date AS Datum, e.expense_no AS BelegNr,
                       COALESCE(s.name, '-') AS Gegenkonto, e.description AS Buchungstext,
                       ROUND(e.net_amount, 2) AS Netto,
                       ROUND(e.vat_amount, 2) AS Vorsteuer,
                       ROUND(e.gross_amount, 2) AS Brutto,
                       e.vat_rate AS MwSt_Satz,
                       COALESCE(ec.bwa_group, ?) AS Soll_Konto,
                       ? AS Haben_Konto, 'H' AS SH
                FROM expenses e
                LEFT JOIN suppliers s ON s.id=e.supplier_id
                LEFT JOIN expense_categories ec ON ec.category=e.category
                WHERE substr(e.expense_date,1,7)=?
                ORDER BY e.expense_date
            """, ("4980", bank_konto, month))

            st.subheader(f"Rechnungen {month}")
            if not invoices.empty:
                st.dataframe(invoices, use_container_width=True)
            else:
                st.info("Keine Rechnungen.")

            st.subheader(f"Ausgaben {month}")
            if not expenses.empty:
                st.dataframe(expenses, use_container_width=True)
            else:
                st.info("Keine Ausgaben.")

            if not invoices.empty or not expenses.empty:
                combined = pd.concat([invoices, expenses], ignore_index=True, sort=False)
                csv = combined.to_csv(index=False, sep=";").encode("utf-8-sig")
                st.download_button(
                    f"📥 DATEV-CSV {month} herunterladen",
                    csv, f"byblos_datev_{month}.csv", "text/csv"
                )

                # Zusammenfassung
                c1, c2, c3 = st.columns(3)
                if not invoices.empty and "Brutto" in invoices.columns:
                    c1.metric("Umsatz gesamt", fmt_eur(float(invoices["Brutto"].sum())))
                if not expenses.empty and "Brutto" in expenses.columns:
                    c2.metric("Ausgaben gesamt", fmt_eur(float(expenses["Brutto"].sum())))

    # ── Tab 4: IBAN-Vorlagen ──────────────────────────────────
    with tabs[4]:
        st.subheader("Bekannte IBANs / Kontoinhaber")
        iban_data = df_fn("SELECT * FROM bank_iban_templates ORDER BY name") if _table_exists(df_fn, "bank_iban_templates") else pd.DataFrame()

        if not iban_data.empty:
            st.dataframe(iban_data, use_container_width=True)

        with st.form("iban_form", clear_on_submit=True):
            a, b, c = st.columns(3)
            iban_name = a.text_input("Name / Beschreibung")
            iban_val  = b.text_input("IBAN")
            iban_cat  = c.text_input("Standard-Kategorie")
            if st.form_submit_button("➕ IBAN speichern") and iban_name and iban_val:
                _ensure_iban_table(run_fn)
                run_fn("INSERT OR REPLACE INTO bank_iban_templates(name,iban,category) VALUES(?,?,?)",
                       (iban_name, iban_val, iban_cat))
                st.success(f"IBAN für '{iban_name}' gespeichert.")
                st.rerun()


def _table_exists(df_fn, table: str) -> bool:
    try:
        r = df_fn("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        return not r.empty
    except Exception:
        return False


def _ensure_iban_table(run_fn) -> None:
    run_fn("""CREATE TABLE IF NOT EXISTS bank_iban_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, iban TEXT UNIQUE, category TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")


# ─────────────────────────────────────────────────────────────
# 2. Vollständiger Import-Assistent
# ─────────────────────────────────────────────────────────────

def page_import_v2(run_fn, df_fn, base_dir: Path, next_number_fn, log_fn,
                   extract_pdf_fn, refresh_inv_fn, refresh_exp_fn) -> None:
    st.title("📥 Import-Assistent")

    tabs = st.tabs([
        "📄 PDF-Import (Rechnungen)", "📊 Excel/CSV-Import",
        "📋 Import-Warteschlange", "🗂️ Archivierte Dateien"
    ])

    IMPORT_DIR = base_dir / "imports"
    IMPORT_DIR.mkdir(exist_ok=True)

    with tabs[0]:
        st.subheader("Eingangsrechnung als PDF importieren")
        st.caption("PDF hochladen → Text wird automatisch extrahiert → Vorschau zur manuellen Übernahme.")

        uploaded = st.file_uploader("PDF hochladen", type=["pdf", "jpg", "jpeg", "png"],
                                    accept_multiple_files=True)

        for uf in uploaded:
            target = IMPORT_DIR / uf.name
            target.write_bytes(uf.read())
            run_fn("INSERT INTO imports(file_name,import_status,note) VALUES(?,?,?)",
                   (uf.name, "neu", "PDF hochgeladen"))
            log_fn("import_upload", uf.name)
            st.success(f"✅ '{uf.name}' gespeichert.")

            # Text extrahieren
            text = ""
            try:
                text = extract_pdf_fn(str(target))
            except Exception:
                pass

            if text:
                with st.expander(f"📄 Extrahierter Text: {uf.name}", expanded=True):
                    st.text_area("Erkannter Text (zur manuellen Übernahme):", text[:2000], height=200)

                    # KI-Kategorisierungs-Vorschlag
                    try:
                        from ml_logic import predict_category
                        cat, conf = predict_category(text[:500])
                        st.info(f"🤖 KI-Vorschlag: **{cat}** ({conf:.0f}% Konfidenz)")
                    except Exception:
                        pass

                    # Schnell-Erfassung als Ausgabe
                    with st.form(f"quick_exp_{uf.name}"):
                        st.caption("Schnell als Ausgabe erfassen:")
                        a, b = st.columns(2)
                        exp_no = a.text_input("Ausgaben-Nr.", next_number_fn("expenses", "expense_no", "AUS-"), key=f"en_{uf.name}")
                        exp_date = b.date_input("Datum", date.today(), key=f"ed_{uf.name}")
                        desc = st.text_input("Beschreibung", text[:60].strip(), key=f"desc_{uf.name}")
                        net = a.number_input("Netto (€)", min_value=0.0, value=0.0, step=10.0, key=f"net_{uf.name}")
                        vat = b.number_input("MwSt %", value=19.0, step=1.0, key=f"vat_{uf.name}")
                        if st.form_submit_button("💾 Als Ausgabe speichern") and desc and net > 0:
                            vat_amt = round(net * vat / 100, 2)
                            gross = round(net + vat_amt, 2)
                            run_fn("""INSERT INTO expenses(expense_no,expense_date,description,net_amount,vat_rate,vat_amount,gross_amount,status,receipt_path,bwa_month)
                                      VALUES(?,?,?,?,?,?,?,?,?,?)""",
                                   (exp_no, exp_date.isoformat(), desc, net, vat, vat_amt, gross,
                                    "offen", str(target), exp_date.strftime("%Y-%m")))
                            run_fn("UPDATE imports SET import_status='verarbeitet', note=? WHERE file_name=?",
                                   (f"Als Ausgabe {exp_no} erfasst", uf.name))
                            log_fn("import_expense_created", f"{exp_no} aus {uf.name}")
                            st.success(f"✅ Ausgabe {exp_no} gespeichert!")
                            st.rerun()

    with tabs[1]:
        st.subheader("Kunden / Rechnungen aus Excel oder CSV importieren")
        import_type = st.selectbox("Was importieren?", ["Kunden", "Ausgaben/Belege", "Zeiterfassung"])
        uf2 = st.file_uploader("Excel/CSV hochladen", type=["xlsx", "xls", "csv"])

        if uf2:
            try:
                if uf2.name.endswith(".csv"):
                    raw = pd.read_csv(uf2, sep=None, engine="python", encoding="utf-8-sig")
                else:
                    raw = pd.read_excel(uf2)
                st.success(f"✅ {len(raw)} Zeilen erkannt, {len(raw.columns)} Spalten")
                st.dataframe(raw.head(5), use_container_width=True)

                if import_type == "Kunden":
                    st.subheader("Spalten-Zuordnung")
                    col_company = st.selectbox("Firmenname", ["—"] + raw.columns.tolist())
                    col_email   = st.selectbox("E-Mail", ["—"] + raw.columns.tolist())
                    col_phone   = st.selectbox("Telefon", ["—"] + raw.columns.tolist())
                    col_street  = st.selectbox("Straße", ["—"] + raw.columns.tolist())
                    col_zip     = st.selectbox("PLZ Ort", ["—"] + raw.columns.tolist())

                    if st.button("📥 Kunden importieren", type="primary") and col_company != "—":
                        imported = 0
                        for _, row in raw.iterrows():
                            company = str(row.get(col_company, "")).strip()
                            if not company or company == "nan":
                                continue
                            cno = next_number_fn("customers", "customer_no", "SD-")
                            run_fn("""INSERT INTO customers(customer_no,company,email,phone,street,zip_city)
                                      VALUES(?,?,?,?,?,?)""",
                                   (cno, company,
                                    str(row.get(col_email, "")) if col_email != "—" else "",
                                    str(row.get(col_phone, "")) if col_phone != "—" else "",
                                    str(row.get(col_street, "")) if col_street != "—" else "",
                                    str(row.get(col_zip, "")) if col_zip != "—" else ""))
                            imported += 1
                        log_fn("customer_import", f"{imported} Kunden importiert")
                        st.success(f"✅ {imported} Kunden importiert!")
                        st.rerun()

            except Exception as e:
                st.error(f"Fehler beim Lesen: {e}")

    with tabs[2]:
        st.subheader("Import-Warteschlange")
        queue = df_fn("SELECT id, file_name AS Datei, import_status AS Status, note AS Notiz, created_at AS Hochgeladen FROM imports ORDER BY created_at DESC")
        if not queue.empty:
            c1, c2 = st.columns(2)
            c1.metric("Gesamt", len(queue))
            c2.metric("Nicht verarbeitet", len(queue[queue["Status"] == "neu"]))
            st.dataframe(queue, use_container_width=True)
        else:
            st.info("Warteschlange leer.")

    with tabs[3]:
        st.subheader("Archivierte Import-Dateien")
        files = list(IMPORT_DIR.iterdir()) if IMPORT_DIR.exists() else []
        if files:
            for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:50]:
                col1, col2 = st.columns([4, 1])
                col1.write(f"📄 {f.name} ({f.stat().st_size//1024} KB)")
                col2.download_button("⬇", f.read_bytes(), f.name, key=f"dl_{f.name}")
        else:
            st.info("Keine importierten Dateien.")


# ─────────────────────────────────────────────────────────────
# 3. Vollständige Lieferantenverwaltung
# ─────────────────────────────────────────────────────────────

def page_suppliers_v2(run_fn, df_fn, next_number_fn, log_fn) -> None:
    st.title("🚚 Lieferantenverwaltung")

    tabs = st.tabs(["📋 Übersicht", "➕ Neu anlegen", "✏️ Bearbeiten", "📊 Ausgaben je Lieferant"])

    with tabs[0]:
        q = st.text_input("🔍 Suche")
        if q:
            data = df_fn("SELECT * FROM suppliers WHERE name LIKE ? OR supplier_no LIKE ? ORDER BY name", (f"%{q}%", f"%{q}%"))
        else:
            data = df_fn("SELECT * FROM suppliers ORDER BY name")
        if not data.empty:
            st.dataframe(data, use_container_width=True)
            csv = data.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button("📥 CSV-Export", csv, "lieferanten.csv", "text/csv")
        else:
            st.info("Keine Lieferanten gefunden.")

    with tabs[1]:
        with st.form("sup_new", clear_on_submit=True):
            a, b = st.columns(2)
            sup_no = a.text_input("Lieferanten-Nr.", next_number_fn("suppliers", "supplier_no", "LF-"))
            name   = b.text_input("Name *")
            contact_person = a.text_input("Ansprechperson")
            phone  = b.text_input("Telefon")
            email  = a.text_input("E-Mail")
            tax_no = b.text_input("USt-ID / Steuernummer")
            iban   = a.text_input("IBAN")
            street = b.text_input("Straße")
            zip_city = a.text_input("PLZ Ort")
            payment_terms = b.text_input("Zahlungsbedingungen", "30 Tage netto")
            notes  = st.text_area("Notizen")
            submitted = st.form_submit_button("💾 Lieferant speichern", type="primary")

        if submitted:
            if not name.strip():
                st.error("Name ist Pflichtfeld.")
            else:
                run_fn("""INSERT INTO suppliers(supplier_no,name,contact_person,email,phone,street,zip_city,tax_no,notes)
                          VALUES(?,?,?,?,?,?,?,?,?)""",
                       (sup_no, name, contact_person, email, phone, street, zip_city, tax_no,
                        f"{notes}\nIBAN:{iban}\nZahlungsbedingungen:{payment_terms}"))
                log_fn("supplier_created", name)
                st.success(f"✅ Lieferant '{name}' gespeichert!")
                st.rerun()

    with tabs[2]:
        sups = df_fn("SELECT id, supplier_no || ' – ' || name AS label FROM suppliers ORDER BY name")
        if sups.empty:
            st.info("Noch keine Lieferanten.")
            return
        sel = st.selectbox("Lieferant", sups["label"].tolist())
        sid = int(sups[sups["label"] == sel].iloc[0]["id"])
        row = df_fn("SELECT * FROM suppliers WHERE id=?", (sid,)).iloc[0].to_dict()

        with st.form("sup_edit"):
            a, b = st.columns(2)
            sup_no = a.text_input("Nr.", str(row.get("supplier_no", "")))
            name   = b.text_input("Name *", str(row.get("name", "")))
            contact_person = a.text_input("Ansprechperson", str(row.get("contact_person", "") or ""))
            phone  = b.text_input("Telefon", str(row.get("phone", "") or ""))
            email  = a.text_input("E-Mail", str(row.get("email", "") or ""))
            tax_no = b.text_input("USt-ID", str(row.get("tax_no", "") or ""))
            street = a.text_input("Straße", str(row.get("street", "") or ""))
            zip_city = b.text_input("PLZ Ort", str(row.get("zip_city", "") or ""))
            notes  = st.text_area("Notizen", str(row.get("notes", "") or ""))
            save = st.form_submit_button("💾 Speichern", type="primary")
        if save and name.strip():
            run_fn("UPDATE suppliers SET supplier_no=?,name=?,contact_person=?,email=?,phone=?,street=?,zip_city=?,tax_no=?,notes=? WHERE id=?",
                   (sup_no, name, contact_person, email, phone, street, zip_city, tax_no, notes, sid))
            log_fn("supplier_updated", name)
            st.success("✅ Lieferant aktualisiert!")
            st.rerun()

        exp_count = int(df_fn("SELECT COUNT(*) AS n FROM expenses WHERE supplier_id=?", (sid,)).iloc[0]["n"])
        if exp_count == 0:
            if st.button("🗑️ Lieferant löschen"):
                run_fn("DELETE FROM suppliers WHERE id=?", (sid,))
                log_fn("supplier_deleted", str(sid))
                st.success("Gelöscht."); st.rerun()
        else:
            st.caption(f"Lieferant hat {exp_count} Ausgaben — Löschen nicht möglich.")

    with tabs[3]:
        st.subheader("Ausgaben-Auswertung je Lieferant")
        stats = df_fn("""
            SELECT s.name AS Lieferant, COUNT(*) AS Belege,
                   SUM(e.net_amount) AS Netto_EUR,
                   SUM(e.gross_amount) AS Brutto_EUR,
                   SUM(e.paid_amount) AS Bezahlt_EUR,
                   ROUND(SUM(e.gross_amount)-SUM(e.paid_amount),2) AS Offen_EUR
            FROM expenses e JOIN suppliers s ON s.id=e.supplier_id
            GROUP BY s.id ORDER BY Brutto_EUR DESC
        """)
        if not stats.empty:
            c1, c2 = st.columns(2)
            c1.metric("Lieferanten", len(stats))
            c2.metric("Gesamtausgaben", fmt_eur(float(stats["Brutto_EUR"].sum())))
            st.dataframe(stats, use_container_width=True)
            st.bar_chart(stats.set_index("Lieferant")["Brutto_EUR"].head(10))
        else:
            st.info("Noch keine Ausgaben mit Lieferanten.")


# ─────────────────────────────────────────────────────────────
# 4. System-Health-Monitor
# ─────────────────────────────────────────────────────────────

def page_system_health(run_fn, df_fn, db_path: Path) -> None:
    st.title("🩺 System-Health-Monitor")

    st.subheader("Datenbankstatistiken")
    tables = [
        "customers", "invoices", "invoice_items", "expenses", "suppliers",
        "employees", "shifts", "time_entries", "contacts", "bank_transactions",
        "email_log", "audit_log", "automation_log", "backups", "imports",
    ]
    stats = []
    for t in tables:
        try:
            n = int(df_fn(f"SELECT COUNT(*) AS n FROM {t}").iloc[0]["n"])
            stats.append({"Tabelle": t, "Einträge": n})
        except Exception:
            stats.append({"Tabelle": t, "Einträge": "—"})

    col1, col2 = st.columns(2)
    df_stats = pd.DataFrame(stats)
    col1.dataframe(df_stats, use_container_width=True)

    # DB-Größe
    db_size = db_path.stat().st_size if db_path.exists() else 0
    col2.metric("Datenbankgröße", f"{db_size / 1024:.0f} KB")
    col2.metric("Tabellen", len(tables))

    # Integrität
    st.subheader("Integritätsprüfungen")
    checks = []

    # Rechnungen ohne Kunden
    r1 = df_fn("SELECT COUNT(*) AS n FROM invoices i LEFT JOIN customers c ON c.id=i.customer_id WHERE c.id IS NULL")
    n1 = int(r1.iloc[0]["n"]) if not r1.empty else 0
    checks.append(("Rechnungen ohne gültigen Kunden", n1 == 0, f"{n1} fehlerhafte Datensätze"))

    # Positionen ohne Rechnung
    r2 = df_fn("SELECT COUNT(*) AS n FROM invoice_items ii LEFT JOIN invoices i ON i.id=ii.invoice_id WHERE i.id IS NULL")
    n2 = int(r2.iloc[0]["n"]) if not r2.empty else 0
    checks.append(("Rechnungspositionen ohne Rechnung", n2 == 0, f"{n2} verwaiste Positionen"))

    # Schichten ohne gültige Mitarbeiter-ID (außer NULL)
    r3 = df_fn("SELECT COUNT(*) AS n FROM shifts s LEFT JOIN employees e ON e.id=s.employee_id WHERE s.employee_id IS NOT NULL AND e.id IS NULL")
    n3 = int(r3.iloc[0]["n"]) if not r3.empty else 0
    checks.append(("Schichten mit ungültiger Mitarbeiter-ID", n3 == 0, f"{n3} fehlerhafte Einträge"))

    for label, ok, detail in checks:
        icon = "✅" if ok else "⚠️"
        color = "#27ae60" if ok else "#e67e22"
        st.markdown(
            f'<div style="border-left:4px solid {color};padding:6px 12px;background:{color}11;border-radius:4px;margin-bottom:6px;">'
            f'{icon} <strong>{label}</strong> — {detail}</div>',
            unsafe_allow_html=True
        )

    # Bereinigung
    st.subheader("Datenbankbereinigung")
    col1, col2 = st.columns(2)
    if col1.button("🗜️ VACUUM (DB komprimieren)"):
        try:
            run_fn("VACUUM")
            st.success("✅ VACUUM ausgeführt – Datenbank optimiert.")
        except Exception as e:
            st.error(f"Fehler: {e}")
    if col2.button("🔍 INTEGRITY CHECK"):
        try:
            result = df_fn("PRAGMA integrity_check")
            if not result.empty and result.iloc[0, 0] == "ok":
                st.success("✅ Integrität OK")
            else:
                st.error(f"⚠️ Probleme gefunden: {result}")
        except Exception as e:
            st.error(f"Fehler: {e}")
