#!/usr/bin/env sh
set -eu

project_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$project_root"

if [ ! -f .env ]; then
  echo ".env fehlt. Zuerst: cp .env.example .env" >&2
  exit 1
fi
if ! awk 'NF >= 2 && $1 !~ /^#/ && $2 ~ /^\$2[aby]\$/' config/users.caddy | grep -q .; then
  echo "Kein aktiver bcrypt-Benutzer vorhanden." >&2
  exit 1
fi

docker compose config --quiet
docker compose run --rm --no-deps gateway \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
echo "Compose- und Caddy-Konfiguration sind gültig."
