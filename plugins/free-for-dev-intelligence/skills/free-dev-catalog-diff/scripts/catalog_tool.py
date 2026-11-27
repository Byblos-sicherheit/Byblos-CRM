#!/usr/bin/env python3
"""Parse and search the free-for.dev Markdown catalog.

No third-party dependencies are required.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

HTTP_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
ANY_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BULLET_RE = re.compile(r"^(\s*)[*-]\s+(.*)$")
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+.#/-]*", re.I)
SEPARATOR_RE = re.compile(r"\s+(?:—|–|-)\s+")

ALIASES = {
    "database": {"database", "db", "postgres", "postgresql", "mysql", "mongodb", "redis", "sql", "nosql"},
    "hosting": {"hosting", "deploy", "deployment", "web", "paas", "iaas", "serverless", "static"},
    "auth": {"auth", "authentication", "authorization", "identity", "sso", "oauth", "oidc", "user management"},
    "monitoring": {"monitor", "monitoring", "observability", "uptime", "metrics", "apm", "status"},
    "logging": {"logging", "logs", "log management", "observability"},
    "email": {"email", "mail", "smtp", "transactional email", "newsletter"},
    "storage": {"storage", "object storage", "media", "file", "cdn"},
    "security": {"security", "tls", "ssl", "pki", "secrets", "vulnerability", "waf", "ddos"},
    "ai": {"ai", "ml", "machine learning", "generative ai", "llm", "inference", "models"},
    "ci": {"ci", "cd", "pipeline", "build", "continuous integration", "continuous delivery"},
    "api": {"api", "apis", "data", "webhook", "integration"},
    "analytics": {"analytics", "events", "statistics", "product analytics", "traffic"},
    "team": {"team", "collaboration", "project management", "issue tracking", "chat"},
    "testing": {"testing", "test", "qa", "browser", "load test", "visual regression"},
}

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "the", "to", "with",
    "ein", "eine", "einer", "eines", "für", "mit", "oder", "und", "von", "zu", "der", "die", "das", "im", "im", "am",
}


@dataclass(frozen=True)
class Entry:
    category: str
    name: str
    url: str | None
    description: str
    raw_text: str
    line: int
    indent: int
    flags: dict[str, bool]


def normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    if not url.lower().startswith(("http://", "https://")):
        return url.strip()
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def classify_flags(text: str) -> dict[str, bool]:
    t = text.lower()
    no_card = bool(re.search(r"no (?:credit )?card|without (?:a )?(?:credit )?card", t))
    card_required = bool(re.search(r"(?:credit )?card required|requires? (?:a )?(?:credit )?card", t)) and not no_card
    non_commercial = bool(re.search(r"non[- ]commercial|not for commercial", t))
    commercial_explicit = bool(re.search(r"commercial use|commercial and non-commercial", t)) and not non_commercial
    trial = bool(re.search(r"\btrial\b", t))
    time_limited = bool(re.search(r"\b(?:6|12|24)\s*(?:mo|mos|month|months)\b|for (?:one|1|twelve|12) year", t))
    return {
        "card_required": card_required,
        "no_card_stated": no_card,
        "trial_mentioned": trial,
        "time_limited_mentioned": time_limited,
        "open_source_or_public_only": bool(re.search(r"open[ -]source|\boss\b|public repositor", t)),
        "personal_or_individual_only": bool(re.search(r"personal (?:use|project)|individuals? only|single user", t)),
        "non_commercial": non_commercial,
        "commercial_use_explicit": commercial_explicit,
        "no_signup_stated": bool(re.search(r"no sign[- ]?up|without sign[- ]?up|no account", t)),
        "region_mentioned": bool(re.search(r"\bregion\b|north america|europe|\beu\b|\bus only\b", t)),
        "inactivity_risk_mentioned": bool(re.search(r"sleep|pause|idle|reclaim", t)),
        "free_forever_stated": bool(re.search(r"free forever|forever free|always[- ]free", t)),
    }


def split_entry_text(raw: str) -> tuple[str, str | None, str]:
    links = ANY_LINK_RE.findall(raw)
    if links:
        name, url = links[0]
        remainder = raw[raw.find(")") + 1 :].strip()
        remainder = re.sub(r"^(?:—|–|-)\s*", "", remainder).strip()
        return name.strip(), normalize_url(url), remainder
    parts = SEPARATOR_RE.split(raw, maxsplit=1)
    name = parts[0].strip(" *`")
    desc = parts[1].strip() if len(parts) > 1 else ""
    return name, None, desc


def parse_catalog(markdown: str) -> list[Entry]:
    lines = markdown.splitlines()
    sections: list[dict] = []
    current: dict | None = None
    for line_no, line in enumerate(lines, 1):
        heading = HEADING_RE.match(line)
        if heading:
            current = {"name": heading.group(1).strip(), "bullets": []}
            sections.append(current)
            continue
        if current is None:
            continue
        bullet = BULLET_RE.match(line)
        if not bullet:
            continue
        raw = bullet.group(2).strip()
        if "Back to Top" in raw:
            continue
        indent = len(bullet.group(1).replace("\t", "    "))
        current["bullets"].append((line_no, indent, raw))

    entries: list[Entry] = []
    for section in sections:
        bullets = section["bullets"]
        if not bullets:
            continue
        min_indent = min(indent for _, indent, _ in bullets)
        index = 0
        while index < len(bullets):
            line_no, indent, raw = bullets[index]
            if indent != min_indent:
                index += 1
                continue
            child_texts: list[str] = []
            child_index = index + 1
            while child_index < len(bullets) and bullets[child_index][1] > min_indent:
                child_texts.append(bullets[child_index][2])
                child_index += 1
            name, url, description = split_entry_text(raw)
            combined_description = " | ".join(part for part in [description, *child_texts] if part)
            combined_raw = " | ".join([raw, *child_texts])
            entries.append(
                Entry(
                    category=section["name"],
                    name=name,
                    url=url,
                    description=combined_description,
                    raw_text=combined_raw,
                    line=line_no,
                    indent=indent,
                    flags=classify_flags(combined_raw),
                )
            )
            index = child_index
    return entries


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text) if token.lower() not in STOPWORDS and len(token) > 1]


def expand_query(tokens: Iterable[str]) -> set[str]:
    expanded = set(tokens)
    joined = " ".join(tokens)
    for key, values in ALIASES.items():
        if key in expanded or any(v in joined for v in values):
            expanded.update(values)
    return expanded


def score_entry(entry: Entry, query_tokens: set[str]) -> float:
    name_tokens = set(tokenize(entry.name))
    category_tokens = set(tokenize(entry.category))
    description_tokens = set(tokenize(entry.description))
    raw_lower = entry.raw_text.lower()
    score = 0.0
    for token in query_tokens:
        if token in name_tokens:
            score += 7.0
        if token in category_tokens:
            score += 4.0
        if token in description_tokens:
            score += 2.0
        if " " in token and token in raw_lower:
            score += 5.0
    phrase = " ".join(sorted(query_tokens))
    if phrase and phrase in raw_lower:
        score += 3.0
    return score


def search_entries(
    entries: list[Entry],
    query: str,
    category: str | None = None,
    exclude_card_required: bool = False,
    commercial: bool = False,
    exclude_trial_mentions: bool = False,
    limit: int = 10,
) -> list[tuple[float, Entry]]:
    tokens = expand_query(tokenize(query))
    category_lower = category.lower() if category else None
    results: list[tuple[float, Entry]] = []
    for entry in entries:
        if category_lower and category_lower not in entry.category.lower():
            continue
        if exclude_card_required and entry.flags["card_required"]:
            continue
        if commercial and entry.flags["non_commercial"]:
            continue
        if exclude_trial_mentions and entry.flags["trial_mentioned"]:
            continue
        score = score_entry(entry, tokens)
        if score > 0:
            results.append((score, entry))
    results.sort(key=lambda pair: (-pair[0], pair[1].name.lower(), pair[1].category.lower()))
    return results[:limit]


def load_entries(path: Path) -> list[Entry]:
    return parse_catalog(path.read_text(encoding="utf-8"))


def output_entries(entries: list[Entry], as_json: bool) -> None:
    if as_json:
        print(json.dumps([asdict(e) for e in entries], indent=2, ensure_ascii=False))
        return
    for e in entries:
        print(f"- {e.name} | {e.category}")
        if e.url:
            print(f"  URL: {e.url}")
        if e.description:
            print(f"  Catalog claim: {e.description}")
        active_flags = [name for name, enabled in e.flags.items() if enabled]
        if active_flags:
            print(f"  Signals: {', '.join(active_flags)}")
        print(f"  Source line: {e.line}")


def command_parse(args: argparse.Namespace) -> int:
    entries = load_entries(Path(args.markdown))
    data = [asdict(e) for e in entries]
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


def command_stats(args: argparse.Namespace) -> int:
    entries = load_entries(Path(args.markdown))
    categories: dict[str, int] = {}
    for entry in entries:
        categories[entry.category] = categories.get(entry.category, 0) + 1
    result = {
        "entries": len(entries),
        "categories": len(categories),
        "category_counts": dict(sorted(categories.items(), key=lambda item: (-item[1], item[0].lower()))),
        "signal_counts": {
            flag: sum(1 for entry in entries if entry.flags.get(flag))
            for flag in sorted(next(iter(entries)).flags) if entries
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def command_search(args: argparse.Namespace) -> int:
    entries = load_entries(Path(args.markdown))
    results = search_entries(
        entries,
        query=args.query,
        category=args.category,
        exclude_card_required=args.exclude_card_required,
        commercial=args.commercial,
        exclude_trial_mentions=args.exclude_trial_mentions,
        limit=args.limit,
    )
    if args.json:
        print(json.dumps([{"score": score, **asdict(entry)} for score, entry in results], indent=2, ensure_ascii=False))
    else:
        output_entries([entry for _, entry in results], as_json=False)
    return 0 if results else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse and search the free-for.dev Markdown catalog")
    sub = parser.add_subparsers(dest="command", required=True)

    p_parse = sub.add_parser("parse", help="Parse catalog entries to JSON")
    p_parse.add_argument("markdown")
    p_parse.add_argument("-o", "--output")
    p_parse.set_defaults(func=command_parse)

    p_stats = sub.add_parser("stats", help="Print catalog statistics")
    p_stats.add_argument("markdown")
    p_stats.set_defaults(func=command_stats)

    p_search = sub.add_parser("search", help="Search catalog entries")
    p_search.add_argument("markdown")
    p_search.add_argument("--query", required=True)
    p_search.add_argument("--category")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--exclude-card-required", action="store_true")
    p_search.add_argument("--exclude-trial-mentions", action="store_true")
    p_search.add_argument("--commercial", action="store_true", help="Exclude entries explicitly marked non-commercial")
    p_search.add_argument("--json", action="store_true")
    p_search.set_defaults(func=command_search)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc.filename}", file=sys.stderr)
        return 1
    except UnicodeDecodeError:
        print("error: input must be UTF-8 Markdown", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
