"""Free-tier stack planner — checks capacity utilization across services."""
from __future__ import annotations
from typing import Any


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    services = payload.get("services", [])
    safety_buffer = float(payload.get("safety_buffer", 0.8))
    results = []

    for svc in services:
        name = svc.get("name", "unknown")
        dimensions = svc.get("dimensions", [])
        dim_results = []
        exhausted = []
        near_limit = []

        for dim in dimensions:
            limit = dim.get("limit")
            usage = dim.get("usage")
            dim_name = dim.get("name", "unknown")
            utilization = None
            status = "unknown"

            if limit is not None and usage is not None:
                try:
                    lim = float(limit)
                    use = float(usage)
                    utilization = round(use / lim, 4) if lim > 0 else None
                    if utilization is not None:
                        if utilization >= 1.0:
                            status = "exhausted"
                            exhausted.append(dim_name)
                        elif utilization >= safety_buffer:
                            status = "near_limit"
                            near_limit.append(dim_name)
                        else:
                            status = "ok"
                except (TypeError, ValueError):
                    pass

            dim_results.append({
                "name": dim_name,
                "utilization": utilization,
                "status": status,
                "unit": dim.get("unit"),
            })

        results.append({
            "name": name,
            "dimensions": dim_results,
            "exhausted": exhausted,
            "near_limit": near_limit,
            "overall_status": "exhausted" if exhausted else ("near_limit" if near_limit else "ok"),
        })

    return {
        "safety_buffer": safety_buffer,
        "services": results,
        "exhausted_services": [r["name"] for r in results if r["overall_status"] == "exhausted"],
        "near_limit_services": [r["name"] for r in results if r["overall_status"] == "near_limit"],
    }
