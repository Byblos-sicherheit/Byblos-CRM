#!/usr/bin/env bash
# =============================================================
# byblos_daily.sh – Byblos CRM v2 Tagesroutine
# =============================================================
# Ausführung täglich via Cron:
#   0 6 * * * /opt/byblos-crm/byblos_daily.sh >> /var/log/byblos_crm.log 2>&1
# =============================================================

set -euo pipefail

APP_DIR="${BYBLOS_APP_DIR:-/opt/byblos-crm/byblos_crm_app}"
PYTHON="${BYBLOS_PYTHON:-$(which python3)}"
BACKUP_DIR="${BYBLOS_BACKUP_DIR:-/var/backups/byblos-crm}"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

log() { echo "$LOG_PREFIX $*"; }

log "=== Byblos CRM Tagesroutine startet ==="
mkdir -p "$BACKUP_DIR"

# 1. Datenbankbackup
DB="$APP_DIR/byblos_crm.db"
if [ -f "$DB" ]; then
    DATE=$(date +%Y-%m-%d)
    BACKUP="$BACKUP_DIR/byblos_crm_$DATE.db"
    cp "$DB" "$BACKUP"
    SIZE=$(du -sh "$BACKUP" | cut -f1)
    log "Backup erstellt: $BACKUP ($SIZE)"
    # Alte Backups aufräumen (>30 Tage)
    find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
    log "Alte Backups bereinigt."
else
    log "WARNUNG: Datenbankdatei nicht gefunden: $DB"
fi

# 2. Python-Routinen ausführen
cd "$APP_DIR"
if [ -f "app.py" ]; then
    "$PYTHON" - << 'PYEOF'
import sys
sys.path.insert(0, '.')
try:
    import app
    app.init_db()

    # Überfällige Rechnungen markieren
    app.mark_overdue_invoices()
    print("[OK] Überfällige Rechnungen markiert")

    # Mahnungen vorbereiten (kein Auto-Versand, nur Queue)
    created, sent = app.queue_overdue_reminders(send_now=False)
    print(f"[OK] Mahnungen vorbereitet: {created} erstellt")

    # KPIs berechnen
    kpis = app.calculate_daily_kpis()
    print(f"[OK] KPIs berechnet: {kpis}")

    # Backup in DB registrieren
    import os
    from datetime import date
    backup_path = f"/var/backups/byblos-crm/byblos_crm_{date.today().isoformat()}.db"
    if os.path.exists(backup_path):
        size = os.path.getsize(backup_path)
        app.run("INSERT INTO backups(file_path,file_size,note) VALUES(?,?,?)",
                (backup_path, size, "automatisch täglich"))
        print(f"[OK] Backup in DB registriert")

    # Automatik-Log
    app.run("INSERT INTO automation_log(action,result) VALUES(?,?)",
            ("daily_routine", "success"))

    print("[OK] Tagesroutine abgeschlossen")
except Exception as e:
    print(f"[FEHLER] Tagesroutine: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)
PYEOF
    log "Python-Routinen abgeschlossen"
else
    log "WARNUNG: app.py nicht gefunden in $APP_DIR"
fi

log "=== Tagesroutine beendet ==="
