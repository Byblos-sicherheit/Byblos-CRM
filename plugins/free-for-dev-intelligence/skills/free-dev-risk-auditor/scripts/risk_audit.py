#!/usr/bin/env python3
"""Audit explicitly supplied free-tier facts using a deterministic risk taxonomy."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def finding(severity: str, code: str, message: str, action: str) -> dict:
    return {"severity": severity, "code": code, "message": message, "action": action}


def age_days(value: str, today: date) -> int | None:
    try:
        return (today - datetime.strptime(value, "%Y-%m-%d").date()).days
    except (ValueError, TypeError):
        return None


def audit_component(component: dict, context: dict, today: date) -> dict:
    name = component.get("name")
    if not name:
        raise ValueError("every component must have a name")
    findings = []
    commercial = context.get("use") == "commercial"
    sensitivity = context.get("data_sensitivity", "normal")
    stage = context.get("stage", "prototype")
    required_region = context.get("required_region")

    if component.get("trial_only") is True:
        findings.append(finding("critical", "trial-not-tier", "The offer is a trial, not a durable free tier.", "Reject it as a permanent free-tier component."))

    commercial_use = component.get("commercial_use", "unknown")
    if commercial and commercial_use == "restricted":
        findings.append(finding("critical", "commercial-restricted", "Commercial use is explicitly restricted.", "Replace the service or obtain a paid/commercial entitlement."))
    elif commercial and commercial_use == "unknown":
        findings.append(finding("high", "commercial-unknown", "Commercial-use eligibility is not verified.", "Verify the provider terms before use."))

    if component.get("tls_included") is False:
        findings.append(finding("critical", "tls-not-included", "TLS is not included in the stated tier.", "Reject the service for internet-facing production use."))
    elif component.get("tls_included") is None:
        findings.append(finding("medium", "tls-unknown", "TLS availability is unknown.", "Verify TLS and custom-domain behavior."))

    card = component.get("card_required") is True
    overage = component.get("auto_overage") is True
    hard_cap = component.get("hard_spend_cap")
    if card and overage and hard_cap is False:
        findings.append(finding("high", "unbounded-overage", "A card, automatic overage, and no hard spend cap create direct billing exposure.", "Enable provider budgets or replace with a hard-capped service."))
    elif overage and hard_cap is None:
        findings.append(finding("high", "overage-cap-unknown", "Automatic overage is enabled but hard-cap behavior is unknown.", "Verify billing controls before deployment."))
    elif card:
        findings.append(finding("low", "card-required", "A payment card is required.", "Document the reason and confirm no automatic paid conversion."))

    if component.get("egress_metered") is True:
        findings.append(finding("medium", "egress-metered", "Outbound data transfer is metered or may exceed the free quota.", "Estimate cross-provider and user-facing egress."))

    inactivity = component.get("inactivity_action", "unknown")
    if inactivity in {"delete", "reclaim"}:
        findings.append(finding("high", "inactivity-data-loss", f"Inactivity may {inactivity} the resource.", "Add backups, keepalive policy if permitted, and a recovery plan."))
    elif inactivity in {"sleep", "suspend", "pause"}:
        findings.append(finding("medium", "inactivity-downtime", f"Inactivity may {inactivity} the resource.", "Accept cold starts explicitly or choose an always-on alternative."))
    elif inactivity == "unknown":
        findings.append(finding("medium", "inactivity-unknown", "Inactivity behavior is unknown.", "Verify sleep, suspension, deletion, and reclamation rules."))

    data_region = component.get("data_region")
    if required_region and (not data_region or required_region.lower() not in str(data_region).lower()):
        findings.append(finding("high", "region-mismatch", "The required data region is not confirmed for this tier.", "Verify plan-specific data residency or replace the service."))
    elif sensitivity in {"high", "regulated"} and not data_region:
        findings.append(finding("high", "region-unknown", "Data region is unknown for sensitive data.", "Verify residency and subprocessors."))

    backup = component.get("backup", "unknown")
    if sensitivity in {"high", "regulated"} and backup in {"none", "unknown", "paid"}:
        sev = "critical" if backup == "none" else "high"
        findings.append(finding(sev, "backup-insufficient", f"Backup status is {backup} for sensitive data.", "Implement an independently tested backup and restore path."))
    elif backup in {"none", "unknown"}:
        findings.append(finding("medium", "backup-unclear", f"Backup status is {backup}.", "Document export, backup, and restore procedures."))

    export = component.get("export", "unknown")
    if export == "none":
        findings.append(finding("high", "no-export", "No data export path is available.", "Reject for persistent business data or add an independent copy."))
    elif export == "proprietary":
        findings.append(finding("medium", "proprietary-export", "Export uses a proprietary format or API.", "Test migration before adoption."))
    elif export == "unknown":
        findings.append(finding("medium", "export-unknown", "Data export is unknown.", "Verify format, frequency, and completeness."))

    support = component.get("support", "unknown")
    if stage == "production" and support in {"community", "none", "unknown"}:
        findings.append(finding("high", "support-insufficient", f"Support level is {support} for a production component.", "Accept the operational risk explicitly or use a supported plan."))

    verified_on = component.get("verified_on")
    days = age_days(verified_on, today) if verified_on else None
    if days is None:
        findings.append(finding("high", "verification-date-missing", "The verification date is missing or invalid.", "Re-verify current provider terms and record YYYY-MM-DD."))
    elif days > 90:
        findings.append(finding("high", "verification-stale", f"Provider terms were verified {days} days ago.", "Re-verify all decision-critical limits."))
    elif days > 30:
        findings.append(finding("medium", "verification-aging", f"Provider terms were verified {days} days ago.", "Re-check before a current purchasing or production decision."))

    for unknown in component.get("unknowns", []):
        findings.append(finding("high", "explicit-unknown", str(unknown), "Resolve this unknown before production use."))

    findings.sort(key=lambda item: (-SEVERITY_ORDER[item["severity"]], item["code"]))
    overall = "low" if not findings else max(findings, key=lambda item: SEVERITY_ORDER[item["severity"]])["severity"]
    return {"name": name, "overall_severity": overall, "findings": findings}


def audit(payload: dict, today: date) -> dict:
    context = payload.get("context", {})
    components = payload.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("components must be a non-empty list")
    audited = [audit_component(component, context, today) for component in components]
    overall = max(audited, key=lambda item: SEVERITY_ORDER[item["overall_severity"]])["overall_severity"]
    counts = {severity: 0 for severity in SEVERITY_ORDER}
    for component in audited:
        for item in component["findings"]:
            counts[item["severity"]] += 1
    return {
        "audit_date": today.isoformat(),
        "overall_severity": overall,
        "finding_counts": counts,
        "components": audited,
        "warning": "The audit evaluates only supplied facts. Missing provider evidence must remain unknown and may increase risk.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit free-tier components from explicit facts")
    parser.add_argument("input_json")
    parser.add_argument("--date", help="Audit date in YYYY-MM-DD; defaults to today")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()
    try:
        today = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
        payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        result = audit(payload, today)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
