# Changelog SystemPlus

## Neue Tabellen

- audit_events
- compliance_checks
- export_jobs
- data_quality_issues

## Neue Funktionen

- register_systemplus
- audit_log_event
- scan_data_quality
- page_systemplus_cockpit
- page_compliance_center
- page_export_backup_center

## App-Menü erweitert

- SystemPlus Cockpit
- Compliance & Recht
- Export & Backup Center

## Syntaxprüfung

Geprüft mit:

```bash
python -m py_compile byblos_crm_app/app.py byblos_crm_app/extensions_complete_system.py
```

Ergebnis: bestanden.
