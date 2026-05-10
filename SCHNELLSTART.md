# 🛡️ Byblos CRM v2 — Schnellstart

## ⚡ INSTALLATION (2 Minuten)

### Windows
1. ZIP entpacken
2. **`INSTALL_HIER_KLICKEN.bat`** doppelklicken
3. Warten bis „Installation erfolgreich" erscheint
4. `J` → Browser öffnet sich automatisch

### Linux / Mac
```bash
chmod +x INSTALL_LINUX_MAC.sh
./INSTALL_LINUX_MAC.sh
```

### Docker (Server)
```bash
docker compose up -d
# App: http://localhost:8501
# API: http://localhost:8000/docs
```

---

## 🚀 STARTEN

| System | Befehl |
|---|---|
| Windows | `BYBLOS_STARTEN.bat` doppelklicken |
| Linux/Mac | `byblos-crm` im Terminal |
| Docker | `docker compose up -d` |

**Browser:** http://localhost:8501  
**Login:** `admin` / `admin123` ← **sofort ändern!**

---

## 📱 REMOTE-ZUGANG (Handy / anderes Netz)

### Gleicher WLAN (einfachste Methode)
1. `BYBLOS_STARTEN.bat` → Modus **2** wählen
2. Im CRM: **🌐 Netzwerk → QR-Code** mit Handy scannen
3. Fertig ✅

### Von überall (anderes WLAN / Mobilfunk)
1. `BYBLOS_STARTEN.bat` → Modus **3** (Cloudflare)
2. Cloudflared herunterladen falls nötig (im CRM automatisch)
3. Generierte HTTPS-URL auf Handy öffnen ✅

### Dauerhaft mit DynDNS
1. DuckDNS.org → kostenlose Domain registrieren
2. Im CRM: **🌐 Netzwerk → DynDNS** → Token + Domain eintragen
3. Router: Port 8501 weiterleiten zu PC-IP
4. URL: `http://deinname.duckdns.org:8501` ✅

---

## 🔑 WICHTIGSTE ERSTE SCHRITTE

1. **Passwort ändern:**  
   Einstellungen → Benutzer & Rollen → Admin → Passwort setzen

2. **Firmendaten eintragen:**  
   Einstellungen → Firmendaten (für Rechnungs-PDF)

3. **Ersten Kunden anlegen:**  
   Kunden → Neu anlegen

4. **SMTP einrichten (E-Mail-Versand):**  
   Einstellungen → E-Mail / SMTP

5. **Backup konfigurieren:**  
   ☁️ Cloud & Betrieb → Cloud-Backup

---

## 📊 WAS IST ENTHALTEN

| Kategorie | Features |
|---|---|
| **CRM** | Kunden, Kontakte, Scoring, Timeline |
| **Rechnungen** | CRUD, PDF, QR-Code, Storno, Freigabe |
| **Personal** | Lohnabrechnung, Urlaub, Überstunden, §34a |
| **Dienstplan** | GPS-Stempeluhr, Schichttausch, Auto-Planung |
| **Buchhaltung** | BWA, DATEV, Kassenbuch, UStVA |
| **Compliance** | GoBD, DSGVO, Wachbuch, Unfallprotokoll |
| **KI** | Chatbot, Scoring, Semantiksuche |
| **Remote** | LAN, Cloudflare, ngrok, DynDNS |
| **API** | REST (FastAPI), JSON-Export, Webhooks |
| **Sicherheit** | 2FA TOTP, Rate-Limiting, Verschlüsselung |

---

## 🆘 FEHLER-HILFE

| Problem | Lösung |
|---|---|
| App startet nicht | `python -m pip install streamlit` |
| Datenbank-Fehler | CRM → Einstellungen → DB-Migrationen |
| Installer-Fehler | `INSTALL.py` direkt mit Python ausführen |
| Port 8501 belegt | `BYBLOS_STARTEN.bat` → Port ändern |
| Kein Browser | Manuell öffnen: http://localhost:8501 |

**Detailliert:** `FEHLERBEHANDLUNG_WINDOWS.md` im Paket

---

*Byblos CRM v2 · 39 Module · 28.700+ Zeilen · 167 Seiten · 127 Tabellen*
