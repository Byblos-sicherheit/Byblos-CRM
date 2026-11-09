#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def metadata(path: Path, source: str | None = None) -> dict:
    data = path.read_bytes()
    text = data.decode('utf-8')
    return {
        'path': str(path),
        'source': source,
        'acquired_at_utc': datetime.now(timezone.utc).isoformat(),
        'bytes': len(data),
        'lines': len(text.splitlines()),
        'sha256': digest(data),
    }


def cmd_create(args: argparse.Namespace) -> int:
    path = Path(args.markdown)
    meta = metadata(path, args.source)
    out = Path(args.output) if args.output else path.with_suffix(path.suffix + '.meta.json')
    out.write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(meta, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    path = Path(args.markdown)
    meta = json.loads(Path(args.metadata).read_text(encoding='utf-8'))
    actual = digest(path.read_bytes())
    result = {'expected_sha256': meta.get('sha256'), 'actual_sha256': actual, 'match': actual == meta.get('sha256')}
    print(json.dumps(result, indent=2))
    return 0 if result['match'] else 2


def cmd_compare(args: argparse.Namespace) -> int:
    a = Path(args.old).read_bytes()
    b = Path(args.new).read_bytes()
    result = {
        'old_sha256': digest(a),
        'new_sha256': digest(b),
        'changed': a != b,
        'old_bytes': len(a),
        'new_bytes': len(b),
    }
    print(json.dumps(result, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('create')
    c.add_argument('markdown')
    c.add_argument('--source')
    c.add_argument('--output')
    c.set_defaults(func=cmd_create)
    v = sub.add_parser('verify')
    v.add_argument('markdown')
    v.add_argument('metadata')
    v.set_defaults(func=cmd_verify)
    d = sub.add_parser('compare')
    d.add_argument('old')
    d.add_argument('new')
    d.set_defaults(func=cmd_compare)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
