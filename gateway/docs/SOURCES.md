# Technische Quellen

Stand der Prüfung: 29.07.2026.

- Caddy `basic_auth`: https://caddyserver.com/docs/caddyfile/directives/basic_auth
- Caddy Automatic HTTPS: https://caddyserver.com/docs/automatic-https
- Caddy `handle_path`: https://caddyserver.com/docs/caddyfile/directives/handle_path
- Caddy `import`: https://caddyserver.com/docs/caddyfile/directives/import
- Caddy Zugriffsprotokolle: https://caddyserver.com/docs/caddyfile/directives/log
- Offizielles Caddy-Container-Image:
  https://hub.docker.com/_/caddy/

Die offizielle Caddy-Dokumentation bestätigt, dass Passwörter für
`basic_auth` gehasht hinterlegt werden müssen, `handle_path` den jeweiligen
Pfadpräfix entfernt und öffentliches HTTPS bei korrektem DNS, erreichbaren
Ports 80/443 sowie persistentem Caddy-Datenspeicher automatisch verwaltet wird.
