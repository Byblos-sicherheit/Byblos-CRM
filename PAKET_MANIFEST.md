# Paket-Manifest

Dieses Paket baut auf `byblos_crm_comprehensive_package.zip` auf und erweitert es um folgende Punkte:

- OCR-Fallback für gescannte PDFs über `pdf2image` + `pytesseract`
- Bild-/Scan-Import für PNG/JPG/JPEG
- optionale Tesseract-OCR-Unterstützung ohne App-Absturz, falls Tesseract fehlt
- aktualisierte `requirements.txt`
- Windows Precheck-Script
- Dependency-Installer für Windows
- Run-App Script für Windows
- Beispielscript für Windows Code Signing
- Android Keystore-Hinweise
- Smoke-Test-Dateien
- finale Checkliste
- Startdatei `START_HIER.txt`

## Prüfung in dieser Umgebung

- Python-Syntaxprüfung für `app.py` und `ml_logic.py`: bestanden.
- Vollständiger Smoke-Test mit Streamlit konnte in dieser Umgebung nicht ausgeführt werden, weil Streamlit hier nicht installiert ist. Das Testskript ist im Paket enthalten und muss lokal nach `pip install -r requirements.txt` ausgeführt werden.

## Ergänzung: Komplett-System

Neu hinzugefügt:
- `byblos_crm_app/extensions_complete_system.py`
- neue App-Seiten: Mehrfach-Rechnungsimport, Schnellsuche/KI, Firmenprofile, Verträge & Dokumente
- `KOMPLETT_SYSTEM_ERWEITERUNG.md`

## Finance & Time Ops Erweiterung

Neu hinzugefügt:

- byblos_crm_app/extensions_finance_time_ops.py
- FINANCE_TIME_OPS_ERWEITERUNG.md

Neue CRM-Seiten:

- E-Rechnung Prüfung
- Zahlungen & Mahnwesen
- Zeiten freigeben

## Erweiterung: Payroll & Reconciliation Ops

- Datei: byblos_crm_app/extensions_payroll_recon_ops.py
- Menüpunkte: Offene Posten, Zeitkonto & Payroll, Ops Prüfungen
- Dokumentation: PAYROLL_RECON_OPS_ERWEITERUNG.md
