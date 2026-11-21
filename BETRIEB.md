# Betrieb des Byblos CRM (Stufe 8)

Diese Anleitung gilt für den eigenen Rechner oder Server, auf dem das CRM dauerhaft läuft.
Sie ergänzt `SERVER_DEPLOYMENT.md`. Eine produktive Umstellung (Echtdaten, Livebetrieb) erfolgt erst nach
gesonderter technischer Freigabe durch den Inhaber.

## 1. Vor dem ersten Einsatz

1. Als `admin` anmelden und sofort das Passwort ändern (Einstellungen). Solange das Standardpasswort aktiv ist,
   zeigt das CRM Admins nach dem Login eine rote Warnung, und der Betriebsstatus meldet einen Fehler.
2. Unter **🛡️ Sicherheit → Zwei-Faktor-Auth** die 2FA für alle Admin-Konten einrichten
   (QR-Code mit einer Authenticator-App scannen, Code eingeben – erst dann ist 2FA aktiv).
3. Unter **⚙️ System → Betriebsstatus** prüfen, dass keine Zeile mit ❌ übrig ist.

## 2. Software-Update (Migration)

Immer in dieser Reihenfolge, während niemand im CRM arbeitet:

```bash
python crm_stage8.py migrate
```

Ablauf: Kopie der Datenbank → Probe-Migration auf der Kopie → Prüfung (Integrität, kein Datenverlust je Tabelle)
→ nur bei Erfolg Sicherung der echten Datenbank → echte Migration → bei einem Fehler automatische Wiederherstellung
der Sicherung. Ändert das Update nichts am Datenbankschema, wird nichts verändert und keine Sicherung angelegt.

## 3. Datensicherung

```bash
python crm_stage8.py backup
```

Erstellt eine konsistente Kopie (SQLite-Backup-API) in `backups/`, prüft sie, speichert die SHA-256-Prüfsumme
und protokolliert den Lauf. Sicherungen zusätzlich außerhalb des Rechners aufbewahren (z. B. verschlüsselter
externer Datenträger) – `backups/` liegt sonst auf derselben Festplatte.

## 4. Wiederherstellung

Nur nach Rücksprache mit dem Inhaber, CRM vorher beenden:

```bash
python -c "import crm_stage8; crm_stage8.restore_db('backups/<datei>.db', 'byblos_crm.db')"
```

Der bisherige Stand bleibt als `byblos_crm.db.vor-wiederherstellung-<zeit>` erhalten.

## 5. Regelmäßige Aufgaben einrichten

**Windows (Aufgabenplanung):**

```bat
schtasks /Create /SC DAILY /ST 02:30 /TN "Byblos CRM Sicherung" /TR "cmd /c cd /d C:\Pfad\zum\CRM && python crm_stage8.py backup"
schtasks /Create /SC DAILY /ST 06:00 /TN "Byblos CRM Zustand"   /TR "cmd /c cd /d C:\Pfad\zum\CRM && python crm_stage8.py health"
```

**Linux (crontab -e):**

```cron
30 2 * * * cd /pfad/zum/crm && python3 crm_stage8.py backup >> logs/backup.log 2>&1
0 6 * * *  cd /pfad/zum/crm && python3 crm_stage8.py health >> logs/health.log 2>&1
```

Erst wenn die Sicherung an mindestens drei Tagen gelaufen ist, zeigt **📊 Übersicht → KPI & Automationen**
die Datensicherung als „aktiv (nachgewiesen)“.

Die bestehende Tagesroutine (`run_daily_automation`) erstellt unter anderem fällige Dauerrechnungen automatisch.
Sie ist deshalb bewusst **nicht** Teil dieser Wartung und wird nur nach ausdrücklicher Freigabe eingeplant.

## 6. Monitoring

`python crm_stage8.py health` prüft Datenbank-Integrität, Standardpasswort, 2FA der Admins, Alter und Prüfsumme der
letzten Sicherung, Automationen und fehlende Erweiterungsmodule. Exit-Code `1` bedeutet: mindestens ein Fehler –
geeignet für Überwachungswerkzeuge oder eine Benachrichtigung aus der Aufgabenplanung.
