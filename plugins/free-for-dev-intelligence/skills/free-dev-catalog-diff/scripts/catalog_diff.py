#!/usr/bin/env python3
"""Compare two free-for.dev Markdown snapshots."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit

from catalog_tool import Entry, parse_catalog


def canonical_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def entry_key(entry: Entry) -> str:
    if entry.url and entry.url.startswith(("http://", "https://")):
        parts = urlsplit(entry.url)
        host = parts.netloc.lower().removeprefix("www.")
        path = parts.path.rstrip("/")
        return f"url:{host}{path}"
    return f"name:{canonical_name(entry.category)}:{canonical_name(entry.name)}"


def parse_file(path: str) -> list[Entry]:
    return parse_catalog(Path(path).read_text(encoding="utf-8"))


def compare(old_entries: list[Entry], new_entries: list[Entry]) -> dict:
    old_map = {entry_key(e): e for e in old_entries}
    new_map = {entry_key(e): e for e in new_entries}

    added = [new_map[k] for k in sorted(new_map.keys() - old_map.keys())]
    removed = [old_map[k] for k in sorted(old_map.keys() - new_map.keys())]
    changed = []
    for key in sorted(old_map.keys() & new_map.keys()):
        old = old_map[key]
        new = new_map[key]
        fields = {}
        for field in ("name", "url", "category", "description"):
            old_value = getattr(old, field)
            new_value = getattr(new, field)
            if old_value != new_value:
                fields[field] = {"old": old_value, "new": new_value}
        if fields:
            changed.append({"key": key, "old": asdict(old), "new": asdict(new), "changes": fields})

    return {
        "summary": {
            "old_entries": len(old_entries),
            "new_entries": len(new_entries),
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
        },
        "added": [asdict(e) for e in added],
        "removed": [asdict(e) for e in removed],
        "changed": changed,
    }


def print_markdown(result: dict) -> None:
    s = result["summary"]
    print("# Catalog diff")
    print()
    print(f"- Old entries: {s['old_entries']}")
    print(f"- New entries: {s['new_entries']}")
    print(f"- Added: {s['added']}")
    print(f"- Removed: {s['removed']}")
    print(f"- Changed: {s['changed']}")
    for title, key in (("Added", "added"), ("Removed", "removed")):
        print(f"\n## {title}")
        if not result[key]:
            print("None")
        for item in result[key]:
            print(f"- {item['name']} ({item['category']})")
            if item.get("url"):
                print(f"  - URL: {item['url']}")
    print("\n## Changed")
    if not result["changed"]:
        print("None")
    for item in result["changed"]:
        print(f"- {item['new']['name']}")
        for field, values in item["changes"].items():
            print(f"  - {field}: `{values['old']}` -> `{values['new']}`")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two free-for.dev README snapshots")
    parser.add_argument("old_markdown")
    parser.add_argument("new_markdown")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    result = compare(parse_file(args.old_markdown), parse_file(args.new_markdown))
    if args.json:
        content = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    else:
        from io import StringIO
        import contextlib
        buffer = StringIO()
        with contextlib.redirect_stdout(buffer):
            print_markdown(result)
        content = buffer.getvalue()
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
