"""Free-tier cost estimator — analyzes quota headroom and overage cost."""
from __future__ import annotations
from typing import Any


def analyze_dimension(d: dict[str, Any]) -> dict[str, Any]:
    limit = d.get("limit")
    usage = d.get("usage")
    paid_rate = d.get("paid_rate")
    name = d.get("name", "unknown")

    utilization = None
    headroom = None
    overage = 0
    estimated_overage_cost = None
    paid_rate_known = paid_rate is not None

    if limit is not None and usage is not None:
        try:
            lim = float(limit)
            use = float(usage)
            utilization = round(use / lim, 4) if lim > 0 else None
            headroom = round(lim - use, 4)
            overage = max(0.0, round(use - lim, 4))
        except (TypeError, ValueError):
            pass

    if overage and paid_rate is not None:
        try:
            estimated_overage_cost = round(overage * float(paid_rate), 6)
        except (TypeError, ValueError):
            pass

    return {
        "name": name,
        "limit": limit,
        "usage": usage,
        "unit": d.get("unit"),
        "utilization": utilization,
        "headroom": headroom,
        "overage": overage,
        "paid_rate": paid_rate,
        "paid_rate_known": paid_rate_known,
        "estimated_overage_cost": estimated_overage_cost,
        "evidence_status": d.get("evidence_status", "catalog-claim"),
    }
