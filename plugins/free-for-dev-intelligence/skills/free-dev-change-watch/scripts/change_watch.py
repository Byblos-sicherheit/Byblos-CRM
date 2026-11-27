"""Free-tier change watch — compares normalized provider profiles for decision-relevant changes."""
from __future__ import annotations
from typing import Any


_DECISION_FIELDS = [
    "free_tier_available", "free_limit", "card_required", "eu_region",
    "dpa_available", "commercial_use", "inactivity_policy", "egress_limit",
    "support_level", "regions", "sla", "open_source",
]


def compare(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    all_keys = set(old.keys()) | set(new.keys())

    for key in sorted(all_keys):
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val != new_val:
            decision_relevant = key in _DECISION_FIELDS
            changes.append({
                "field": key,
                "old": old_val,
                "new": new_val,
                "decision_relevant": decision_relevant,
                "change_type": _classify(old_val, new_val),
            })

    decision_changes = [c for c in changes if c["decision_relevant"]]

    return {
        "name": new.get("name") or old.get("name", "unknown"),
        "total_changes": len(changes),
        "decision_relevant_changes": len(decision_changes),
        "changes": changes,
        "decision_changes": decision_changes,
        "material_change": bool(decision_changes),
    }


def _classify(old_val: Any, new_val: Any) -> str:
    if old_val is None:
        return "added"
    if new_val is None:
        return "removed"
    if isinstance(old_val, bool) or isinstance(new_val, bool):
        return "toggled"
    try:
        if float(new_val) > float(old_val):
            return "increased"
        if float(new_val) < float(old_val):
            return "decreased"
    except (TypeError, ValueError):
        pass
    return "changed"
