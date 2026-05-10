# 🛡️ Byblos CRM v2

<div align="center">

![Byblos CRM Logo](https://img.shields.io/badge/Byblos-CRM_v2-c0392b?style=for-the-badge&logo=shield&logoColor=white)

**Open Source CRM für Sicherheitsdienstleister**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-red.svg)](https://streamlit.io)
[![Code Lines](https://img.shields.io/badge/Code-30%2C000%2B_Zeilen-orange.svg)](#)
[![Pages](https://img.shields.io/badge/Seiten-176-purple.svg)](#)
[![Tests](https://img.shields.io/badge/Tests-72_Unit_Tests-green.svg)](#)

[🚀 Schnellstart](#schnellstart) · [📖 Dokumentation](#dokumentation) · [🤝 Mitmachen](#mitmachen) · [📸 Screenshots](#screenshots)

</div>

---

## 🌟 Was ist Byblos CRM?

Byblos CRM ist ein **vollständiges, kostenloses Open-Source-Management-System** speziell für Sicherheitsdienstleister, Wachdienste und ähnliche Unternehmen.

### ✨ Highlights

- 🏢 **176 Seiten** — alles was ein Sicherheitsunternehmen braucht
- 📱 **Remote-Zugang** — Handy, Tablet, überall erreichbar
- 🔒 **Datenschutz** — DSGVO-konform, Daten bleiben lokal
- 🤖 **KI-Features** — Scoring, Prognosen, Chatbot
- 💰 **100% kostenlos** — MIT-Lizenz, keine versteckten Kosten
- 🖥️ **Läuft lokal** — kein Cloud-Abo, keine monatlichen Gebühren

---

## 📋 Feature-Übersicht

<details>
<summary><b>👥 CRM & Kunden</b></summary>

- Kundenverwaltung mit Scoring (A+–F)
- Vollständige Kontakthistorie & Timeline
- Customer Lifetime Value (CLV) Analyse
- Kundenzufriedenheits-Umfragen
- Kunden-Jubiläen & Erinnerungen
- Angebote → Rechnungen Konvertierung

</details>

<details>
<summary><b>💰 Rechnungen & Finanzen</b></summary>

- Rechnungen mit PDF-Export & QR-Code/GiroCode
- Automatisches Mahnwesen (4 Eskalationsstufen)
- DATEV SKR03/SKR04 Export
- ZUGFeRD 2.3 E-Rechnung (EN-16931)
- SEPA pain.008 Lastschrift
- Buchungsjournal, Kassenbuch, Debitorenkontoblatt
- UStVA-Vorbereitung
- BWA automatisch aus Ausgaben
- Stripe Zahlungslinks

</details>

<details>
<summary><b>👮 Sicherheitsdienst-spezifisch</b></summary>

- 📔 Digitales Wachbuch (stündliche Einträge)
- 🏢 Objekt-Stammdaten (Gebäude, Liegenschaften)
- 🔑 Schlüsselverwaltung (Ausgabe/Rückgabe/Verlust)
- 🚨 Unfallmelde-Protokoll (BG-konform, §34a GewO)
- 📋 Dienstanweisung-Generator mit PDF-Export
- 🎪 Einsatzplanung Großveranstaltungen
- 📜 §34a GewO Registrierungs-Center
- 🚦 Arbeitszeit-Ampel (ArbZG §3, §5, §9)

</details>

<details>
<summary><b>👥 Personal & Dienstplan</b></summary>

- Lohnabrechnung mit Lohnzettel-PDF
- GPS-Stempeluhr (Schicht-Check-in)
- Dienstplan mit Schichttausch-Börse
- Automatische Schichtzuweisung nach Präferenzen
- Urlaubsplanung & Genehmigung
- Überstunden-Konto (kumuliert)
- §34a-Qualifikationsverwaltung
- Personalplanung Soll/Ist
- Reisekostenabrechnung

</details>

<details>
<summary><b>🤖 KI & Automatisierung</b></summary>

- Kunden-Scoring (A+–F) mit ML
- Umsatz-Prognose (30/60/90 Tage)
- Anomalie-Erkennung bei Rechnungen
- KI-Chatbot (10 natürlichsprachliche Queries)
- Semantische Suche (TF-IDF)
- BWA-Kategorie-Vorautorisierung
- Automatisches Mahnwesen

</details>

<details>
<summary><b>🌐 Remote-Zugang</b></summary>

- LAN-Zugang (Handy im gleichen WLAN) + QR-Code
- Cloudflare Tunnel (kostenlos, kein Router nötig)
- ngrok Tunnel
- DynDNS Auto-Update (DuckDNS, No-IP)
- Automatische Firewall-Regel
- 2FA für Remote-Zugang

</details>

<details>
<summary><b>🔒 Sicherheit & DSGVO</b></summary>

- TOTP 2-Faktor-Authentifizierung (Google Authenticator)
- Rollenbasierte Zugriffskontrolle (Admin/Manager/MA/Buchhalter)
- Rate-Limiting & Brute-Force-Schutz
- Session-Security mit Auto-Logout
- AES-256 Backup-Verschlüsselung
- DSGVO-Datenschutzcenter
- Vollständiger Audit-Log

</details>

<details>
<summary><b>☁️ Integrationen</b></summary>

- **E-Mail:** SMTP (Gmail, Outlook, eigener Server)
- **Messenger:** Telegram, WhatsApp Business, Teams, Slack, Discord
- **Cloud:** Dropbox API, Google Drive (rclone), WebDAV/Nextcloud
- **Zahlung:** Stripe Checkout, SEPA-Lastschrift
- **API:** FastAPI REST (12 Endpunkte), JSON-Export, Webhooks
- **Kalender:** iCal/ICS-Export
- **Automatisierung:** Zapier/Make Webhook-Templates

</details>

---

## 🚀 Schnellstart

### Option 1: Windows (empfohlen)

```
1. ZIP herunterladen und entpacken
2. INSTALL_HIER_KLICKEN.bat doppelklicken
3. Browser öffnet automatisch: http://localhost:8501
4. Login: admin / admin123
```

### Option 2: Linux / macOS

```bash
git clone https://github.com/byblos-security/byblos-crm.git
cd byblos-crm
chmod +x INSTALL_LINUX_MAC.sh
./INSTALL_LINUX_MAC.sh
```

### Option 3: Docker

```bash
git clone https://github.com/byblos-security/byblos-crm.git
cd byblos-crm
docker compose up -d
# App: http://localhost:8501
```

### Option 4: Manuell

```bash
pip install -r byblos_crm_app/requirements.txt
cd byblos_crm_app
streamlit run app.py
```

**Erster Login:** `admin` / `admin123` ← sofort ändern!

---

## 📱 Remote-Zugang einrichten

### Handy im gleichen WLAN (sofort)
```
BYBLOS_STARTEN.bat → Modus 2 → QR-Code scannen
```

### Von überall (anderes WLAN / Mobilfunk)
```
BYBLOS_STARTEN.bat → Modus 3 (Cloudflare Tunnel)
→ HTTPS-URL wird automatisch generiert
→ Auf Handy öffnen
```

### Dauerhaft mit eigenem Domain-Namen
```
1. DuckDNS.org kostenlose Domain registrieren
2. App → 🌐 Netzwerk → DynDNS → Token eintragen
3. Router: Port 8501 weiterleiten
4. URL: http://meincrm.duckdns.org:8501
```

---

## 🏗️ Architektur

```
byblos_crm_v2/
├── byblos_crm_app/          # Haupt-App
│   ├── app.py               # Router (176 Seiten)
│   ├── ml_logic.py          # KI/ML Module
│   ├── api_server.py        # FastAPI REST
│   ├── extensions_v2_*.py   # Feature-Module (40+)
│   └── requirements.txt
├── tests/
│   └── test_byblos_crm.py   # 72 Unit-Tests
├── nginx/
│   └── nginx.conf           # HTTPS Reverse-Proxy
├── .github/workflows/       # CI/CD
├── docker-compose.yml       # Docker
├── INSTALL_HIER_KLICKEN.bat # Windows-Installer
├── INSTALL_LINUX_MAC.sh     # Linux/Mac-Installer
├── BYBLOS_STARTEN.bat       # Windows-Starter
└── LICENSE                  # MIT License
```

**Tech-Stack:**
- **Frontend:** Streamlit 1.30+
- **Backend:** Python 3.10+, SQLite
- **REST-API:** FastAPI + uvicorn
- **PDF:** ReportLab
- **ML:** scikit-learn
- **Verschlüsselung:** cryptography (AES-256)

---

## 🤝 Mitmachen

Byblos CRM ist Open Source — Beiträge sind herzlich willkommen!

```bash
# Fork erstellen auf GitHub
git clone https://github.com/DEIN-USERNAME/byblos-crm.git
cd byblos-crm
python -m venv venv && source venv/bin/activate
pip install -r byblos_crm_app/requirements.txt
```

**Wie beitragen:**
1. 🐛 **Bug melden** → [GitHub Issues](https://github.com/byblos-security/byblos-crm/issues)
2. 💡 **Feature-Idee** → [GitHub Discussions](https://github.com/byblos-security/byblos-crm/discussions)
3. 🔧 **Pull Request** → Bitte [CONTRIBUTING.md](CONTRIBUTING.md) lesen
4. ⭐ **Star geben** → Hilft anderen das Projekt zu finden!

---

## 📊 Projekt-Statistiken

| Kennzahl | Wert |
|---|---|
| Python-Module | 42 |
| Code-Zeilen | 30.272+ |
| Seiten / Routen | 176 |
| Datenbank-Tabellen | 127 |
| Unit-Tests | 72 |
| Integrationen | 15+ |
| Sprachen | Deutsch |

---

## 📸 Screenshots

> *Screenshots werden nach erstem stabilen Release hinzugefügt*

---

## ❓ FAQ

**Ist die App wirklich kostenlos?**  
Ja, vollständig kostenlos. MIT-Lizenz bedeutet: kostenlos nutzen, ändern, weiterverteilen — auch kommerziell.

**Wo werden meine Daten gespeichert?**  
Lokal auf deinem PC (`byblos_crm.db`). Keine Cloud, kein Abo, keine Datenweitergabe.

**Läuft die App auf meinem Handy?**  
Die App läuft auf dem PC und ist über den Browser auf dem Handy erreichbar (LAN oder Tunnel).

**Muss ich programmieren können?**  
Nein. Der Installer richtet alles automatisch ein.

**Wie bekomme ich Updates?**  
```bash
git pull  # oder neue ZIP-Version herunterladen
```

**Wo bekomme ich Hilfe?**  
→ [GitHub Issues](https://github.com/byblos-security/byblos-crm/issues) · [Discussions](https://github.com/byblos-security/byblos-crm/discussions)

---

## 📄 Lizenz

**MIT License** — Open Source, kostenlos für alle Zwecke.

Siehe [LICENSE](LICENSE) für den vollständigen Text.

---

<div align="center">

**Entwickelt für die Sicherheitsbranche 🛡️**

Wenn dieses Projekt hilft, gib einen ⭐ auf GitHub!

</div>
