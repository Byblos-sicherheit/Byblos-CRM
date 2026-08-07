"""Free-tier architecture designer — checks topology, failure domains, and boundaries."""
from __future__ import annotations
from typing import Any


def analyze(architecture: dict[str, Any]) -> dict[str, Any]:
    services = architecture.get("services", [])
    edges = architecture.get("edges", [])
    findings: list[dict[str, Any]] = []

    service_names = {s.get("name") for s in services if s.get("name")}

    # Check for missing quota fields
    for svc in services:
        name = svc.get("name", "unknown")
        if not svc.get("region"):
            findings.append({"severity": "warning", "service": name, "issue": "region_unspecified",
                             "detail": "No region declared; cross-region egress charges may apply."})
        if not svc.get("backup") and svc.get("stateful"):
            findings.append({"severity": "warning", "service": name, "issue": "no_backup",
                             "detail": "Stateful service with no backup strategy declared."})
        if svc.get("single_dependency"):
            findings.append({"severity": "info", "service": name, "issue": "single_dependency",
                             "detail": "Service is a single dependency in the architecture."})

    # Check edges for egress risk
    egress_edges = [e for e in edges if e.get("egress_sensitive")]
    for edge in egress_edges:
        findings.append({
            "severity": "warning",
            "edge": f"{edge.get('from')} -> {edge.get('to')}",
            "issue": "egress_sensitive",
            "detail": "Edge marked egress-sensitive; verify free-tier egress allowances.",
        })

    # Identify dangling references
    for edge in edges:
        for endpoint in ("from", "to"):
            ref = edge.get(endpoint)
            if ref and ref not in service_names:
                findings.append({"severity": "error", "edge": str(edge), "issue": "dangling_reference",
                                 "detail": f"Referenced service '{ref}' not declared in services."})

    return {
        "service_count": len(services),
        "edge_count": len(edges),
        "findings": findings,
        "finding_counts": {
            "error": sum(1 for f in findings if f.get("severity") == "error"),
            "warning": sum(1 for f in findings if f.get("severity") == "warning"),
            "info": sum(1 for f in findings if f.get("severity") == "info"),
        },
    }
