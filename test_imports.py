"""Minimal smoke test for the Byblos CRM package."""
import importlib

REQUIRED = [
    'streamlit', 'pandas', 'reportlab', 'openpyxl', 'sklearn',
    'pdfplumber', 'pytesseract', 'pdf2image', 'PIL'
]

for name in REQUIRED:
    importlib.import_module(name)
    print('[OK]', name)

print('All import checks passed.')
