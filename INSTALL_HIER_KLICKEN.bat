@echo off
:: ============================================================
:: BYBLOS CRM v2 - HIER DOPPELKLICKEN!
:: Kein Administrator noetig!
:: Kein Inno Setup!
:: Kein PyInstaller!
:: ============================================================
title Byblos CRM v2 - Installation
color 0B

echo.
echo  Byblos CRM v2 - Installation startet...
echo  Bitte warten...
echo.

:: Python finden
set "PY="
python --version >nul 2>&1 && set "PY=python"
if "%PY%"=="" py --version >nul 2>&1 && set "PY=py"

if "%PY%"=="" (
    echo.
    echo  [FEHLER] Python nicht gefunden!
    echo.
    echo  Bitte Python installieren:
    echo  https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    echo.
    echo  WICHTIG: "Add Python to PATH" anwaehlen!
    echo.
    :: Python automatisch herunterladen
    powershell -Command "
        Write-Host 'Lade Python 3.11 herunter...'
        $url = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
        $tmp = [IO.Path]::GetTempPath() + 'py_setup.exe'
        (New-Object Net.WebClient).DownloadFile($url, $tmp)
        Write-Host 'Starte Python-Installation...'
        Start-Process $tmp -Args '/quiet InstallAllUsers=0 PrependPath=1' -Wait
        Remove-Item $tmp
        Write-Host 'Python installiert! Bitte nochmal klicken.'
    " 2>nul
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('%PY% --version 2^>^&1') do echo  Python: %%v

:: Python-Installer starten
%PY% "%~dp0INSTALL.py"

pause
