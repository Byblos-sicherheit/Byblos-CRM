#!/usr/bin/env sh
set -eu

project_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
users_file="$project_root/config/users.caddy"
username="${1:-}"

if [ -z "$username" ]; then
  echo "Verwendung: $0 BENUTZERNAME" >&2
  exit 1
fi
if [ ! -f "$users_file" ]; then
  echo "Benutzerdatei nicht gefunden." >&2
  exit 1
fi

active_count="$(awk 'NF >= 2 && $1 !~ /^#/ && $2 ~ /^\$2[aby]\$/ { count++ } END { print count+0 }' "$users_file")"
found_count="$(awk -v user="$username" 'NF >= 2 && $1 == user && $2 ~ /^\$2[aby]\$/ { count++ } END { print count+0 }' "$users_file")"

if [ "$found_count" -eq 0 ]; then
  echo "Benutzer '$username' wurde nicht gefunden." >&2
  exit 1
fi
if [ "$active_count" -le 1 ]; then
  echo "Der letzte Benutzer wird nicht entfernt. Zuerst einen Ersatzbenutzer anlegen." >&2
  exit 1
fi

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT INT TERM
{
  echo "# Automatisch verwaltete bcrypt-Zugänge. Keine Klartext-Passwörter."
  awk -v user="$username" 'NF >= 2 && $1 !~ /^#/ && $1 != user && $2 ~ /^\$2[aby]\$/ { print }' "$users_file"
} > "$tmp_file"
mv "$tmp_file" "$users_file"
chmod 600 "$users_file"
trap - EXIT INT TERM

echo "Benutzer '$username' wurde entfernt."
echo "Zum Aktivieren: docker compose restart gateway"
