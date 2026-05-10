@echo off
REM Beispiel fuer Windows Code Signing. Werte anpassen.
REM Voraussetzung: Windows SDK signtool.exe und ein Code-Signing-Zertifikat.

set FILE_TO_SIGN=dist\ByblosCRM.exe
set PFX_PATH=dein-zertifikat.pfx
set PFX_PASSWORD=DEIN_PASSWORT

signtool sign /fd SHA256 /f "%PFX_PATH%" /p "%PFX_PASSWORD%" /tr http://timestamp.digicert.com /td SHA256 "%FILE_TO_SIGN%"
