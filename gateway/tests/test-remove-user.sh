#!/usr/bin/env sh
set -eu

temp_root="$(mktemp -d)"
trap 'rm -rf "$temp_root"' EXIT INT TERM
mkdir -p "$temp_root/scripts" "$temp_root/config"
cp "$(dirname "$0")/../scripts/remove-user.sh" "$temp_root/scripts/remove-user.sh"
printf '%s\n' \
  '# Testzugänge' \
  'alice $2a$14$TESTHASHALICE' \
  'bob $2b$14$TESTHASHBOB' \
  > "$temp_root/config/users.caddy"

"$temp_root/scripts/remove-user.sh" alice >/dev/null

if grep -q '^alice ' "$temp_root/config/users.caddy"; then
  echo "Entfernter Benutzer ist noch vorhanden." >&2
  exit 1
fi
if ! grep -q '^bob ' "$temp_root/config/users.caddy"; then
  echo "Verbleibender Benutzer wurde fälschlich entfernt." >&2
  exit 1
fi
if "$temp_root/scripts/remove-user.sh" bob >/dev/null 2>&1; then
  echo "Der letzte Benutzer konnte fälschlich entfernt werden." >&2
  exit 1
fi

echo "Benutzerentfernung und Schutz des letzten Benutzers: BESTANDEN"
