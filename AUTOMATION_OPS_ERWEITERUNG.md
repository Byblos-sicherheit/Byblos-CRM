# Automation Ops Erweiterung

Diese Stufe ergänzt das CRM um operative Automatisierung und Sicherheitslogik.

## Enthalten

- SLA-Regeln für Leads, Angebote, Verträge und Rechnungen
- Mahnstufenlogik für offene Rechnungen
- Angebotsstatus und Auftragsstatus
- Dokumentstatus für Freigabe und Archivierung
- Import-Quarantäne für unsichere Datensätze
- KI-Antwort-Schutz mit Ampel: grün, gelb, rot
- Tagesabschluss-Checkliste
- Monatsabschluss-Checkliste

## Wichtig

Automatische Entscheidungen dürfen nicht blind gebucht werden, wenn Dokumente unsicher sind. Alles unter hoher Sicherheit gehört in die Prüfliste oder Quarantäne.

## Nächster technischer Schritt

`extensions_automation_ops.py` kann in `app.py` eingebunden werden. Sinnvoll ist ein eigener Menüpunkt:

- Automation Ops
- Mahnungen
- Quarantäne
- Tagesabschluss
- Monatsabschluss

## Rechtlicher Hinweis

Mahnungen, AGB, AVV, Datenschutz und Vertragsvorlagen müssen vor produktivem Einsatz rechtlich geprüft werden.
