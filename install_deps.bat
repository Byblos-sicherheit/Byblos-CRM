@echo off
set "PYTHON="
python --version >nul 2>&1 && set "PYTHON=python"
if "%PYTHON%"=="" (py --version >nul 2>&1 && set "PYTHON=py")
if "%PYTHON%"=="" exit /b 0

%PYTHON% -m pip install streamlit pandas openpyxl reportlab "qrcode[pil]" Pillow scikit-learn cryptography psutil --quiet --no-warn-script-location 2>nul
