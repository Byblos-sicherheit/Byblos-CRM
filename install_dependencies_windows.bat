@echo off
setlocal

echo === Byblos CRM Dependencies installieren ===
python -m pip install --upgrade pip
python -m pip install -r byblos_crm_app\requirements.txt

echo.
echo Fertig. Starte danach:
echo streamlit run byblos_crm_app\app.py
