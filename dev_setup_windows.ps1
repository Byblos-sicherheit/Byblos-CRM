$ErrorActionPreference = "Stop"
Write-Host "Setting up Byblos CRM dev environment..."
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r byblos_crm_app\requirements.txt
python tests\test_imports.py
Write-Host "Done. Start with: streamlit run byblos_crm_app/app.py"
