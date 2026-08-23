#!/usr/bin/env sh
set -eu

temp_root="$(mktemp -d)"
trap 'rm -rf "$temp_root"' EXIT INT TERM
mkdir -p "$temp_root/scripts" "$temp_root/config" "$temp_root/fake-bin"
cp "$(dirname "$0")/../scripts/add-user.sh" "$temp_root/scripts/add-user.sh"

printf '%s\n' \
  '#!/usr/bin/env sh' \
  'if [ "$1" = "run" ]; then' \
  '  printf "%s\n" '\''$2a$14$TESTHASHGENERATEDBYFAKEDOCKER'\''' \
  '  exit 0' \
  'fi' \
  'exit 0' \
  > "$temp_root/fake-bin/docker"
chmod +x "$temp_root/fake-bin/docker"

printf '%s\n%s\n' 'VeryLongTestPassword1!' 'VeryLongTestPassword1!' |
  script -q -e -c "PATH=$temp_root/fake-bin:$PATH $temp_root/scripts/add-user.sh alice" /dev/null >/dev/null

if ! grep -q '^alice \$2a\$14\$TESTHASH' "$temp_root/config/users.caddy"; then
  echo "Benutzer wurde nicht mit bcrypt-Hash gespeichert." >&2
  exit 1
fi
if grep -q 'VeryLongTestPassword' "$temp_root/config/users.caddy"; then
  echo "Klartext-Passwort wurde gespeichert." >&2
  exit 1
fi

echo "Benutzeranlage ohne Klartextspeicherung: BESTANDEN"
