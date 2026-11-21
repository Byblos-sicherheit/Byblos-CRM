"""CRM Stufe 8 – Seiten "Zwei-Faktor-Auth" (eigenes Konto) und "Betriebsstatus" (Admin)."""
from __future__ import annotations

import io

import streamlit as st

import crm_stage8

ICON = {"ok": "✅", "warnung": "⚠️", "fehler": "❌"}


def page_two_factor_v2(conn_fn, log_fn, username) -> None:
    st.title("🔐 Zwei-Faktor-Authentifizierung")
    if not username:
        st.error("Bitte zuerst anmelden.")
        return
    with conn_fn() as conn:
        crm_stage8.ensure_tables(conn)
        row = conn.execute("SELECT totp_secret, enabled FROM two_factor_secrets WHERE username=?", (username,)).fetchone()
        if row and row[1] == 1:
            st.success("2FA ist für Ihr Konto aktiv.")
            code = st.text_input("Aktueller Code zum Deaktivieren", max_chars=6, key="tfa_disable_code")
            if st.button("2FA deaktivieren"):
                try:
                    crm_stage8.disable_2fa(conn, username, code)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    log_fn("2fa_disabled", username)
                    st.rerun()
            return
        if not row:
            st.info("2FA schützt Ihr Konto zusätzlich mit einem Code aus einer Authenticator-App.")
            if st.button("2FA einrichten"):
                crm_stage8.start_2fa(conn, username)
                st.rerun()
            return
        secret = row[0]
        uri = crm_stage8.provisioning_uri(username, secret)
        st.markdown("**1.** QR-Code mit der Authenticator-App scannen oder den Schlüssel manuell eingeben.")
        try:
            import qrcode
            buf = io.BytesIO()
            qrcode.make(uri).save(buf, format="PNG")
            st.image(buf.getvalue(), width=220)
        except ImportError:
            st.caption("QR-Code nicht verfügbar – Schlüssel manuell eingeben.")
        st.code(secret)
        st.markdown("**2.** Den angezeigten 6-stelligen Code eingeben. Erst dann wird 2FA aktiv.")
        code = st.text_input("Code aus der App", max_chars=6, key="tfa_confirm_code")
        if st.button("✅ 2FA aktivieren"):
            try:
                crm_stage8.confirm_2fa(conn, username, code)
            except ValueError as exc:
                st.error(str(exc))
            else:
                log_fn("2fa_enabled", username)
                st.success("2FA ist aktiv. Beim nächsten Login wird der Code abgefragt.")


def page_operations_v2(db_path, backup_dir, verify_password, log_fn, role) -> None:
    st.title("🩺 Betriebsstatus")
    if role != "Inhaber/Admin":
        st.error("Nur für Inhaber/Admin.")
        return
    report = crm_stage8.health_report(db_path, verify_password)
    st.table([{"": ICON[s], "Prüfung": n, "Detail": d} for n, s, d in report])
    a, b = st.columns(2)
    if a.button("💾 Jetzt sichern (konsistent, geprüft)"):
        target, digest = crm_stage8.backup_db(db_path, backup_dir, note="manuell")
        log_fn("backup_stage8", target.name)
        st.success(f"Sicherung {target.name} angelegt, SHA-256 {digest[:16]}…")
    b.caption("Wiederherstellen und Migrieren nur über die Kommandozeile mit vorheriger Freigabe – siehe BETRIEB.md.")
    st.subheader("Regelmäßige Wartung einrichten (auf dem Zielrechner)")
    st.markdown("Erst wenn diese Aufgaben eingerichtet sind und an mehreren Tagen gelaufen sind, "
                "zeigt das Dashboard die Datensicherung als **aktiv (nachgewiesen)**.")
    st.code("python crm_stage8.py backup   # täglich, z. B. 02:30\n"
            "python crm_stage8.py health   # täglich; Exit-Code 1 = Fehler (Monitoring)", language="bash")
