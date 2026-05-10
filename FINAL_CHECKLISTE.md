# Finale Checkliste Byblos CRM

## Code und App
- [ ] `python -m pip install -r byblos_crm_app\requirements.txt` erfolgreich
- [ ] `tests\run_smoke_test.bat` erfolgreich
- [ ] App startet mit `scripts\run_app_windows.bat`
- [ ] Login funktioniert
- [ ] Kunden/Rechnungen/Ausgaben funktionieren
- [ ] CSV/Excel-Import funktioniert
- [ ] PDF-Import mit digitaler PDF funktioniert
- [ ] Bild-/Scan-OCR mit Tesseract funktioniert

## OCR
- [ ] Tesseract OCR installiert
- [ ] Tesseract im Windows PATH
- [ ] Deutsche Sprachdatei `deu.traineddata` installiert
- [ ] Poppler installiert, wenn gescannte PDF-Seiten via `pdf2image` verarbeitet werden sollen

## Windows Distribution
- [ ] EXE mit `installer\build_exe.bat` gebaut
- [ ] EXE lokal getestet
- [ ] Setup.exe mit Inno Setup gebaut
- [ ] Setup.exe installiert und deinstalliert getestet
- [ ] EXE/Setup signiert

## MSIX
- [ ] MSIX mit Microsoft MSIX Packaging Tool gebaut
- [ ] Publisher passt zum Zertifikat
- [ ] MSIX signiert
- [ ] MSIX Installation getestet

## Android
- [ ] echte CRM-URL in `MainActivity.java` eingetragen
- [ ] echtes Icon ersetzt
- [ ] APK/AAB in Android Studio gebaut
- [ ] Release-Keystore erstellt und sicher gespeichert
- [ ] App auf echtem Android-Gerät getestet

## Datenschutz und Betrieb
- [ ] DSGVO-Prüfung durchgeführt
- [ ] Backup/Restore getestet
- [ ] Rollen/Rechte geprüft
- [ ] Zugriff auf CRM per HTTPS abgesichert
- [ ] Produktivdaten nicht in Testpaketen verteilt
