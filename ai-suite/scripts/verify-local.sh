#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

printf '== Backend tests and syntax ==\n'
(
  cd "$ROOT/backend"
  node --test
  npm run check
)

printf '== Antigravity agent-backend tests and syntax ==\n'
(
  cd "$ROOT/agent-backend"
  PYTHONPATH=. python3 -m unittest discover -s tests -v
  python3 -m compileall -q byblos_agent tests
)

printf '== Static project checks ==\n'
python3 - "$ROOT" <<'PY'
from pathlib import Path
import json
import re
import sys
import tomllib
import xml.etree.ElementTree as ET

root = Path(sys.argv[1])

json_files = list(root.rglob("*.json"))
for path in json_files:
    json.loads(path.read_text(encoding="utf-8"))

toml_files = list(root.rglob("*.toml"))
for path in toml_files:
    tomllib.loads(path.read_text(encoding="utf-8"))

xml_files = list(root.rglob("*.xml"))
for path in xml_files:
    ET.parse(path)

secret_pattern = re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")
for path in root.rglob("*"):
    if not path.is_file() or ".git" in path.parts:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    if secret_pattern.search(text):
        raise SystemExit(f"Possible OpenAI API key found in {path}")
    obsolete_model = "gpt-5.6" + "-luna"
    if obsolete_model in text:
        raise SystemExit(f"Unsupported placeholder model name found in {path}")

print(f"Validated {len(json_files)} JSON, {len(toml_files)} TOML and {len(xml_files)} XML files")
print("No embedded OpenAI key pattern or obsolete model placeholder found")
PY

bash -n "$ROOT/android-app/gradlew"

if [[ "${RUN_ANDROID_BUILD:-0}" == "1" ]]; then
  printf '== Android unit tests, lint and debug build ==\n'
  (
    cd "$ROOT/android-app"
    ./gradlew --no-daemon testDebugUnitTest lintDebug assembleDebug
  )
else
  printf 'Android build skipped. Run with RUN_ANDROID_BUILD=1 when JDK, SDK and Gradle network/cache are available.\n'
fi
