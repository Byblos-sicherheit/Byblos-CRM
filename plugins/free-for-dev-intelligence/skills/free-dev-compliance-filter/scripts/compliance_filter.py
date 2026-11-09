"""Free-tier compliance filter — evaluates services against boolean requirements."""
from __future__ import annotations
from typing import Any


_ALIASES: dict[str, list[str]] = {
    "eu_region": ["eu_region", "eu", "gdpr_region", "europe"],
    "dpa": ["dpa", "data_processing_agreement", "gdpr_dpa"],
    "no_card": ["no_card", "no_credit_card", "card_not_required", "no_cc"],
    "commercial": ["commercial", "commercial_use", "commercial_ok"],
    "open_source": ["open_source", "oss", "foss"],
    "soc2": ["soc2", "soc_2", "soc2_type2"],
    "iso27001": ["iso27001", "iso_27001"],
}


def _lookup(service: dict[str, Any], requirement: str) -> bool | None:
    keys = _ALIASES.get(requirement, [requirement])
    for k in keys:
        val = service.get(k)
        if val is not None:
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in {"true", "yes", "1"}
    return None


def evaluate(service: dict[str, Any], required: list[str], unknown_policy: str) -> dict[str, Any]:
    name = service.get("name", "unknown")
    passed: list[str] = []
    failed: list[str] = []
    flagged: list[str] = []

    for req in required:
        val = _lookup(service, req)
        if val is True:
            passed.append(req)
        elif val is False:
            failed.append(req)
        else:
            if unknown_policy == "fail":
                failed.append(req)
            else:
                flagged.append(req)

    compliant = not failed
    return {
        "name": name,
        "compliant": compliant,
        "passed": passed,
        "failed": failed,
        "flagged": flagged,
        "evidence_status": service.get("evidence_status", "catalog-claim"),
    }
