#!/usr/bin/env sh
set -eu

project_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$project_root"

sh -n scripts/add-user.sh scripts/remove-user.sh scripts/validate.sh
python3 tests/static_checks.py
sh tests/test-add-user.sh
sh tests/test-remove-user.sh
