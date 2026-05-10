@echo off
setlocal EnableDelayedExpansion
:: =============================================================
::  build_exe.bat - Byblos CRM Windows-Build
::  Dieses Skript IMMER vom installer\ Ordner aus starten,
::  ODER per Doppelklick direkt ausfuehren.
::  Es ermittelt selbst den Projektstamm.
:: =============================================================

:: Projektverzeichnis = ein Ordner ueber diesem Skript
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

:: Zu absolutem Pfad aufloesen
pushd "%PROJECT_DIR%"
set "PROJECT_DIR=%CD%"
popd

echo.
echo =====================================================
echo   Byblos CRM - Windows Build v2.0
echo   Projektverzeichnis: %PROJECT_DIR%
echo =====================================================
echo.

:: --- Python pruefen ---
where python >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden.
    echo Bitte Python 3.10+ von https://python.org installieren.
    echo Wichtig: "Add Python to PATH" beim Install anhaaken!
    pause & exit /b 1
)
python --version
echo.

:: --- Ins Projektverzeichnis wechseln ---
cd /d "%PROJECT_DIR%"
echo [INFO] Arbeitsverzeichnis: %CD%
echo.

:: --- requirements.txt pruefen ---
if not exist "byblos_crm_app\requirements.txt" (
    echo [FEHLER] byblos_crm_app\requirements.txt nicht gefunden.
    echo Bitte sicherstellen dass du das komplette Paket entpackt hast.
    pause & exit /b 1
)

:: --- Virtuelle Umgebung ---
if not exist "venv\" (
    echo [INFO] Erstelle virtuelle Umgebung...
    python -m venv venv
    if errorlevel 1 (
        echo [FEHLER] Konnte venv nicht erstellen.
        pause & exit /b 1
    )
)

echo [INFO] Aktiviere venv...
call venv\Scripts\activate.bat

:: --- pip upgraden (separat, um den "To modify pip"-Fehler zu umgehen) ---
echo [INFO] Aktualisiere pip...
python -m pip install --upgrade pip --quiet 2>nul
echo [OK] pip aktuell.

:: --- PyInstaller installieren ---
echo [INFO] Installiere PyInstaller...
python -m pip install --upgrade pyinstaller --quiet
if errorlevel 1 (
    echo [FEHLER] PyInstaller konnte nicht installiert werden.
    pause & exit /b 1
)
echo [OK] PyInstaller installiert.

:: --- App-Abhaengigkeiten installieren ---
echo [INFO] Installiere App-Abhaengigkeiten aus requirements.txt...
python -m pip install -r byblos_crm_app\requirements.txt --quiet
if errorlevel 1 (
    echo [WARNUNG] Einige Pakete konnten nicht installiert werden.
    echo Moeglicherweise fehlt Microsoft C++ Build Tools fuer pytesseract.
    echo Weiter mit verfuegbaren Paketen...
)
echo [OK] Abhaengigkeiten installiert.
echo.

:: --- Alte Builds bereinigen ---
if exist "dist\ByblosCRM\" (
    echo [INFO] Loesche alten Build...
    rmdir /s /q "dist\ByblosCRM" 2>nul
)
if exist "build\" (
    rmdir /s /q "build" 2>nul
)

:: --- Assets sicherstellen ---
if not exist "byblos_crm_app\assets\" (
    mkdir "byblos_crm_app\assets"
)

:: --- Spec-Datei direkt hier im Skript erzeugen (kein Pfad-Problem) ---
echo [INFO] Erstelle PyInstaller-Spec...
(
echo # -*- mode: python ; coding: utf-8 -*-
echo # ByblosCRM.spec - automatisch generiert von build_exe.bat
echo block_cipher = None
echo a = Analysis^(
echo     ['byblos_crm_app\\launcher.py'],
echo     pathex=['byblos_crm_app'],
echo     binaries=[],
echo     datas=[
echo         ^('byblos_crm_app', 'byblos_crm_app'^),
echo     ],
echo     hiddenimports=[
echo         'streamlit', 'streamlit.runtime.scriptrunner.magic_funcs',
echo         'pandas', 'pandas._libs.tslibs.timedeltas',
echo         'pandas._libs.tslibs.np_datetime', 'pandas._libs.tslibs.nattype',
echo         'pandas._libs.tslibs.offsets', 'pandas._libs.skiplist',
echo         'pandas._libs.hashtable', 'pandas._libs.index',
echo         'reportlab', 'openpyxl', 'sklearn',
echo         'sklearn.linear_model', 'sklearn.feature_extraction.text',
echo         'pdfplumber', 'PIL', 'PIL.Image', 'click',
echo         'tornado', 'tornado.websocket', 'altair', 'pyarrow',
echo         'packaging', 'validators', 'tzlocal', 'cachetools',
echo         'importlib_metadata', 'sqlite3',
echo     ],
echo     hookspath=[],
echo     runtime_hooks=[],
echo     excludes=['matplotlib', 'scipy', 'jupyter', 'IPython'],
echo     cipher=block_cipher,
echo ^)
echo pyz = PYZ^(a.pure, a.zipped_data, cipher=block_cipher^)
echo exe = EXE^(
echo     pyz, a.scripts, [],
echo     exclude_binaries=True,
echo     name='ByblosCRM',
echo     debug=False,
echo     strip=False,
echo     upx=True,
echo     console=False,
echo     icon=None,
echo ^)
echo coll = COLLECT^(
echo     exe, a.binaries, a.zipfiles, a.datas,
echo     strip=False,
echo     upx=True,
echo     name='ByblosCRM',
echo ^)
) > ByblosCRM_build.spec

echo [OK] Spec-Datei erstellt.
echo.

:: --- launcher.py pruefen / erstellen ---
if not exist "byblos_crm_app\launcher.py" (
    echo [INFO] Erstelle launcher.py...
    (
    echo import os, sys, threading, time, webbrowser, subprocess
    echo from pathlib import Path
    echo def get_base^(^):
    echo     if getattr^(sys, 'frozen', False^):
    echo         return Path^(sys._MEIPASS^)
    echo     return Path^(__file__^).resolve^(^).parent
    echo def open_browser^(port, delay=3.0^):
    echo     time.sleep^(delay^)
    echo     webbrowser.open^(f'http://localhost:{port}'^)
    echo def main^(^):
    echo     base = get_base^(^)
    echo     app_dir = base / 'byblos_crm_app'
    echo     app_py = app_dir / 'app.py'
    echo     port = 8501
    echo     threading.Thread^(target=open_browser, args=^(port,^), daemon=True^).start^(^)
    echo     env = os.environ.copy^(^)
    echo     env['PYTHONPATH'] = str^(app_dir^)
    echo     cmd = [sys.executable, '-m', 'streamlit', 'run', str^(app_py^),
    echo            '--server.port', str^(port^),
    echo            '--server.headless', 'true',
    echo            '--server.enableCORS', 'false',
    echo            '--browser.gatherUsageStats', 'false']
    echo     proc = subprocess.run^(cmd, env=env, cwd=str^(app_dir^)^)
    echo     sys.exit^(proc.returncode^)
    echo if __name__ == '__main__':
    echo     main^(^)
    ) > byblos_crm_app\launcher.py
    echo [OK] launcher.py erstellt.
)

:: --- PyInstaller ausfuehren ---
echo [INFO] Starte PyInstaller...
echo.
python -m PyInstaller ByblosCRM_build.spec --noconfirm --clean --distpath dist --workpath build

if errorlevel 1 (
    echo.
    echo [FEHLER] PyInstaller ist fehlgeschlagen.
    echo Bitte obige Fehlermeldung pruefen.
    echo.
    echo Haeufige Ursachen:
    echo   - Fehlende DLL/Bibliothek: pip install [paket] ausfuehren
    echo   - Antivirenprogramm blockiert: Ausnahme fuer diesen Ordner setzen
    echo   - Pfad mit Sonderzeichen: Projekt in C:\ByblosCRM kopieren
    pause & exit /b 1
)

:: Aufraumen
del ByblosCRM_build.spec 2>nul

echo.
echo =====================================================
echo   BUILD ERFOLGREICH!
echo =====================================================
echo.
echo   EXE-Ordner: %PROJECT_DIR%\dist\ByblosCRM\
echo   Starten:    dist\ByblosCRM\ByblosCRM.exe
echo.

:: --- Inno Setup (optional) ---
where iscc >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Inno Setup gefunden - erstelle Installer...
    if exist "installer\inno_setup.iss" (
        iscc installer\inno_setup.iss
        if not errorlevel 1 (
            echo [OK] Setup-Installer: Output\ByblosCRMSetup.exe
        )
    )
) else (
    echo [INFO] Tipp: Inno Setup installieren fuer einen professionellen Setup-Installer.
    echo        https://jrsoftware.org/isinfo.php
)

echo.
echo Naechste Schritte:
echo   1. Testen:    dist\ByblosCRM\ByblosCRM.exe doppelklicken
echo   2. MSIX:      PowerShell als Admin: .\msix\build_msix.ps1
echo   3. Android:   android\build_apk.bat
echo.
pause
