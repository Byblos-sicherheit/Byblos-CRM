@echo off
setlocal
cd /d %~dp0\..
python tests\test_imports.py
python -m py_compile byblos_crm_app\app.py byblos_crm_app\ml_logic.py
if errorlevel 1 (
  echo Smoke test failed.
  exit /b 1
)
echo Smoke test passed.
