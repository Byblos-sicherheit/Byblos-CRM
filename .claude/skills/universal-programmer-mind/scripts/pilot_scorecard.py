#!/usr/bin/env python3
"""Evaluate a pre-weighted pilot scorecard from JSON without changing criteria."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


def number(value: Any, name: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return value


def evaluate(data: dict[str, Any]) -> dict[str, Any]:
    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        raise ValueError("categories must be a non-empty list")

    parsed = []
    weight_total = 0.0
    weighted_points = 0.0
    failed_gates = []
    for index, item in enumerate(categories):
        if not isinstance(item, dict):
            raise ValueError(f"categories[{index}] must be an object")
        name = str(item.get("name", "")).strip()
        if not name:
            raise ValueError(f"categories[{index}].name is required")
        weight = number(item.get("weight"), f"{name}.weight", 0, 100)
        score = number(item.get("score"), f"{name}.score", 0, 5)
        mandatory = bool(item.get("mandatory_gate", False))
        gate_passed = bool(item.get("gate_passed", True))
        if mandatory and not gate_passed:
            failed_gates.append(name)
        weight_total += weight
        weighted_points += weight * score / 5
        parsed.append(
            {
                "name": name,
                "weight": weight,
                "score": score,
                "mandatory_gate": mandatory,
                "gate_passed": gate_passed,
                "evidence": str(item.get("evidence", "")),
            }
        )

    if abs(weight_total - 100.0) > 0.01:
        raise ValueError(f"weights must total 100; received {weight_total:g}")

    threshold = number(data.get("approval_threshold", 70), "approval_threshold", 0, 100)
    recommendation = "approve" if weighted_points >= threshold and not failed_gates else "do-not-approve"
    if failed_gates:
        reason = "one or more mandatory gates failed"
    elif weighted_points < threshold:
        reason = "weighted score is below the predeclared threshold"
    else:
        reason = "threshold met and all mandatory gates passed"

    return {
        "weighted_score_0_to_100": weighted_points,
        "approval_threshold": threshold,
        "failed_mandatory_gates": failed_gates,
        "recommendation": recommendation,
        "reason": reason,
        "categories": parsed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("input JSON must be an object")
        result = evaluate(data)
        text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
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
