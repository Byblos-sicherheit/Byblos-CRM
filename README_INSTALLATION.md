# Byblos CRM – Installation und Distribution

Dieses Paket enthält den aktuellen Stand der Byblos‑CRM‑Webanwendung
(Python/Streamlit) inklusive der KI‑Logik zur Dokumentenklassifikation
und PDF‑Import.  Darüber hinaus findest du Skripte und Vorlagen, um
die Anwendung als ausführbares Windows‑Programm zu verpacken, einen
Windows‑Installer zu erstellen und eine einfache Android‑App zu
erstellen, die die Web‑Oberfläche per WebView lädt.

## Ordnerstruktur

```
final_package/
├── byblos_crm_app/        # Quellcode der CRM‑App (Streamlit)
├── installer/
│   ├── build_exe.bat      # Skript zum Erstellen der EXE mit PyInstaller
│   └── inno_setup.iss     # Inno‑Setup‑Skript für Windows‑Installer
├── msix/
│   └── README_MSIX.md     # Anleitung für MSIX‑Packaging
├── android/
│   ├── app/src/main/java/com/example/bybloscrm/MainActivity.java
│   ├── app/src/main/res/layout/activity_main.xml
│   ├── app/src/main/AndroidManifest.xml
│   └── README_ANDROID.md  # Anleitung zur Erstellung einer Android‑WebView
└── README_INSTALLATION.md # Diese Datei
```

## Windows‑Distribution

1. **EXE erstellen**
   - Öffne eine Eingabeaufforderung in diesem Verzeichnis.
   - Führe `installer\build_exe.bat` aus.  Das Skript installiert
     PyInstaller (falls noch nicht vorhanden) und erstellt im Ordner
     `dist` die Datei `ByblosCRM.exe`.  Die gesamte Anwendung wird
     dabei in eine einzige Datei gebündelt【996800693482621†L294-L313】.
2. **Windows‑Installer (Setup.exe)**
   - Installiere den Inno Setup Compiler (kostenlos erhältlich).
   - Starte den Script Wizard, wähle „Neues Skript aus Vorlage“ und
     importiere die Datei `installer\inno_setup.iss`【352968430935897†L37-L56】.
   - Passe gegebenenfalls Pfade (z. B. Version, Icon) an.
   - Klicke auf „Compile“, um ein `ByblosCRMSetup.exe` zu erstellen.
3. **MSIX‑Paket**
   - Folge der Anleitung in `msix/README_MSIX.md`, um ein `.msix`
     zu bauen und zu signieren.

## Android‑App

Die Android‑App besteht aus einer einfachen WebView, die deine
CRM‑URL lädt【616907568633741†L809-L896】.  Folgende Schritte sind nötig:

1. Installiere Android Studio.
2. Lege ein neues „Empty Activity“‑Projekt an.
3. Ersetze die in Android Studio generierten Dateien mit den
   Vorlagen aus `android/app/src/main` und passe Paketnamen sowie
   die URL (`loadUrl`) an【616907568633741†L809-L896】.
4. Füge im Manifest die Internet‑Berechtigung ein【616907568633741†L889-L896】.
5. Baue und signiere die APK (siehe `android/README_ANDROID.md`).

## Hinweise

- Diese Distribution dient als Grundlage.  Sie enthält keine
  Code‑Signierung oder Key‑Stores; diese müssen separat
  erworben/erzeugt werden.
- Die AI‑Funktionalität basiert auf scikit‑learn.  Sorge dafür,
  dass `scikit-learn`, `pdfplumber` und alle weiteren Abhängigkeiten
  installiert sind (siehe `byblos_crm_app/requirements.txt`).
- Der PDF‑Import nutzt `pdfplumber` zur Textextraktion.  Für
  besonders komplexe Dokumente solltest du eine OCR‑Engine (z. B.
  Tesseract) integrieren.
- Für Datenschutz und Compliance prüfe die Verarbeitung von
  personenbezogenen Daten (DSGVO).

Viel Erfolg beim Bauen und Verteilen deiner Byblos‑CRM‑Applikation!