#!/usr/bin/env sh
set -eu

project_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
users_file="$project_root/config/users.caddy"
caddy_image="caddy:2.11.4-alpine"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker wurde nicht gefunden." >&2
  exit 1
fi

username="${1:-}"
if [ -z "$username" ]; then
  printf "Benutzername (3-32 Zeichen): "
  IFS= read -r username
fi

case "$username" in
  ""|[!A-Za-z0-9]*|*[!A-Za-z0-9._-]*)
    echo "Ungültiger Benutzername." >&2
    exit 1
    ;;
esac

if [ "${#username}" -lt 3 ] || [ "${#username}" -gt 32 ]; then
  echo "Der Benutzername muss 3-32 Zeichen haben." >&2
  exit 1
fi

printf "Passwort (mindestens 14 Zeichen): "
trap 'stty echo 2>/dev/null || true' EXIT INT TERM
stty -echo
IFS= read -r password
stty echo
printf "\nPasswort wiederholen: "
stty -echo
IFS= read -r confirmation
stty echo
printf "\n"

if [ "${#password}" -lt 14 ]; then
  echo "Das Passwort ist zu kurz." >&2
  exit 1
fi
if [ "$password" != "$confirmation" ]; then
  echo "Die Passwörter stimmen nicht überein." >&2
  exit 1
fi

password_hash="$(docker run --rm "$caddy_image" caddy hash-password --plaintext "$password")"
password=""
confirmation=""

tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"; stty echo 2>/dev/null || true' EXIT INT TERM
{
  echo "# Automatisch verwaltete bcrypt-Zugänge. Keine Klartext-Passwörter."
  if [ -f "$users_file" ]; then
    awk -v user="$username" '
      /^[[:space:]]*#/ { next }
      NF >= 2 && $1 != user && $2 ~ /^\$2[aby]\$/ { print }
    ' "$users_file"
  fi
  printf "%s %s\n" "$username" "$password_hash"
} > "$tmp_file"
mv "$tmp_file" "$users_file"
chmod 600 "$users_file"
trap - EXIT INT TERM

echo "Benutzer '$username' wurde gespeichert."
echo "Zum Aktivieren: docker compose restart gateway"
