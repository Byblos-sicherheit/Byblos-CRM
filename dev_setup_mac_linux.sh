#!/usr/bin/env bash
set -euo pipefail
echo "Setting up Byblos CRM dev environment..."
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r byblos_crm_app/requirements.txt
python tests/test_imports.py
echo "Done. Start with: streamlit run byblos_crm_app/app.py"
