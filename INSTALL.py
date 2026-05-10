"""
Byblos CRM v2 - Python-Installer (garantiert ohne Admin-Fehler)
Kein Inno Setup, kein PyInstaller, kein C:\Users\Public
"""
import sys, os, shutil, subprocess, socket, webbrowser, threading, time
from pathlib import Path

def main():
    print("\n" + "="*55)
    print("  BYBLOS CRM v2 - INSTALLATION")
    print("="*55 + "\n")

    # Quell-Verzeichnis finden
    script_dir = Path(__file__).parent
    candidates = [
        script_dir / "byblos_crm_v2" / "byblos_crm_app",
        script_dir / "byblos_crm_app",
        script_dir,
    ]
    app_src = None
    for c in candidates:
        if (c / "app.py").exists():
            app_src = c
            break

    if not app_src:
        print("[FEHLER] app.py nicht gefunden!")
        print("Bitte ZIP vollstaendig entpacken und nochmal starten.")
        input("\nEnter drücken...")
        sys.exit(1)
    print(f"[OK] Quellordner: {app_src}")

    # Zielordner: APPDATA (kein Admin nötig!)
    dest = Path(os.environ.get("APPDATA", Path.home())) / "ByblosCRM" / "app"
    dest.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Zielordner: {dest}")

    # Dateien kopieren
    print("[1/4] Kopiere App-Dateien...")
    shutil.copytree(str(app_src), str(dest), dirs_exist_ok=True)
    for sub in ["generated/invoices","generated/payroll","generated/reports",
                "imports","assets","backups",".streamlit"]:
        (dest / sub).mkdir(parents=True, exist_ok=True)
    print("      Erledigt.")

    # Streamlit Konfiguration
    config = dest / ".streamlit" / "config.toml"
    config.write_text("""[server]
port = 8501
headless = true
address = "localhost"
maxUploadSize = 200

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#c0392b"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#1a1f2e"
textColor = "#e8eaf0"
font = "sans serif"
""")

    # Pakete installieren
    print("[2/4] Installiere Python-Pakete...")
    pkgs = ["streamlit","pandas","openpyxl","reportlab","qrcode[pil]",
            "Pillow","scikit-learn","cryptography","psutil"]
    for pkg in pkgs:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg,
             "--quiet", "--no-warn-script-location"],
            capture_output=True)
        status = "OK" if r.returncode == 0 else "WARNUNG"
        print(f"      [{status}] {pkg}")
    print("      Erledigt.")

    # Datenbank initialisieren
    print("[3/4] Datenbank initialisieren...")
    os.chdir(str(dest))
    sys.path.insert(0, str(dest))
    try:
        import app as crm_app
        crm_app.init_db()
        print("      Datenbank bereit.")
    except Exception as e:
        print(f"      (Wird beim ersten Start erstellt: {e})")

    # Starter-Skript erstellen (APPDATA - kein Public!)
    starter_dir = dest.parent
    starter_path = starter_dir / "Byblos_CRM_Starten.bat"
    starter_path.write_text(f"""@echo off
title Byblos CRM v2
color 0A
echo.
echo   Byblos CRM v2 startet...
echo   Browser: http://localhost:8501
echo   Login: admin / admin123
echo.
cd /d "{dest}"
start /B "" cmd /C "timeout /t 3 /nobreak >nul && start http://localhost:8501"
{sys.executable} -m streamlit run app.py --server.port=8501 --server.address=localhost --server.headless=true --browser.gatherUsageStats=false
echo.
echo Beendet. Enter druecken.
pause >nul
""", encoding="utf-8")
    print(f"[4/4] Starter erstellt: {starter_path}")

    # Desktop-Verknüpfung NUR im eigenen Desktop (kein Public!)
    desktop = Path.home() / "Desktop"
    shortcut_created = False

    if desktop.exists():
        # Methode 1: .bat direkt auf Desktop kopieren
        bat_on_desktop = desktop / "Byblos CRM.bat"
        try:
            shutil.copy2(str(starter_path), str(bat_on_desktop))
            shortcut_created = True
            print(f"      Desktop: {bat_on_desktop}")
        except Exception as e:
            print(f"      Desktop-Kopie: {e}")

        # Methode 2: .lnk via PowerShell (eigener Desktop!)
        if not shortcut_created:
            ps_cmd = f"""
$s = (New-Object -COM WScript.Shell).CreateShortcut('{desktop / "Byblos CRM.lnk"}')
$s.TargetPath = '{starter_path}'
$s.WorkingDirectory = '{dest}'
$s.Description = 'Byblos CRM v2'
$s.Save()
"""
            r = subprocess.run(["powershell", "-Command", ps_cmd],
                               capture_output=True, timeout=10)
            if r.returncode == 0:
                shortcut_created = True
                print(f"      Desktop-Verknüpfung: {desktop / 'Byblos CRM.lnk'}")

    print("\n" + "="*55)
    print("  INSTALLATION ERFOLGREICH!")
    print("="*55)
    print(f"\n  Starter: {starter_path}")
    if shortcut_created:
        print(f"  Desktop: Byblos CRM (Doppelklick)")
    print(f"\n  Browser: http://localhost:8501")
    print(f"  Login:   admin / admin123")
    print(f"\n  WICHTIG: Passwort nach erstem Login ändern!")
    print("="*55)

    antwort = input("\nJetzt starten? (J/N): ").strip().lower()
    if antwort == "j":
        subprocess.Popen(str(starter_path), shell=True)

if __name__ == "__main__":
    main()
