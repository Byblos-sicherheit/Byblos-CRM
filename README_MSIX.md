# MSIX‑Packaging für Byblos CRM

Dieses Verzeichnis enthält eine kurze Anleitung, wie du aus der mit
PyInstaller erstellten EXE eine **.msix**‑Installationsdatei erzeugen
kannst.  Der Prozess kann nur auf einem Windows‑Rechner mit dem
Microsoft **MSIX Packaging Tool** durchgeführt werden.

## Voraussetzungen

* Die Datei `ByblosCRM.exe` muss bereits existieren.  Erstelle sie
  mit dem mitgelieferten Skript `installer\build_exe.bat`.
* Das **MSIX Packaging Tool** ist im Microsoft Store verfügbar.  Lade
  es von dort herunter und installiere es.
* Ein Code‑Signing‑Zertifikat (PFX) ist erforderlich, um das MSIX
  anschließend zu signieren.  Ohne Signatur kann die MSIX nicht
  installiert werden.

## Schritt‑für‑Schritt

1. Öffne das *MSIX Packaging Tool* und wähle "Anwendungspaket" →
   "Neues Paket aus vorhandenem Installer erstellen".
2. Gib dein Paket‑Name (z. B. `ByblosCRM`) und deine Publisher
   Informationen ein.  Der Publisher muss zum Signaturzertifikat
   passen.
3. Als Installationsprogramm wählst du die erstellte `ByblosCRM.exe`.
   Unter **Arguments** bleibt das Feld leer.
4. Als Installationsverzeichnis gibst du etwas wie
   `%ProgramFiles%\Byblos CRM` an.
5. Lass die restlichen Optionen unverändert und starte die
   Paketerstellung.  Nach Abschluss erhältst du eine
   `ByblosCRM.msix`.
6. Signiere die MSIX mit deinem Code‑Signing‑Zertifikat, zum Beispiel
   mittels `signtool`:

   ```
   signtool sign /fd SHA256 /a /f dein-zertifikat.pfx /p zerti-passwort ByblosCRM.msix
   ```

7. Teste die Installation, indem du die signierte `.msix` per Doppelklick
   öffnest.  Windows sollte nach Bestätigung die App im
   App‑Installer installieren.

## Hinweise

* Ohne Zertifikat können MSIX‑Pakete nicht installiert werden.
* MSIX‑Pakete verfügen über strikte Berechtigungen; wenn deine App
  zusätzlich (z. B. Write‑Zugriffe außerhalb des AppData) benötigt,
  müssen diese im Package manifest definiert werden.

Weitere Informationen findest du in der offiziellen Microsoft‑Dokumentation.