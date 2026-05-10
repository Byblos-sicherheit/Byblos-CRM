@echo off
setlocal
cd /d %~dp0\..
python -m streamlit run byblos_crm_app\app.py
