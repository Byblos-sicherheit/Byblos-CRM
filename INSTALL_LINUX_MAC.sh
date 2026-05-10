#!/bin/bash
# ============================================================
# Byblos CRM v2 - Auto-Installer fuer Linux & macOS
# Ausfuehren: chmod +x INSTALL_LINUX_MAC.sh && ./INSTALL_LINUX_MAC.sh
# ============================================================

set -e
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "\n${CYAN}${BOLD}======================================================"
echo "  BYBLOS CRM v2 - Auto-Installer fuer Linux/macOS"
echo -e "======================================================${NC}\n"

# Betriebssystem ermitteln
OS="linux"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
fi
echo -e "  Erkanntes System: ${OS}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.byblos_crm"
APP_DIR="$INSTALL_DIR/app"
DATA_DIR="$INSTALL_DIR/data"

# 1. Voraussetzungen pruefen
echo -e "\n${YELLOW}[1/7] System-Voraussetzungen pruefen...${NC}"

if ! command -v python3 &>/dev/null; then
    echo -e "  ${RED}Python3 nicht gefunden!${NC}"
    if [[ "$OS" == "mac" ]]; then
        echo "  Installiere via Homebrew: brew install python3"
        if command -v brew &>/dev/null; then
            brew install python3
        fi
    else
        echo "  Installiere Python3..."
        sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip -qq
    fi
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo -e "  ${GREEN}$PYTHON_VERSION ✓${NC}"

if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null; then
    echo "  pip installieren..."
    if [[ "$OS" == "mac" ]]; then
        python3 -m ensurepip --upgrade
    else
        sudo apt-get install -y python3-pip -qq
    fi
fi
echo -e "  ${GREEN}pip ✓${NC}"

# 2. Verzeichnisse erstellen
echo -e "\n${YELLOW}[2/7] Verzeichnisse anlegen...${NC}"
mkdir -p "$INSTALL_DIR" "$APP_DIR" "$DATA_DIR"
mkdir -p "$APP_DIR/generated/invoices"
mkdir -p "$APP_DIR/generated/payroll"
mkdir -p "$APP_DIR/generated/reports"
mkdir -p "$APP_DIR/imports"
mkdir -p "$APP_DIR/assets"
mkdir -p "$APP_DIR/backups"
echo -e "  ${GREEN}Verzeichnisse erstellt ✓${NC}"

# 3. App-Dateien kopieren
echo -e "\n${YELLOW}[3/7] App-Dateien installieren...${NC}"
if [[ -d "$SCRIPT_DIR/byblos_crm_app" ]]; then
    cp -r "$SCRIPT_DIR/byblos_crm_app/." "$APP_DIR/"
    echo -e "  ${GREEN}Dateien kopiert ✓${NC}"
else
    echo -e "  ${RED}Fehler: byblos_crm_app/ nicht gefunden in $SCRIPT_DIR${NC}"
    echo "  Bitte sicherstellen, dass das ZIP vollstaendig entpackt ist."
    exit 1
fi

# 4. Streamlit-Konfiguration
echo -e "\n${YELLOW}[4/7] Konfiguration anlegen...${NC}"
mkdir -p "$APP_DIR/.streamlit"
cat > "$APP_DIR/.streamlit/config.toml" << 'TOML'
[server]
port = 8501
headless = true
address = "localhost"
maxUploadSize = 200

[browser]
gatherUsageStats = false
serverAddress = "localhost"
serverPort = 8501

[theme]
primaryColor = "#c0392b"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#1a1f2e"
textColor = "#e8eaf0"
font = "sans serif"
TOML
echo -e "  ${GREEN}Konfiguration erstellt ✓${NC}"

# 5. Python-Abhaengigkeiten installieren
echo -e "\n${YELLOW}[5/7] Python-Pakete installieren (kann 2-3 Minuten dauern)...${NC}"

# pip Optionen fuer verschiedene Systeme
PIP_OPTS="--quiet"
if python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
    PIP_OPTS="$PIP_OPTS --break-system-packages" 2>/dev/null || true
fi

PACKAGES="streamlit>=1.30 pandas openpyxl reportlab qrcode pillow scikit-learn cryptography fastapi uvicorn"
PACKAGES="$PACKAGES python-multipart requests"

if [[ -f "$APP_DIR/requirements.txt" ]]; then
    python3 -m pip install -r "$APP_DIR/requirements.txt" $PIP_OPTS || \
    python3 -m pip install -r "$APP_DIR/requirements.txt" || \
    pip3 install -r "$APP_DIR/requirements.txt"
else
    python3 -m pip install $PACKAGES $PIP_OPTS || \
    python3 -m pip install $PACKAGES || \
    pip3 install $PACKAGES
fi
echo -e "  ${GREEN}Pakete installiert ✓${NC}"

# 6. Datenbank initialisieren
echo -e "\n${YELLOW}[6/7] Datenbank initialisieren...${NC}"
cd "$APP_DIR"
python3 - << 'PYEOF'
import sys
sys.path.insert(0, '.')
try:
    import app as a
    a.init_db()
    print("  Datenbank erfolgreich initialisiert")
    import sqlite3
    conn = sqlite3.connect(str(a.DB_PATH))
    t = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    u = conn.execute("SELECT username, role FROM users").fetchall()
    conn.close()
    print(f"  {t} Tabellen, Benutzer: {u}")
except Exception as e:
    print(f"  Warnung (nicht kritisch): {e}")
PYEOF
echo -e "  ${GREEN}Datenbank bereit ✓${NC}"

# 7. Start-Skripte erstellen
echo -e "\n${YELLOW}[7/7] Start-Skripte und Verknuepfungen erstellen...${NC}"

# Start-Skript
cat > "$INSTALL_DIR/start_byblos.sh" << STARTER
#!/bin/bash
# Byblos CRM v2 Starter
cd "$APP_DIR"

# Browser nach 3 Sekunden oeffnen
(sleep 3 && (
    if command -v xdg-open &>/dev/null; then xdg-open http://localhost:8501
    elif command -v open &>/dev/null; then open http://localhost:8501
    fi
)) &

echo "======================================"
echo "  Byblos CRM v2 startet..."
echo "  Browser: http://localhost:8501"
echo "  Stoppen: Strg+C"
echo "======================================"

python3 -m streamlit run app.py \
    --server.port=8501 \
    --server.address=localhost \
    --server.headless=true \
    --browser.gatherUsageStats=false
STARTER
chmod +x "$INSTALL_DIR/start_byblos.sh"

# Desktop-Eintrag (Linux)
if [[ "$OS" == "linux" ]]; then
    DESKTOP_FILE="$HOME/.local/share/applications/byblos-crm.desktop"
    mkdir -p "$(dirname $DESKTOP_FILE)"
    cat > "$DESKTOP_FILE" << DESKTOP
[Desktop Entry]
Name=Byblos CRM
Comment=Byblos Sicherheitsdienst CRM v2
Exec=bash -c "$INSTALL_DIR/start_byblos.sh"
Terminal=true
Type=Application
Categories=Office;Finance;
StartupNotify=true
DESKTOP
    chmod +x "$DESKTOP_FILE"
    echo -e "  ${GREEN}Desktop-Eintrag erstellt ✓${NC}"
fi

# Alias fuer Terminal
SHELL_RC="$HOME/.bashrc"
if [[ -f "$HOME/.zshrc" ]]; then SHELL_RC="$HOME/.zshrc"; fi
if ! grep -q "byblos-crm" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# Byblos CRM" >> "$SHELL_RC"
    echo "alias byblos-crm='$INSTALL_DIR/start_byblos.sh'" >> "$SHELL_RC"
    echo -e "  ${GREEN}Terminal-Alias 'byblos-crm' erstellt ✓${NC}"
fi

# macOS: App-Bundle (einfach)
if [[ "$OS" == "mac" ]]; then
    DESKTOP="$HOME/Desktop"
    cat > "$DESKTOP/Byblos CRM.command" << MACSTART
#!/bin/bash
$INSTALL_DIR/start_byblos.sh
MACSTART
    chmod +x "$DESKTOP/Byblos CRM.command"
    echo -e "  ${GREEN}macOS Starter auf Desktop erstellt ✓${NC}"
fi

echo -e "\n${GREEN}${BOLD}======================================================"
echo "  INSTALLATION ABGESCHLOSSEN!"
echo -e "======================================================${NC}"
echo ""
echo -e "  Installiert in: ${BOLD}$INSTALL_DIR${NC}"
echo ""
echo -e "  STARTEN (3 Moeglichkeiten):"
echo -e "  1) Terminal:   ${BOLD}byblos-crm${NC}  (nach neuem Terminal-Start)"
echo -e "  2) Direkt:     ${BOLD}$INSTALL_DIR/start_byblos.sh${NC}"
if [[ "$OS" == "linux" ]]; then
echo -e "  3) Desktop:    Anwendungsmenu → Byblos CRM"
elif [[ "$OS" == "mac" ]]; then
echo -e "  3) Desktop:    'Byblos CRM.command' auf dem Desktop"
fi
echo ""
echo -e "  Browser: ${BOLD}http://localhost:8501${NC}"
echo -e "  Login:   ${BOLD}admin${NC} / ${BOLD}admin123${NC} (sofort aendern!)"
echo ""

# Direkt starten?
read -p "  Byblos CRM jetzt starten? (j/N): " START_NOW
if [[ "$START_NOW" =~ ^[jJ]$ ]]; then
    exec "$INSTALL_DIR/start_byblos.sh"
fi
