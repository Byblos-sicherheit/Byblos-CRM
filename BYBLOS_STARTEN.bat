@echo off
:: ============================================================
:: BYBLOS CRM v2 - NETZWERK-STARTER
:: Lokal + LAN + Internet (Tunnel) in einem Skript
:: DOPPELKLICK zum Starten!
:: ============================================================
title Byblos CRM v2 - Netzwerk-Starter
color 0B
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1

:: Pfade bestimmen
set "APP_DIR=%~dp0app"
if not exist "!APP_DIR!\app.py" (
    set "APP_DIR=%APPDATA%\ByblosCRM\app"
)
if not exist "!APP_DIR!\app.py" (
    echo [FEHLER] app.py nicht gefunden. Bitte DIREKTINSTALL.bat zurerst ausfuehren.
    pause & exit /b 1
)

:: Python finden
set "PY="
python --version >nul 2>&1 && set "PY=python"
if "!PY!"=="" py --version >nul 2>&1 && set "PY=py"
if "!PY!"=="" (echo [FEHLER] Python nicht gefunden! & pause & exit /b 1)

:: Lokale IP ermitteln
for /f "tokens=2 delims=:" %%a in ('!PY! -c "import socket; s=socket.socket(); s.connect((\"8.8.8.8\",80)); print(\"IP:\"+s.getsockname()[0]); s.close()" 2^>nul') do (
    set "LOCAL_IP=%%a"
    set "LOCAL_IP=!LOCAL_IP: =!"
)
if "!LOCAL_IP!"=="" set "LOCAL_IP=127.0.0.1"

set "PORT=8501"

cls
echo.
echo  =======================================================
echo    BYBLOS CRM v2 - NETZWERK-EINSTELLUNGEN
echo  =======================================================
echo.
echo    PC-Name   : %COMPUTERNAME%
echo    Lokale IP : !LOCAL_IP!
echo    Port      : !PORT!
echo.
echo  ----- Modus waehlen -----
echo.
echo  [1] Nur auf diesem PC (localhost)
echo      Sicher - nur lokal erreichbar
echo.
echo  [2] Im Heimnetz / Buero-WLAN
echo      Handy + andere Geraete im gleichen WLAN
echo      URL: http://!LOCAL_IP!:!PORT!
echo.
echo  [3] Von ueberall (Cloudflare Tunnel - kostenlos)
echo      Handy von ueberall, anderes WLAN, Mobilfunk
echo      Erfordert: cloudflared.exe im Programmordner
echo.
echo  [4] Von ueberall (ngrok Tunnel)
echo      Alternative zu Cloudflare
echo.
echo  =======================================================
echo.
set /p "MODE=Modus eingeben (1/2/3/4) [Standard: 1]: "
if "!MODE!"=="" set "MODE=1"

:: Konfiguration schreiben
if not exist "!APP_DIR!\.streamlit" mkdir "!APP_DIR!\.streamlit"

if "!MODE!"=="1" (
    set "BIND=localhost"
    set "ACCESS_MSG=Nur auf diesem PC: http://localhost:!PORT!"
)
if "!MODE!"=="2" (
    set "BIND=0.0.0.0"
    set "ACCESS_MSG=Im Heimnetz: http://!LOCAL_IP!:!PORT!"
    call :FIREWALL_RULE
)
if "!MODE!"=="3" (
    set "BIND=localhost"
    set "ACCESS_MSG=Cloudflare Tunnel wird gestartet..."
)
if "!MODE!"=="4" (
    set "BIND=localhost"
    set "ACCESS_MSG=ngrok Tunnel wird gestartet..."
)

:: Streamlit-Konfiguration
(
echo [server]
echo port = !PORT!
echo headless = true
echo address = "!BIND!"
echo maxUploadSize = 200
echo.
echo [browser]
echo gatherUsageStats = false
echo.
echo [theme]
echo primaryColor = "#c0392b"
echo backgroundColor = "#0e1117"
echo secondaryBackgroundColor = "#1a1f2e"
echo textColor = "#e8eaf0"
echo font = "sans serif"
) > "!APP_DIR!\.streamlit\config.toml"

cls
echo.
echo  =======================================================
echo    BYBLOS CRM v2 STARTET...
echo  =======================================================
echo.
echo    Modus  : Modus !MODE!
echo    Zugang : !ACCESS_MSG!
echo    Login  : admin / admin123
echo.
echo    Zum Beenden: Dieses Fenster schliessen
echo  =======================================================
echo.

:: Browser-Start (nach 4 Sekunden)
start /B "" cmd /C "timeout /t 4 /nobreak >nul && start http://localhost:!PORT!"

:: Tunnel-Start (Modus 3 oder 4)
if "!MODE!"=="3" call :START_CLOUDFLARE
if "!MODE!"=="4" call :START_NGROK

:: App starten
cd /d "!APP_DIR!"
!PY! -m streamlit run app.py ^
    --server.port=!PORT! ^
    --server.address=!BIND! ^
    --server.headless=true ^
    --browser.gatherUsageStats=false

goto :END

:: ── Firewall-Regel hinzufuegen ────────────────────────────
:FIREWALL_RULE
echo  [INFO] Firewall-Regel fuer Port !PORT! wird geprueft...
netsh advfirewall firewall show rule name="ByblosCRM-!PORT!" >nul 2>&1
if !errorlevel! neq 0 (
    :: Regel existiert noch nicht - erstellen (braucht Admin!)
    powershell -Command "
        try {
            New-NetFirewallRule -DisplayName 'ByblosCRM-!PORT!' -Direction Inbound -Action Allow -Protocol TCP -LocalPort !PORT! -ErrorAction Stop
            Write-Host '  Firewall-Regel erstellt'
        } catch {
            Write-Host '  Firewall: Administrator-Rechte benoetigt'
            Write-Host '  Bitte als Admin ausfuehren oder manuell:'
            Write-Host '  netsh advfirewall firewall add rule name=ByblosCRM-!PORT! protocol=TCP dir=in localport=!PORT! action=allow'
        }
    " 2>nul
) else (
    echo  [OK] Firewall-Regel bereits vorhanden.
)
goto :EOF

:: ── Cloudflare Tunnel ─────────────────────────────────────
:START_CLOUDFLARE
set "CF_EXE="
set "CF_SEARCH=%~dp0cloudflared.exe %~dp0app\cloudflared.exe %APPDATA%\ByblosCRM\cloudflared.exe %LOCALAPPDATA%\ByblosCRM\cloudflared.exe"
for %%P in (!CF_SEARCH!) do (
    if exist "%%P" set "CF_EXE=%%P"
)
if "!CF_EXE!"=="" (
    echo  [CLOUDFLARE] cloudflared.exe nicht gefunden!
    echo  Bitte herunterladen von: https://developers.cloudflare.com/cloudflared/get-started/
    echo  Dann in den Ordner legen: %~dp0
    echo.
    echo  Starte stattdessen nur lokal...
    goto :EOF
)

echo  [CLOUDFLARE] Starte Tunnel (kann 30 Sek dauern)...
start /B "" cmd /C "!CF_EXE! tunnel --url http://localhost:!PORT! > %TEMP%\cloudflare_url.txt 2>&1"
timeout /t 8 /nobreak >nul

:: URL aus Log lesen
for /f "tokens=*" %%L in ('type "%TEMP%\cloudflare_url.txt" 2^>nul ^| findstr "trycloudflare"') do (
    echo  [CLOUDFLARE] %%L
)
echo.
echo  [CLOUDFLARE] Tunnel laeuft im Hintergrund.
echo  URL ist sichtbar in: Byblos CRM -> Netzwerk -> Remote-Zugang
goto :EOF

:: ── ngrok Tunnel ─────────────────────────────────────────
:START_NGROK
set "NGROK_EXE="
for %%P in (%~dp0ngrok.exe %~dp0app\ngrok.exe %APPDATA%\ByblosCRM\ngrok.exe) do (
    if exist "%%P" set "NGROK_EXE=%%P"
)
if "!NGROK_EXE!"=="" (
    echo  [NGROK] ngrok.exe nicht gefunden!
    echo  Bitte herunterladen von: https://ngrok.com/download
    echo  Dann in den Ordner legen: %~dp0
    echo.
    goto :EOF
)
echo  [NGROK] Starte Tunnel...
start /B "" "!NGROK_EXE!" http !PORT!
timeout /t 4 /nobreak >nul
echo  [NGROK] Tunnel laeuft. URL in Byblos CRM -> Netzwerk -> Remote-Zugang
goto :EOF

:END
echo.
echo  Byblos CRM beendet. Druecken Sie Enter.
pause >nul
