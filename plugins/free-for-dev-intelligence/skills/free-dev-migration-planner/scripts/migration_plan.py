"""Free-tier migration planner — generates gated migration plans between services."""
from __future__ import annotations
from typing import Any


_PHASES = ["preparation", "export", "transfer", "import", "verification", "cutover", "rollback_plan"]


def plan(migration: dict[str, Any]) -> dict[str, Any]:
    source = migration.get("source", {})
    target = migration.get("target", {})
    data_volume_gb = migration.get("data_volume_gb")
    downtime_tolerance = migration.get("downtime_tolerance", "unknown")

    source_name = source.get("name", "unknown")
    target_name = target.get("name", "unknown")

    phases: list[dict[str, Any]] = []
    warnings: list[str] = []

    # Check export readiness
    export_ready = source.get("export_support", True)
    import_ready = target.get("import_support", True)

    if not export_ready:
        warnings.append(f"Source '{source_name}' may not support data export; verify manually.")
    if not import_ready:
        warnings.append(f"Target '{target_name}' may not support bulk data import; verify manually.")

    # Estimate downtime
    estimated_downtime_minutes = None
    if data_volume_gb is not None:
        try:
            gb = float(data_volume_gb)
            estimated_downtime_minutes = max(5, round(gb * 2))
        except (TypeError, ValueError):
            pass

    if downtime_tolerance == "zero" and estimated_downtime_minutes:
        warnings.append("Zero downtime requested but non-trivial data volume detected; consider blue-green or CDC approach.")

    for phase in _PHASES:
        phases.append({
            "phase": phase,
            "status": "pending",
            "gate": f"Verify {phase} completion before proceeding.",
            "notes": [],
        })

    return {
        "source": source_name,
        "target": target_name,
        "data_volume_gb": data_volume_gb,
        "downtime_tolerance": downtime_tolerance,
        "estimated_downtime_minutes": estimated_downtime_minutes,
        "export_ready": export_ready,
        "import_ready": import_ready,
        "phases": phases,
        "warnings": warnings,
        "evidence_status": "catalog-claim — verify all migration steps with provider documentation.",
    }
