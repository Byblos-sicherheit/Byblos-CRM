@echo off
title Byblos CRM v2
color 0A

set "APP_DIR=%~dp0app"
set "PORT=8501"

:: Python finden
set "PYTHON="
python --version >nul 2>&1 && set "PYTHON=python"
if "%PYTHON%"=="" (py --version >nul 2>&1 && set "PYTHON=py")
if "%PYTHON%"=="" (
    echo Python nicht gefunden! Bitte python.org/downloads
    pause
    exit /b 1
)

:: Streamlit check
%PYTHON% -m streamlit --version >nul 2>&1
if errorlevel 1 (
    echo Installiere Streamlit...
    %PYTHON% -m pip install streamlit pandas reportlab qrcode Pillow scikit-learn cryptography --quiet
)

:: Konfiguration
if not exist "%APP_DIR%\.streamlit" mkdir "%APP_DIR%\.streamlit"
(
echo [server]
echo port = %PORT%
echo headless = true
echo address = "localhost"
echo [browser]
echo gatherUsageStats = false
echo [theme]
echo primaryColor = "#c0392b"
echo backgroundColor = "#0e1117"
echo secondaryBackgroundColor = "#1a1f2e"
echo textColor = "#e8eaf0"
) > "%APP_DIR%\.streamlit\config.toml"

echo.
echo  ==========================================
echo    Byblos CRM v2 - wird gestartet
echo    http://localhost:%PORT%
echo    admin / admin123
echo  ==========================================
echo.

start "" /B cmd /C "timeout /t 4 /nobreak >nul && start http://localhost:%PORT%"
cd /d "%APP_DIR%"
%PYTHON% -m streamlit run app.py --server.port=%PORT% --server.address=localhost --server.headless=true --browser.gatherUsageStats=false
