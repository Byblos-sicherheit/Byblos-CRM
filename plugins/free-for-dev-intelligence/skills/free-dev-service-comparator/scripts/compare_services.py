#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path

DEFAULT_WEIGHTS = {
    'capability_fit': 3.0,
    'quota_fit': 2.5,
    'billing_safety': 2.0,
    'region_fit': 1.5,
    'operations': 1.5,
    'portability': 1.0,
    'evidence': 2.0,
}


def clamp(value):
    if value is None:
        return None
    value = float(value)
    return max(0.0, min(1.0, value))


def hard_fail(service, constraints):
    checks = []
    if constraints.get('require_no_card'):
        val = service.get('card_required')
        checks.append(('no_card', False if val is True else True if val is False else None))
    if constraints.get('require_commercial'):
        val = service.get('commercial_allowed')
        checks.append(('commercial', val if isinstance(val, bool) else None))
    if constraints.get('require_eu_region'):
        val = service.get('eu_region')
        checks.append(('eu_region', val if isinstance(val, bool) else None))
    policy = constraints.get('unknown_hard_constraint_policy', 'disqualify')
    reasons = []
    for name, passed in checks:
        if passed is False:
            reasons.append(name + ':failed')
        elif passed is None and policy == 'disqualify':
            reasons.append(name + ':unknown')
    return reasons


def score(service, weights):
    weighted = 0.0
    used = 0.0
    missing = []
    components = {}
    for key, weight in weights.items():
        val = clamp(service.get(key))
        if val is None:
            missing.append(key)
            continue
        components[key] = val
        weighted += val * float(weight)
        used += float(weight)
    base = weighted / used if used else 0.0
    penalty = min(0.20, 0.02 * len(missing))
    return max(0.0, base - penalty), components, missing


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('services')
    p.add_argument('--constraints', required=True)
    args = p.parse_args()
    services = json.loads(Path(args.services).read_text(encoding='utf-8'))
    constraints = json.loads(Path(args.constraints).read_text(encoding='utf-8'))
    weights = dict(DEFAULT_WEIGHTS)
    weights.update(constraints.get('weights', {}))
    viable = []
    disqualified = []
    for service in services:
        reasons = hard_fail(service, constraints)
        if reasons:
            disqualified.append({'name': service.get('name'), 'reasons': reasons})
            continue
        value, components, missing = score(service, weights)
        viable.append({'name': service.get('name'), 'score': round(value, 4), 'components': components, 'missing': missing})
    viable.sort(key=lambda x: (-x['score'], str(x['name']).lower()))
    print(json.dumps({'viable': viable, 'disqualified': disqualified, 'weights': weights}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
