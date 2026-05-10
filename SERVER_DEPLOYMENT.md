# Byblos CRM v2 – Server-Deployment

## Option A: Docker (empfohlen)

### Voraussetzungen
- Linux-Server (Ubuntu 22.04 LTS empfohlen, min. 1 GB RAM)
- Docker + Docker Compose installiert

### Installation

```bash
# 1. Docker installieren (Ubuntu)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# 2. Docker Compose installieren
sudo apt-get install -y docker-compose-plugin

# 3. Projektdateien hochladen
# FTP/SFTP/SCP zu /opt/byblos-crm/
scp -r byblos_crm_v2/byblos_crm_app/ user@server:/opt/byblos-crm/

# 4. Starten
cd /opt/byblos-crm
docker compose up -d

# 5. Status prüfen
docker compose ps
docker compose logs -f
```

### App aufrufen
- Lokal: http://localhost:8501
- Aus dem Netzwerk: http://SERVER-IP:8501

---

## Option B: Mit Nginx + SSL (Produktionsempfehlung)

### Nginx installieren und konfigurieren

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx

# SSL-Zertifikat (Let's Encrypt)
sudo certbot --nginx -d crm.byblos-sicherheit.de

# Nginx-Konfiguration
sudo nano /etc/nginx/sites-available/byblos-crm
```

Inhalt der Nginx-Konfiguration (`nginx.conf`):

```nginx
server {
    listen 80;
    server_name crm.byblos-sicherheit.de;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name crm.byblos-sicherheit.de;

    ssl_certificate     /etc/letsencrypt/live/crm.byblos-sicherheit.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/crm.byblos-sicherheit.de/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Sicherheits-Header
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header Referrer-Policy strict-origin-when-cross-origin;

    # Streamlit WebSocket + HTTP
    location / {
        proxy_pass         http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;

        # Upload-Größe (für Belege/PDFs)
        client_max_body_size 200M;
    }

    # Basis-Auth als zweite Sicherheitsstufe (optional)
    # auth_basic "Byblos CRM";
    # auth_basic_user_file /etc/nginx/.htpasswd;
}
```

```bash
# Nginx aktivieren
sudo ln -s /etc/nginx/sites-available/byblos-crm /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## Option C: Direkte Python-Installation (ohne Docker)

```bash
# Ubuntu 22.04
sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv

# Projektverzeichnis
mkdir -p /opt/byblos-crm
cd /opt/byblos-crm

# Virtuelle Umgebung
python3 -m venv venv
source venv/bin/activate

# Abhängigkeiten
pip install -r requirements.txt
pip install "qrcode[pil]"

# Starten
streamlit run app.py --server.address=0.0.0.0 --server.port=8501

# Als Systemdienst (systemd)
sudo nano /etc/systemd/system/byblos-crm.service
```

Inhalt der systemd-Unit (`byblos-crm.service`):

```ini
[Unit]
Description=Byblos CRM v2
After=network.target

[Service]
Type=simple
User=byblos
WorkingDirectory=/opt/byblos-crm/byblos_crm_app
ExecStart=/opt/byblos-crm/venv/bin/streamlit run app.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.headless=true
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable byblos-crm
sudo systemctl start byblos-crm
sudo systemctl status byblos-crm
```

---

## Backup-Strategie

### Täglich automatisch (Crontab)
```bash
crontab -e

# Backup täglich 03:00 Uhr
0 3 * * * /opt/byblos-crm/scripts/backup.sh >> /var/log/byblos-backup.log 2>&1
```

`/opt/byblos-crm/scripts/backup.sh`:
```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/var/backups/byblos-crm"
mkdir -p "$BACKUP_DIR"

# Datenbankdatei sichern
cp /opt/byblos-crm/byblos_crm_app/byblos_crm.db "$BACKUP_DIR/byblos_crm_$DATE.db"
# Optional: Docker-Volume sichern
# docker run --rm -v byblos_crm_database:/data -v $BACKUP_DIR:/backup \
#   alpine tar czf /backup/byblos_db_$DATE.tar.gz /data

# Alte Backups löschen (älter als 30 Tage)
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete

echo "[$(date)] Backup erstellt: byblos_crm_$DATE.db"
```

### Offsite-Backup (optional)
```bash
# Zu einem anderen Server kopieren
rsync -avz --delete /var/backups/byblos-crm/ user@backup-server:/backups/byblos/
```

---

## Update-Prozess

```bash
cd /opt/byblos-crm

# 1. Neues Paket hochladen und entpacken
# 2. Backup erstellen
cp byblos_crm_app/byblos_crm.db /var/backups/byblos-pre-update.db

# Docker-Update
docker compose pull || true
docker compose up -d --build

# Systemd-Update
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart byblos-crm
```

---

## Sicherheitsempfehlungen

| Maßnahme | Beschreibung |
|---|---|
| **Firewall** | Port 8501 nur intern erreichbar, Nginx auf 443 |
| **Starkes Passwort** | Admin-Passwort sofort nach Installation ändern |
| **SSL** | Let's Encrypt (kostenlos) via Certbot |
| **Updates** | `sudo unattended-upgrades` aktivieren |
| **Backup-Verschlüsselung** | `gpg --symmetric backup.db` |
| **Fail2Ban** | Nginx-Zugriffe auf Brute-Force prüfen |

---

## Monitoring

```bash
# App-Status
docker compose ps
curl -f http://localhost:8501/_stcore/health

# Ressourcen
docker stats byblos_crm

# Logs (letzte 100 Zeilen)
docker compose logs --tail=100 -f
```
