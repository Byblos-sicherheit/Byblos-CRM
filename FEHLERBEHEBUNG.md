# Byblos CRM v2 – Fehlerbehebung

## Windows EXE / BUILD_WINDOWS.bat

### ❌ „Python wurde nicht gefunden"
**Ursache:** Python ist nicht im Windows PATH.  
**Lösung:**  
1. Python von https://python.org/downloads herunterladen (3.10, 3.11 oder 3.12 empfohlen)  
2. Bei der Installation: **☑ „Add Python to PATH"** aktivieren  
3. Danach CMD neu öffnen und `python --version` testen

### ❌ „To modify pip, please run the following command: python.exe -m pip install …"
**Ursache:** Alte pip-Version versucht sich selbst zu aktualisieren, was in manchen Umgebungen eingeschränkt ist.  
**Lösung:** Das Skript `BUILD_WINDOWS.bat` behebt dies automatisch, indem pip innerhalb der virtuellen Umgebung (venv) aktualisiert wird – nicht global. Einfach `BUILD_WINDOWS.bat` nochmals starten.

### ❌ „Could not open requirements file: … requirements.txt"
**Ursache:** Skript läuft im falschen Verzeichnis.  
**Lösung:** **Immer `BUILD_WINDOWS.bat` per Doppelklick starten** – nie per CMD aus einem anderen Ordner. Das Skript setzt das Verzeichnis automatisch korrekt (`cd /d "%~dp0"`).

### ❌ „Spec file 'installer\ByblosCRM.spec' not found"
**Ursache:** Altes Build-Skript aus dem `installer\`-Unterordner wurde aufgerufen.  
**Lösung:** Das neue `BUILD_WINDOWS.bat` liegt im **Root-Ordner** (`byblos_crm_v2\`) – dieses verwenden. Das Skript benutzt keine .spec-Datei mehr, sondern übergibt alle Parameter direkt.

### ❌ Antivirus blockiert PyInstaller oder die EXE
**Ursache:** Viele Antivirus-Programme erkennen PyInstaller-EXEs fälschlicherweise als Bedrohung.  
**Lösung:**  
1. Ordner `byblos_crm_v2\` als Ausnahme im Antivirus hinzufügen  
2. `dist\ByblosCRM\` als Ausnahme hinzufügen  
3. Build erneut starten

### ❌ „UPX is not available" (Warnung, kein Fehler)
Kein Problem – UPX ist optional und wird nur für kleinere EXE-Dateien benötigt. Der Build läuft trotzdem durch.

### ❌ ByblosCRM.exe startet, aber kein Browser öffnet sich
**Lösung:**  
1. Kurz warten (Streamlit braucht 3–8 Sekunden zum Starten)  
2. Browser manuell öffnen: http://localhost:8501  
3. Falls Port belegt: http://localhost:8502 versuchen (Launcher wählt automatisch freien Port)

### ❌ EXE startet, Browser öffnet sich, aber leere Seite / Fehler
**Lösung:**  
1. `dist\ByblosCRM\ByblosCRM.exe` direkt (nicht per Verknüpfung) starten  
2. Sicherstellen, dass `dist\ByblosCRM\byblos_crm_app\` vorhanden ist  
3. Ggf. den gesamten `dist\ByblosCRM\`-Ordner in einen Pfad **ohne Sonderzeichen und Leerzeichen** kopieren

---

## MSIX (build_msix.ps1)

### ❌ „MakeAppx.exe nicht gefunden"
**Lösung:** Windows SDK installieren:  
https://developer.microsoft.com/windows/downloads/windows-sdk/  
Nur „Windows SDK for Desktop C++ Apps" auswählen reicht.

### ❌ „Add-AppxPackage: Deployment failed"
**Ursache:** Unsigned MSIX kann nur mit aktiviertem Developer Mode installiert werden.  
**Lösung:**  
1. Windows Einstellungen → System → Für Entwickler → **Entwicklermodus: AN**  
2. PowerShell als Admin: `Add-AppxPackage -Path "...\ByblosCRM.msix" -AllowUnsigned`

### ❌ Publisher-Mismatch beim Signieren
**Ursache:** Zertifikat-Subject stimmt nicht mit `AppxManifest.xml` überein.  
**Lösung:** In `msix\AppxManifest.xml` den Wert `Publisher="CN=..."` auf den Subject-Name des Zertifikats anpassen.

---

## Android APK

### ❌ „JAVA_HOME not set" / „java nicht gefunden"
**Lösung:** Android Studio installieren – es enthält JDK 17. Danach:  
Windows: `set JAVA_HOME=C:\Program Files\Android\Android Studio\jbr`  
Mac/Linux: `export JAVA_HOME=/Applications/Android\ Studio.app/Contents/jbr/Contents/Home`

### ❌ „SDK location not found"
**Lösung:**  
1. `android\local.properties.template` kopieren als `android\local.properties`  
2. Pfad zum Android SDK anpassen (s. Datei)

### ❌ APK lässt sich nicht installieren
**Lösung:**  
1. Gerät: Einstellungen → Sicherheit → **Unbekannte Apps installieren: erlaubt**  
2. APK per USB oder Dateimanager auf Gerät übertragen  
3. Per ADB: `adb install app-debug.apk`

### ❌ App öffnet weiße Seite / „Verbindung abgelehnt"
**Ursache:** CRM-URL in `MainActivity.java` ist falsch oder Server läuft nicht.  
**Lösung:**  
1. In `android\app\src\main\java\de\byblos_sicherheit\crm\MainActivity.java` Zeile `CRM_URL` anpassen:  
   - Lokales Netz: `http://192.168.1.XXX:8501` (IP des Servers, nicht 192.168.1.1!)  
   - Internet: `https://dein-crm-server.de`  
2. Sicherstellen, dass der CRM-Server läuft und aus dem Netzwerk erreichbar ist  
3. APK neu bauen und installieren

---

## App / Streamlit (Direktstart)

### ❌ „ModuleNotFoundError: No module named 'streamlit'"
```bash
pip install streamlit pandas reportlab openpyxl scikit-learn pdfplumber Pillow
```

### ❌ Streamlit Seite lädt nicht richtig / CSS fehlt
Browser-Cache leeren: `Strg + Shift + R`

### ❌ Datenbank-Fehler beim Start
Die SQLite-Datenbank wird automatisch beim ersten Start erstellt. Falls sie korrupt ist:  
`byblos_crm_app\byblos_crm.db` löschen → App neu starten → leere DB wird neu erstellt.

---

## Allgemein

### Direktstart ohne Build (zum Testen)
```bash
cd byblos_crm_app
pip install streamlit pandas reportlab openpyxl scikit-learn pdfplumber Pillow altair pyarrow
streamlit run app.py
```

### Logs anzeigen
Beim Direktstart erscheinen Logs direkt im Terminal.  
Bei der EXE: Temporärer Ordner → `%TEMP%\ByblosCRM_*.log` (falls vorhanden)

### Support
Bei weiteren Fragen: info@byblos-sicherheit.de
