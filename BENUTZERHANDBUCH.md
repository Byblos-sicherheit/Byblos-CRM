# Byblos CRM v2 – Benutzerhandbuch

**Version 2.0 | © Byblos Sicherheitsdienst & Service**

---

## Inhaltsverzeichnis

1. Systemanforderungen & Installation
2. Erster Start & Onboarding
3. Navigation
4. Kunden & CRM
5. Rechnungsverwaltung
6. Ausgaben & BWA
7. Mitarbeiterverwaltung
8. Dienstplanung
9. Personal-Features
10. Buchhaltung & DATEV
11. Berichte & Auswertungen
12. KI-Funktionen
13. Backup & Sicherheit
14. API & Integrationen
15. Troubleshooting

---

## 1. Systemanforderungen & Installation

### Voraussetzungen
- **Betriebssystem:** Windows 10/11, macOS 11+, Ubuntu 20.04+
- **Python:** Version 3.10 oder höher
- **RAM:** Mindestens 512 MB frei (empfohlen: 2 GB)
- **Festplatte:** Mindestens 500 MB für App + Datenbank + PDFs

### Installation (Windows)
1. Python 3.11 installieren: https://python.org/downloads
2. ZIP-Datei entpacken in `C:\ByblosCRM\`
3. `BUILD_WINDOWS.bat` doppelklicken (erstellt EXE automatisch)
4. App starten: `ByblosCRM.exe`

### Installation (Linux/Mac/Server)
```bash
cd byblos_crm_app
pip install -r requirements.txt
streamlit run app.py
```

### Docker (empfohlen für Server)
```bash
docker compose up -d
# App läuft auf http://localhost:8501
```

---

## 2. Erster Start & Onboarding

Beim ersten Start erscheint der **Onboarding-Assistent** (🚀 Einrichtung → Onboarding-Assistent).

### Pflicht-Schritte:
1. **Firmendaten** eintragen (Einstellungen → Firmendaten)
2. **Ersten Kunden** anlegen (Kunden → Neu)
3. **SMTP einrichten** für E-Mail-Versand (Einstellungen → E-Mail)
4. **Logo hochladen** (Einstellungen → Firmendaten → Logo)
5. **Ersten Mitarbeiter** anlegen
6. **Erstes Backup** erstellen

### Standard-Login:
- **Benutzername:** admin
- **Passwort:** admin123 (bitte sofort ändern!)

---

## 3. Navigation

Die Sidebar ist in **thematische Gruppen** gegliedert:

| Symbol | Gruppe | Inhalt |
|---|---|---|
| 📊 | Übersicht | Dashboard, Berichte, Benachrichtigungen |
| 👥 | CRM | Kunden, Kontakte, KI-Auswertungen |
| 💰 | Finanzen | Rechnungen, Ausgaben, Angebote |
| 📥 | Import/Export | Intelligenter Import, Backup |
| 🚚 | Lieferanten | Lieferantenverwaltung |
| 🔄 | Dauerrechnungen | Wiederkehrende Rechnungen |
| 🏖️ | Personal Plus | Urlaubsplanung, Fahrtenbuch |
| 📊 | SLA & Projekte | SLA-Monitoring, Projekte |
| 🏦 | DATEV & Steuern | DATEV-Mapping, Steuerkalender |
| 🔔 | Benachrichtigungen | Telegram, Webhooks |
| 📈 | Betrieb | Betriebskosten, Checklisten |
| 💶 | Lohn & Berichte | Lohnabrechnung, Aging, Wiedervorlagen |
| 🎓 | Qualifikationen | Zertifikate, Schichttausch |
| 🧮 | Kalkulation | Kostenvoranschlag, SEPA |
| 🔌 | API | JSON-API, iCal, KI-Suche |
| ☁️ | Cloud | Backup, Live-Betrieb |
| 🛡️ | Sicherheit | 2FA, DSGVO |

---

## 4. Kunden & CRM

### Kunden anlegen
1. Kunden → Neue Kunden
2. Pflichtfeld: **Firmenname**
3. Optional: Kontaktperson, E-Mail, Telefon, Adresse
4. Kunden-Nr. wird automatisch vergeben (SD-0001 ff.)

### Kontakthistorie
- Jedes Telefonat, Meeting, E-Mail dokumentieren
- **Wiedervorlagen** für Folgeaktionen setzen
- Timeline je Kunde unter "Kunden-Timeline"

### KI-Auswertungen
- **Kunden-Scoring:** Note A+–F basierend auf Zahlungsverhalten
- **Anomalie-Erkennung:** Ungewöhnliche Rechnungsbeträge
- **Umsatz-Prognose:** Bis 12 Monate voraus

---

## 5. Rechnungsverwaltung

### Rechnung erstellen
1. Rechnungen → Neue Rechnung
2. Kunde auswählen, Datum und Fälligkeit setzen
3. Positionen direkt im Formular erfassen
4. Rechnungs-Nr. wird automatisch vergeben (RE-0001 ff.)

### PDF erstellen & versenden
- Rechnungen → PDF & Versand → "PDF erstellen"
- PDF wird automatisch mit Firmenlogo, IBAN und GiroCode erstellt
- Direkt aus der App per E-Mail versenden

### Zahlungseingang buchen
- Rechnungen → Zahlung buchen
- Teilzahlungen möglich (Status: "teilbezahlt")
- Mehrere Zahlungsarten: Überweisung, Bar, SEPA, PayPal

### Mahnwesen
- Automatisch: Tagesroutine markiert überfällige Rechnungen
- Manuell: Automatik → Mahnwesen → "Mahnungen vorbereiten"
- Mahngebühren nach BGB §288 automatisch berechnen

---

## 6. Ausgaben & BWA

### Ausgabe erfassen
- Ausgaben → Ausgabe erfassen
- Beleg hochladen (PDF/JPG) → wird in Personalakte gespeichert
- KI schlägt BWA-Kategorie vor (21 Kategorien nach SKR03)

### BWA-Monatsbericht
- Ausgaben → BWA-Auswertung → Monat wählen
- Zeigt Umsatz, Ausgaben, Vorsteuer, Ergebnis
- Vergleich mit Vorjahr unter "BWA-Jahresvergleich"

---

## 7. Mitarbeiterverwaltung

### Mitarbeiter anlegen
- Mitarbeiter → Neu anlegen
- Pflicht: Name, Mitarbeiter-Nr.
- Optional: Stundenlohn, IBAN für Lohnzahlung, Vertragsart

### Qualifikationen & Zertifikate
- Qualifikationen → Qualifikation eintragen
- 14 vordefinierte Typen (§34a GewO, Erste-Hilfe etc.)
- Ablaufwarnung 60 Tage vorher automatisch

### Digitale Personalakte
- Personalakte → Mitarbeiter wählen → Dokument hochladen
- Arbeitsvertrag, Zeugnisse, Zertifikate zentral
- Automatische Ablaufüberwachung

---

## 8. Dienstplanung

### Schicht anlegen
- Dienstplan → Neue Schicht
- Mitarbeiter und Objekt zuordnen
- Wiederholschichten: Täglich/Wöchentlich/Monatlich

### GPS-Stempeluhr
- GPS-Stempeluhr → Mitarbeiter wählen → Einstempeln
- Standortkoordinaten optional
- Schicht wird automatisch auf "bestätigt" gesetzt

### Schicht-Tauschbörse
- Mitarbeiter bietet Schicht an
- Andere Mitarbeiter übernehmen
- Manager genehmigt → Schicht automatisch neu zugeordnet

---

## 9. Personal-Features

### Lohnabrechnung
- Lohnabrechnung → Abrechnung erstellen
- Brutto, SV-Abzüge, Lohnsteuer, Netto
- PDF-Lohnzettel mit Unterschriftsfeldern
- Massenversand per E-Mail

### Urlaub
- Urlaubsplanung → Antrag stellen
- Genehmigung durch Manager
- Urlaubskonto mit Resturlaubsberechnung

### Überstunden
- Überstunden-Ausgleich → Antrag
- Als Freizeitausgleich oder Auszahlung

### Minijobler-Rechner
- Minijobler-Rechner → Stunden + Stundenlohn eingeben
- Ampel: Grün (unter 538 €), Gelb (Midijob), Rot (Regelan)

---

## 10. Buchhaltung & DATEV

### DATEV-Export
- DATEV & Steuern → DATEV-Mapping
- SKR03 und SKR04 je Kostenart editierbar
- Export als CSV oder Excel mit korrekten Buchungskonten

### Steuerkalender
- Steuerkalender → "Steuertermine einrichten"
- USt-Voranmeldung, Lohnsteuer, SV, Vorauszahlungen
- Status-Tracking (offen/eingereicht/bezahlt)

### GoBD-Konformität
- Archiv/GoBD → GoBD-Checkliste
- 6 automatische Prüfpunkte
- Score 0–6 mit Handlungsempfehlungen

---

## 11. Berichte & Auswertungen

### Monatsbericht als PDF
- PDF-Berichte → Monat wählen → "PDF erstellen"
- KPI-Zusammenfassung, Rechnungsliste, Ausgaben, Offene Posten

### Executive Summary
- Executive Summary → 1-seitiger Managementbericht als PDF
- 8 KPIs, Top-5-Kunden, farbkodiertes Ergebnis

### Aging-Report (Debitorenalterung)
- Aging-Report → zeigt offene Rechnungen nach Alter
- 0–30 / 31–60 / 61–90 / >90 Tage
- Automatische Handlungsempfehlungen

---

## 12. KI-Funktionen

### KI-Chatbot
- KI-Assistent → Chatbot
- Natürlichsprachliche Fragen: "Umsatz diesen Monat?", "Überfällige Rechnungen?"
- 10 vordefinierte Antwortmuster

### Semantische Suche
- Erweitert → KI-Suche
- TF-IDF über alle Tabellen gleichzeitig
- Relevanz-Ranking in Prozent

### BWA-Auto-Kategorisierung
- BWA-Auto → Neue Banktransaktionen automatisch kategorisieren
- KI + Regelbasiertes Fallback
- Massenbuchen mit einem Klick

---

## 13. Backup & Sicherheit

### Automatisches Backup
- Täglich via Tagesroutine (Automatik → Tagesroutine)
- Cloud-Upload zu Nextcloud/WebDAV konfigurierbar
- Backup-Monitor zeigt Alter und Größe

### Verschlüsseltes Backup
- Betrieb → Verschlüsseltes Backup
- AES-256 via Python Cryptography (PBKDF2 + Fernet)
- Passwort sicher aufbewahren!

### Zwei-Faktor-Authentifizierung
- Sicherheit → 2FA
- TOTP (Google Authenticator / Authy)
- QR-Code oder manueller Secret-Import

---

## 14. API & Integrationen

### JSON-API (einfach)
- JSON-API → Datensatz als JSON herunterladen
- Kunden, Rechnungen, Mitarbeiter, Schichten, KPIs

### FastAPI REST-Server
- FastAPI-Server → api_server.py starten
- `uvicorn api_server:app --port 8000`
- Vollständige Swagger-Dokumentation unter /docs

### Telegram-Benachrichtigungen
- Benachrichtigungen → Einrichtung
- BotFather → Neuen Bot erstellen
- Token + Chat-ID eintragen

### MS Teams / Slack / Discord
- Webhooks → Neuer Webhook
- URL aus Teams/Slack/Discord Webhook-Einstellungen
- Test-Nachricht direkt aus der App

### iCal/ICS-Export
- Kalender-Export → Schichten/Steuertermine/Wiedervorlagen
- In Google Calendar, Outlook, Apple Kalender importieren

---

## 15. Troubleshooting

### App startet nicht
```bash
# Abhängigkeiten prüfen:
pip install -r requirements.txt
# Datenbank-Pfad prüfen:
ls -la byblos_crm.db
# App mit Debug-Output starten:
streamlit run app.py --logger.level=debug
```

### Datenbankfehler
- Systemgesundheit → INTEGRITY CHECK durchführen
- Falls Fehler: Letztes Backup einspielen
- Support: Backup-Datei und Fehlermeldung mitschicken

### PDF-Erstellung fehlerhaft
```bash
pip install --upgrade reportlab
```

### E-Mail wird nicht gesendet
- Einstellungen → E-Mail → Test-E-Mail senden
- SMTP-Port und SSL/TLS-Einstellung prüfen
- Gmail: App-Passwort statt normales Passwort verwenden

### QR-Code fehlt auf Rechnungen
```bash
pip install "qrcode[pil]"
```

### OCR nicht verfügbar
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-deu
pip install pdf2image
```

---

## Kontakt & Support

**Byblos Sicherheitsdienst & Service**

Bei technischen Fragen: FEHLERBEHEBUNG.md im Installationsverzeichnis

---

*Byblos CRM v2.0 – Entwickelt mit Streamlit, SQLite, ReportLab*
