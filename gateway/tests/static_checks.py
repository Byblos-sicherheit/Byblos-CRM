#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def read(relative_path: str) -> str:
    path = ROOT / relative_path
    require(path.is_file(), f"Fehlende Datei: {relative_path}")
    return path.read_text(encoding="utf-8") if path.is_file() else ""


caddyfile = read("config/Caddyfile")
compose = read("compose.yaml")
env_example = read(".env.example")
users = read("config/users.caddy")
for required_document in (
    "DEPLOY-ANLEITUNG.md",
    "docs/OPERATIONS.md",
    "docs/BACKUP-RESTORE.md",
    "docs/SECURITY-PRIVACY.md",
    "docs/ROLES.md",
    "docs/ROUTER-DNS-CHECKLIST.md",
    "docs/SOURCES.md",
    "reports/DELIVERY-MATRIX.md",
    "reports/OPEN-ITEMS.md",
    "THIRD-PARTY-NOTICES.md",
):
    read(required_document)

require(caddyfile.count("{") == caddyfile.count("}"), "Caddyfile: Klammern sind nicht ausgeglichen")
for token in (
    'basic_auth bcrypt "Byblos Server"',
    "import users.caddy",
    "handle_path /crm/*",
    "handle_path /wks/*",
    "handle_path /files/*",
    "header_up -Authorization",
    "{$LEXAI_UPSTREAM}",
    "{$DOMAIN}",
):
    require(token in caddyfile, f"Caddyfile: Pflichtteil fehlt: {token}")

for token in (
    "caddy:2.11.4-alpine",
    '"80:80/tcp"',
    '"443:443/tcp"',
    '"443:443/udp"',
    "./config:/etc/caddy:ro",
    "byblos_gateway_data",
):
    require(token in compose, f"compose.yaml: Pflichtteil fehlt: {token}")

for variable in (
    "DOMAIN",
    "ACME_EMAIL",
    "LEXAI_UPSTREAM",
    "CRM_UPSTREAM",
    "WKS_UPSTREAM",
    "FILES_UPSTREAM",
):
    require(re.search(rf"(?m)^{variable}=", env_example) is not None, f".env.example: {variable} fehlt")
    require(f"${{{variable}" in compose, f"compose.yaml: {variable} fehlt")

active_users = [
    line
    for line in users.splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]
require(not active_users, "Im Lieferpaket ist ein aktiver Gateway-Benutzer enthalten")
require(not (ROOT / ".env").exists(), "Im Lieferpaket ist eine produktive .env enthalten")

secret_patterns = {
    "privater Schlüssel": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "AWS-Zugriffsschlüssel": re.compile(r"AKIA[0-9A-Z]{16}"),
    "OpenAI-Schlüssel": re.compile(r"sk-proj-[A-Za-z0-9_-]+"),
}
for path in ROOT.rglob("*"):
    if not path.is_file() or ".zip" in path.suffixes:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for label, pattern in secret_patterns.items():
        require(pattern.search(text) is None, f"Mögliches Geheimnis ({label}) in {path.relative_to(ROOT)}")

markdown_link = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+)\)")
for path in ROOT.rglob("*.md"):
    text = path.read_text(encoding="utf-8")
    for target in markdown_link.findall(text):
        target_path = (path.parent / target).resolve()
        require(target_path.exists(), f"Toter relativer Link in {path.relative_to(ROOT)}: {target}")

if ERRORS:
    print("\n".join(f"FEHLER: {error}" for error in ERRORS))
    sys.exit(1)

print("Statische Gateway-Prüfungen: BESTANDEN")
