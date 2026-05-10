"""
extensions_v2_finance_time_ops.py – DynDNS Auto-Update + System-Utilities
==========================================================================
1. DynDNS Auto-Update (DuckDNS, No-IP, Strato)
2. Auto-Update Checker (neue Versionen)
3. System-Utilities (Port-Check, IP-Refresh)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import socket
import threading
import time

import streamlit as st


# ─────────────────────────────────────────────────────────────
# DynDNS Auto-Update
# ─────────────────────────────────────────────────────────────

def update_duckdns(token: str, domain: str) -> Tuple[bool, str]:
    """Aktualisiert DuckDNS mit aktueller IP."""
    try:
        import urllib.request
        subdomain = domain.replace(".duckdns.org", "")
        url = f"https://www.duckdns.org/update?domains={subdomain}&token={token}&ip="
        with urllib.request.urlopen(url, timeout=10) as r:
            result = r.read().decode().strip()
            return result == "OK", result
    except Exception as e:
        return False, str(e)


def update_noip(username: str, password: str, hostname: str) -> Tuple[bool, str]:
    """Aktualisiert No-IP mit aktueller IP."""
    try:
        import urllib.request, base64
        url = f"https://dynupdate.no-ip.com/nic/update?hostname={hostname}"
        creds = base64.b64encode(f"{username}:{password}".encode()).decode()
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Basic {creds}")
        req.add_header("User-Agent", "ByblosCRM/2.0 admin@byblos.de")
        with urllib.request.urlopen(req, timeout=10) as r:
            result = r.read().decode().strip()
            ok = result.startswith("good") or result.startswith("nochg")
            return ok, result
    except Exception as e:
        return False, str(e)


def get_current_public_ip() -> str:
    try:
        import urllib.request
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as r:
            return r.read().decode().strip()
    except Exception:
        return ""


def start_dyndns_updater(provider: str, config: dict, interval_min: int = 5) -> threading.Thread:
    """Startet einen Hintergrund-Thread der DynDNS regelmäßig aktualisiert."""
    def updater():
        last_ip = ""
        while True:
            try:
                current_ip = get_current_public_ip()
                if current_ip and current_ip != last_ip:
                    if provider == "duckdns":
                        ok, msg = update_duckdns(config.get("token",""), config.get("domain",""))
                    elif provider == "noip":
                        ok, msg = update_noip(config.get("username",""),
                                              config.get("password",""),
                                              config.get("hostname",""))
                    else:
                        ok, msg = False, "Unbekannter Anbieter"
                    if ok:
                        last_ip = current_ip
            except Exception:
                pass
            time.sleep(interval_min * 60)

    t = threading.Thread(target=updater, daemon=True)
    t.start()
    return t


def page_dyndns_manager(run_fn, df_fn, get_setting_fn, set_setting_fn) -> None:
    st.title("🌐 DynDNS Auto-Update")
    st.caption("Automatische Aktualisierung deiner DynDNS-Domain wenn sich die IP ändert.")

    PROVIDERS = {
        "duckdns": "🦆 DuckDNS (kostenlos)",
        "noip":    "🔗 No-IP (kostenlos/kostenpflichtig)",
        "strato":  "🇩🇪 Strato DynDNS",
        "manual":  "⚙️ Manuell / Andere",
    }

    tabs = st.tabs(["⚙️ Einrichten", "📊 Status", "📖 Anleitung"])

    with tabs[0]:
        provider = st.selectbox("DynDNS-Anbieter",
                                list(PROVIDERS.values()),
                                index=list(PROVIDERS.values()).index(
                                    PROVIDERS.get(get_setting_fn("dyndns_provider","duckdns"),
                                                  PROVIDERS["duckdns"])))
        prov_key = [k for k,v in PROVIDERS.items() if v == provider][0]

        with st.form("dyndns_form"):
            if prov_key == "duckdns":
                st.markdown("**DuckDNS einrichten:** https://www.duckdns.org → kostenlos registrieren")
                token = st.text_input("DuckDNS Token", get_setting_fn("dyndns_token",""),
                                       type="password",
                                       help="Auf duckdns.org nach Login oben sichtbar")
                domain = st.text_input("Domain", get_setting_fn("dyndns_domain",""),
                                        placeholder="meincrm.duckdns.org")
                interval = st.slider("Update-Intervall (Minuten)", 1, 60, 5)

            elif prov_key == "noip":
                st.markdown("**No-IP einrichten:** https://www.noip.com → kostenlos registrieren")
                username = st.text_input("No-IP Benutzername", get_setting_fn("noip_username",""))
                password = st.text_input("No-IP Passwort", get_setting_fn("noip_password",""),
                                          type="password")
                hostname = st.text_input("Hostname", get_setting_fn("noip_hostname",""),
                                          placeholder="meincrm.ddns.net")
                interval = st.slider("Update-Intervall (Minuten)", 1, 60, 5)

            else:
                st.info("Bitte manuell konfigurieren oder anderen Anbieter wählen.")
                interval = 5

            auto_start = st.checkbox("Automatisch beim App-Start updaten",
                                      value=get_setting_fn("dyndns_auto","0") == "1")

            if st.form_submit_button("💾 Speichern", type="primary"):
                set_setting_fn("dyndns_provider", prov_key)
                set_setting_fn("dyndns_auto", "1" if auto_start else "0")
                set_setting_fn("dyndns_interval", str(interval))
                if prov_key == "duckdns":
                    set_setting_fn("dyndns_token", token)
                    set_setting_fn("dyndns_domain", domain)
                elif prov_key == "noip":
                    set_setting_fn("noip_username", username)
                    set_setting_fn("noip_password", password)
                    set_setting_fn("noip_hostname", hostname)
                st.success("✅ DynDNS-Einstellungen gespeichert!")

        # Manueller Test
        st.divider()
        st.subheader("🔍 Verbindungstest")
        col1, col2 = st.columns(2)

        current_ip = get_current_public_ip()
        col1.metric("Aktuelle öffentliche IP", current_ip or "Nicht ermittelbar")

        saved_domain = get_setting_fn("dyndns_domain", "")
        if saved_domain and col2.button("🔄 DynDNS jetzt aktualisieren", type="primary"):
            prov = get_setting_fn("dyndns_provider","duckdns")
            with st.spinner("Update läuft..."):
                if prov == "duckdns":
                    ok, msg = update_duckdns(
                        get_setting_fn("dyndns_token",""),
                        get_setting_fn("dyndns_domain","")
                    )
                elif prov == "noip":
                    ok, msg = update_noip(
                        get_setting_fn("noip_username",""),
                        get_setting_fn("noip_password",""),
                        get_setting_fn("noip_hostname","")
                    )
                else:
                    ok, msg = False, "Kein Anbieter konfiguriert"

            if ok:
                run_fn("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
                       ("dyndns_last_update", datetime.now().isoformat()))
                run_fn("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
                       ("dyndns_last_ip", current_ip))
                st.success(f"✅ Domain aktualisiert! IP: {current_ip}")
            else:
                st.error(f"❌ Fehler: {msg}")

        last_update = get_setting_fn("dyndns_last_update","")
        last_ip     = get_setting_fn("dyndns_last_ip","")
        if last_update:
            st.caption(f"Letztes Update: {last_update[:16]} · IP: {last_ip}")

    with tabs[1]:
        st.subheader("DynDNS-Status")
        prov = get_setting_fn("dyndns_provider","")
        domain = get_setting_fn("dyndns_domain","") or get_setting_fn("noip_hostname","")
        last_update = get_setting_fn("dyndns_last_update","")
        last_ip = get_setting_fn("dyndns_last_ip","")
        current = get_current_public_ip()

        c1, c2, c3 = st.columns(3)
        c1.metric("Anbieter", PROVIDERS.get(prov, "–") if prov else "–")
        c2.metric("Domain", domain or "–")
        c3.metric("Aktueller Status",
                  "✅ Aktuell" if (last_ip == current and last_ip) else "⚠️ Update nötig")

        if domain:
            st.info(f"**Dein CRM von überall erreichbar:** `http://{domain}:8501`")
            st.caption("Firewall: Port 8501 im Router weiterleiten (Port-Forwarding)")

        # Letzten Update-Verlauf
        history = df_fn("SELECT value AS IP, key AS Zeit FROM settings WHERE key LIKE 'dyndns_%' ORDER BY key DESC LIMIT 5")
        if not history.empty:
            st.dataframe(history, use_container_width=True)

    with tabs[2]:
        st.markdown("""
## DynDNS Schritt-für-Schritt (DuckDNS - kostenlos)

### 1. DuckDNS registrieren
1. **www.duckdns.org** aufrufen
2. Mit Google/GitHub einloggen (kostenlos)
3. Domain wählen: z.B. `bybloscrm.duckdns.org`
4. **Token** kopieren (oben auf der Seite)

### 2. Im CRM einrichten
- Tab "Einrichten" → Token + Domain eintragen → Speichern
- "DynDNS jetzt aktualisieren" klicken → Testen

### 3. Router konfigurieren (Port-Weiterleitung)
1. Router-Admin öffnen (meist `192.168.1.1` im Browser)
2. **Port-Weiterleitung / NAT** suchen
3. Neue Regel: **TCP Port 8501** → PC-IP (z.B. `192.168.1.100`)
4. Speichern

### 4. Von überall zugreifen
```
http://bybloscrm.duckdns.org:8501
```
Auf Handy, PC, überall — auch mit Mobilfunk! ✅

---

### Alternative: Cloudflare Tunnel (kein Router-Setup!)
Im CRM unter **🌐 Netzwerk → Remote-Zugang → ☁️ Cloudflare**  
→ Kein Router-Zugang nötig, sofort einsatzbereit
        """)
