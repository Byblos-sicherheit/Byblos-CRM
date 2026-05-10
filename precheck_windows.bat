@echo off
setlocal EnableDelayedExpansion
:: ============================================================
::  precheck_windows.bat - Systemvoraussetzungen pruefen
::  Vor dem Build ausfuehren um Probleme zu erkennen
:: ============================================================
cd /d "%~dp0.."
echo.
echo =====================================================
echo   Byblos CRM - System-Vorpruefung
echo =====================================================
echo.
set ERRORS=0
set WARNINGS=0

:: 1. Python
echo [1/6] Pruefe Python...
where python >nul 2>&1
if errorlevel 1 (
    echo   [FEHLER] Python nicht gefunden!
    echo   Bitte installieren: https://python.org/downloads
    echo   WICHTIG: "Add Python to PATH" anhaaken!
    set /a ERRORS+=1
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
    echo   [OK] !PY_VER!
    echo !PY_VER! | findstr /r "3\.[0-9][0-9]" >nul || (
        echo   [WARNUNG] Python 3.10+ empfohlen
        set /a WARNINGS+=1
    )
)

:: 2. pip
echo [2/6] Pruefe pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo   [FEHLER] pip nicht gefunden!
    set /a ERRORS+=1
) else (
    for /f "tokens=*" %%v in ('python -m pip --version 2^>^&1') do echo   [OK] %%v
)

:: 3. Projektstruktur
echo [3/6] Pruefe Projektstruktur...
if not exist "byblos_crm_app\app.py" (
    echo   [FEHLER] byblos_crm_app\app.py nicht gefunden!
    echo   Bitte das komplette ZIP-Paket entpacken.
    set /a ERRORS+=1
) else (
    echo   [OK] app.py gefunden
)
if not exist "byblos_crm_app\requirements.txt" (
    echo   [FEHLER] requirements.txt nicht gefunden!
    set /a ERRORS+=1
) else (
    echo   [OK] requirements.txt gefunden
)

:: 4. Speicherplatz
echo [4/6] Pruefe Speicherplatz...
for /f "tokens=3" %%s in ('dir /-c "%CD%" ^| findstr /r "Bytes frei"') do set FREE_BYTES=%%s
if defined FREE_BYTES (
    echo   [OK] Freier Speicher vorhanden
) else (
    echo   [INFO] Speicherplatz konnte nicht geprueft werden - mind. 2 GB empfohlen
    set /a WARNINGS+=1
)

:: 5. Pfad auf Sonderzeichen pruefen
echo [5/6] Pruefe Pfad auf Sonderzeichen...
set "CURRENT=%CD%"
echo %CURRENT% | findstr /r "[&()!@#$%%^]" >nul
if not errorlevel 1 (
    echo   [WARNUNG] Pfad enthaelt Sonderzeichen: %CURRENT%
    echo   Dies kann PyInstaller zum Absturz bringen.
    echo   Empfehlung: Projekt nach C:\ByblosCRM\ kopieren
    set /a WARNINGS+=1
) else (
    echo   [OK] Pfad ohne Sonderzeichen
)

:: 6. Inno Setup (optional)
echo [6/6] Pruefe Inno Setup (optional)...
where iscc >nul 2>&1
if errorlevel 1 (
    echo   [INFO] Inno Setup nicht gefunden (optional fuer Setup-Installer)
    echo   Download: https://jrsoftware.org/isinfo.php
) else (
    echo   [OK] Inno Setup gefunden
)

echo.
echo =====================================================
if !ERRORS! GTR 0 (
    echo   ERGEBNIS: !ERRORS! Fehler gefunden - Build wird FEHLSCHLAGEN!
    echo   Bitte Fehler beheben, dann nochmal pruefen.
) else if !WARNINGS! GTR 0 (
    echo   ERGEBNIS: !WARNINGS! Warnung^(en^) - Build sollte funktionieren
    echo   Warnungen lesen und ggf. beheben.
) else (
    echo   ERGEBNIS: Alles OK - bereit fuer den Build!
    echo   Starten: BUILD_WINDOWS.bat doppelklicken
)
echo =====================================================
echo.
pause
