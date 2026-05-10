# -*- mode: python ; coding: utf-8 -*-
# ByblosCRM.spec – PyInstaller-Konfigurationsdatei
# Erstellt eine standalone EXE für Windows (64-bit)
#
# Verwendung:
#   pyinstaller ByblosCRM.spec
#
# Das Ergebnis liegt in: dist\ByblosCRM\ByblosCRM.exe  (OneDir-Modus)
# Für MSIX wird der OneDir-Modus empfohlen (schnellerer Start).

import sys
from pathlib import Path

block_cipher = None
APP_NAME = "ByblosCRM"
APP_DIR = Path("byblos_crm_app")

# Alle Datendateien der App einschließen
datas = [
    (str(APP_DIR / "*.py"),         "byblos_crm_app"),
    (str(APP_DIR / ".streamlit"),   "byblos_crm_app/.streamlit"),
    (str(APP_DIR / "assets"),       "byblos_crm_app/assets"),
    (str(APP_DIR / "templates"),    "byblos_crm_app/templates"),
    (str(APP_DIR / "training_data.json"), "byblos_crm_app"),
    (str(APP_DIR / "requirements.txt"),   "byblos_crm_app"),
    # Streamlit static assets
    ("venv/Lib/site-packages/streamlit", "streamlit"),
    ("venv/Lib/site-packages/altair",    "altair"),
]

# Hidden imports für Streamlit und Abhängigkeiten
hiddenimports = [
    "streamlit",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "streamlit.components.v1",
    "pandas",
    "pandas._libs.tslibs.timedeltas",
    "pandas._libs.tslibs.np_datetime",
    "pandas._libs.tslibs.nattype",
    "pandas._libs.tslibs.offsets",
    "pandas._libs.skiplist",
    "pandas._libs.hashtable",
    "pandas._libs.index",
    "reportlab",
    "reportlab.graphics.charts",
    "openpyxl",
    "sklearn",
    "sklearn.linear_model",
    "sklearn.feature_extraction.text",
    "pdfplumber",
    "PIL",
    "PIL.Image",
    "sqlalchemy",
    "altair",
    "pyarrow",
    "click",
    "tornado",
    "tornado.websocket",
    "watchdog",
    "gitpython",
    "pydeck",
    "tzlocal",
    "cachetools",
    "validators",
    "packaging",
    "importlib_metadata",
]

a = Analysis(
    [str(APP_DIR / "launcher.py")],
    pathex=[str(APP_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "jupyter", "IPython", "notebook"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # Kein Konsolenfenster (GUI-App)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="byblos_crm_app/assets/icon.ico",   # Icon-Datei (optional)
    version="version_info.txt",              # Windows-Versionsinfo (optional)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
