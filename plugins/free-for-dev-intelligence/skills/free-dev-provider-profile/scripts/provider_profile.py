#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from collections import defaultdict
from pathlib import Path

RECOMMENDED = ["free_tier","trial_only","card_required","commercial_use","free_limits","overage_behavior","regions","dpa","subprocessors","data_residency","inactivity_policy","data_deletion","backup","sla","export","support"]

def canonical(v):
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(",",":"))

def build(data: dict) -> dict:
    claims = data.get("claims") or []
    by = defaultdict(list)
    invalid = []
    for i,c in enumerate(claims):
        if not isinstance(c,dict) or not c.get("field"):
            invalid.append(i); continue
        by[c["field"]].append(c)
    fields = {}
    conflicts = []
    for field, items in sorted(by.items()):
        vals = {canonical(x.get("value")) for x in items}
        status = "conflict" if len(vals)>1 else "evidenced"
        if status=="conflict": conflicts.append(field)
        fields[field] = {"status":status,"value":None if status=="conflict" else items[-1].get("value"),"evidence":items}
    covered = sum(1 for f in RECOMMENDED if f in fields and fields[f]["status"]=="evidenced")
    missing = [f for f in RECOMMENDED if f not in fields]
    return {
        "provider": data.get("provider"), "service": data.get("service"),
        "evidence_coverage_percent": round(100*covered/len(RECOMMENDED),1),
        "coverage_interpretation": "documentation coverage only; not a provider quality or compliance score",
        "fields": fields, "conflicts": conflicts, "missing_recommended_fields": missing,
        "invalid_claim_indexes": invalid,
        "decision_status": "conflict" if conflicts else ("incomplete" if missing else "evidence-complete")
    }

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("input"); p.add_argument("-o","--output"); a=p.parse_args()
    out=build(json.loads(Path(a.input).read_text(encoding="utf-8")))
    text=json.dumps(out,indent=2,ensure_ascii=False)+"\n"
    if a.output: Path(a.output).write_text(text,encoding="utf-8")
    else: print(text,end="")
    return 0
if __name__=="__main__": raise SystemExit(main())
