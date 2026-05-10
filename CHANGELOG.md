# Changelog - Byblos CRM

Alle wichtigen Änderungen werden in dieser Datei dokumentiert.
Format: [Keep a Changelog](https://keepachangelog.com/de/1.0.0/)

## [2.0.0] - 2025-05-10

### 🎉 Open Source Release (MIT License)

### Hinzugefügt
- 176 Seiten / Routen in einer App
- 42 Python-Module, 30.000+ Zeilen Code
- 127 Datenbank-Tabellen
- 72 Unit-Tests
- Vollständiges §34a GewO Compliance-Center
- Digitales Wachbuch
- Schlüsselverwaltung
- Dienstanweisung-Generator mit PDF
- Einsatzplanung Großveranstaltungen
- Unfallmelde-Protokoll (BG-konform)
- Remote-Zugang: LAN + Cloudflare Tunnel + ngrok
- DynDNS Auto-Update (DuckDNS, No-IP)
- ZUGFeRD 2.3 E-Rechnung
- SEPA pain.008 XML
- AES-256 Backup-Verschlüsselung
- KI-Chatbot, Scoring, Semantiksuche
- FastAPI REST-Server (12 Endpunkte)
- Docker + nginx + systemd Deployment
- Windows-Installer (kein Admin, kein PyInstaller)
- Tages-Briefing Dashboard
- KPI-Ziele mit Fortschrittsbalken
- CLV-Analyse
- Schicht-Konflikt-Erkennung
- ArbZG-Ampel
- Währungsrechner
- Einsatzkosten-Kalkulator

### Geändert
- Installer von Inno Setup → Python-Skript (kein Admin nötig)
- Kein PyInstaller (Python 3.13 Kompatibilität)
- Desktop-Verknüpfung in %USERPROFILE%\Desktop (statt C:\Users\Public)

### Behoben
- IPersistFile::Save Code 0x80070005 (Admin-Rechte-Fehler)
- DeleteFile Code 5 (EXE gesperrt)
- PyInstaller multiprocessing PermissionError

## [1.0.0] - 2024-01-01

### Erstveröffentlichung
- Grundlegende CRM-Funktionen
- Rechnungsverwaltung
- Mitarbeiterverwaltung
