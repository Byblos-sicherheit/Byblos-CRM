#!/usr/bin/env python3
"""Calculate a transparent annual technology-adoption ROI model from user inputs.

The script never supplies benchmark assumptions. Every monetary or improvement value
must be provided by the caller. Input is JSON; output can be JSON or Markdown.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


REQUIRED_NUMBERS = (
    "reclaimed_engineering_hours_annual",
    "loaded_engineering_cost_per_hour",
    "baseline_ci_network_cost_annual",
    "ci_network_avoidance_fraction",
    "governance_hours_reduced_annual",
    "loaded_governance_cost_per_hour",
    "baseline_incident_remediation_cost_annual",
    "modeled_risk_reduction_fraction",
    "annual_license_cost",
    "annual_operating_cost",
    "one_time_implementation_cost",
)


def finite_nonnegative(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return value


def fraction(value: Any, name: str) -> float:
    value = finite_nonnegative(value, name)
    if value > 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return value


def calculate(data: dict[str, Any]) -> dict[str, Any]:
    missing = [name for name in REQUIRED_NUMBERS if name not in data]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))

    values = {name: finite_nonnegative(data[name], name) for name in REQUIRED_NUMBERS}
    values["ci_network_avoidance_fraction"] = fraction(
        data["ci_network_avoidance_fraction"], "ci_network_avoidance_fraction"
    )
    values["modeled_risk_reduction_fraction"] = fraction(
        data["modeled_risk_reduction_fraction"], "modeled_risk_reduction_fraction"
    )

    currency = str(data.get("currency", "EUR")).strip().upper() or "EUR"
    scenario = str(data.get("scenario", "provided-inputs")).strip() or "provided-inputs"

    engineering_value = (
        values["reclaimed_engineering_hours_annual"]
        * values["loaded_engineering_cost_per_hour"]
    )
    infrastructure_value = (
        values["baseline_ci_network_cost_annual"]
        * values["ci_network_avoidance_fraction"]
    )
    governance_value = (
        values["governance_hours_reduced_annual"]
        * values["loaded_governance_cost_per_hour"]
    )
    risk_value = (
        values["baseline_incident_remediation_cost_annual"]
        * values["modeled_risk_reduction_fraction"]
    )
    annual_recurring_cost = values["annual_license_cost"] + values["annual_operating_cost"]
    gross_value = engineering_value + infrastructure_value + governance_value + risk_value
    steady_state_net = gross_value - annual_recurring_cost
    first_year_net = steady_state_net - values["one_time_implementation_cost"]
    monthly_steady_state_net = steady_state_net / 12
    payback_months = None
    if monthly_steady_state_net > 0:
        payback_months = values["one_time_implementation_cost"] / monthly_steady_state_net

    return {
        "scenario": scenario,
        "currency": currency,
        "inputs": values,
        "values": {
            "engineering_value_annual": engineering_value,
            "infrastructure_value_annual": infrastructure_value,
            "governance_value_annual": governance_value,
            "modeled_risk_value_annual": risk_value,
            "annual_gross_value": gross_value,
            "annual_recurring_cost": annual_recurring_cost,
            "steady_state_annual_net_value": steady_state_net,
            "first_year_net_value": first_year_net,
            "payback_months": payback_months,
        },
        "warnings": [
            "Modeled risk value is not realized cash savings unless validated by the measurement method.",
            "The result is only as reliable as the provided baseline, eligibility boundary, and realization assumptions.",
        ],
    }


def money(value: float, currency: str) -> str:
    return f"{value:,.2f} {currency}"


def as_markdown(result: dict[str, Any]) -> str:
    v = result["values"]
    currency = result["currency"]
    payback = "Not calculated (steady-state net value is not positive)"
    if v["payback_months"] is not None:
        payback = f"{v['payback_months']:.1f} months"
    rows = [
        ("Engineering value", v["engineering_value_annual"]),
        ("Infrastructure value", v["infrastructure_value_annual"]),
        ("Governance value", v["governance_value_annual"]),
        ("Modeled risk value", v["modeled_risk_value_annual"]),
        ("Annual gross value", v["annual_gross_value"]),
        ("Annual recurring cost", -v["annual_recurring_cost"]),
        ("Steady-state annual net value", v["steady_state_annual_net_value"]),
        ("First-year net value", v["first_year_net_value"]),
    ]
    lines = [
        f"# ROI Model — {result['scenario']}",
        "",
        "| Component | Annual value |",
        "|---|---:|",
    ]
    lines.extend(f"| {label} | {money(value, currency)} |" for label, value in rows)
    lines.extend(["", f"**Payback:** {payback}", "", "## Warnings"])
    lines.extend(f"- {warning}" for warning in result["warnings"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="JSON input file")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("input JSON must be an object")
        result = calculate(data)
        text = (
            json.dumps(result, indent=2, ensure_ascii=False) + "\n"
            if args.format == "json"
            else as_markdown(result)
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
