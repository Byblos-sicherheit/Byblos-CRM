#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import traceback
import urllib.request
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WIDGET_URI = "ui://free-dev/comparison-v1.html"
SERVER_NAME = "free-for-dev-intelligence"
SERVER_VERSION = "4.0.0"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26")
UPSTREAM_RAW = "https://raw.githubusercontent.com/ripienaar/free-for-dev/master/README.md"
UPSTREAM_CATALOG = "https://github.com/ripienaar/free-for-dev/blob/master/README.md"


def _load_module(relpath: str, alias: str):
    path = ROOT / relpath
    if not path.exists():
        raise RuntimeError(f"Required module missing: {relpath}")
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {relpath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


CATALOG = _load_module("skills/free-dev-catalog-search/scripts/catalog_tool.py", "ffd_catalog_tool")
ROUTER = _load_module("skills/free-dev-query-router/scripts/query_router.py", "ffd_query_router")
COMPARATOR = _load_module("skills/free-dev-service-comparator/scripts/compare_services.py", "ffd_compare_services")
COST = _load_module("skills/free-dev-cost-estimator/scripts/cost_model.py", "ffd_cost_model")
RISK = _load_module("skills/free-dev-risk-auditor/scripts/risk_audit.py", "ffd_risk_audit")
CAPACITY = _load_module("skills/free-dev-stack-planner/scripts/capacity_check.py", "ffd_capacity_check")
COMPLIANCE = _load_module("skills/free-dev-compliance-filter/scripts/compliance_filter.py", "ffd_compliance_filter")
PROFILE = _load_module("skills/free-dev-provider-profile/scripts/provider_profile.py", "ffd_provider_profile")
ARCH = _load_module("skills/free-dev-architecture-designer/scripts/architecture_plan.py", "ffd_architecture")
MIGRATION = _load_module("skills/free-dev-migration-planner/scripts/migration_plan.py", "ffd_migration")
WATCH = _load_module("skills/free-dev-change-watch/scripts/change_watch.py", "ffd_change_watch")

_CACHE: dict[str, Any] = {"sha": None, "entries": None, "source": None}


def _data_dir() -> Path:
    raw = os.getenv("PLUGIN_DATA") or os.getenv("FREE_DEV_DATA_DIR")
    path = Path(raw).expanduser() if raw else ROOT / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _catalog_path() -> Path:
    explicit = os.getenv("FREE_FOR_DEV_CATALOG_PATH")
    if explicit:
        return Path(explicit).expanduser()
    return _data_dir() / "free-for-dev-README.md"


def _meta_path() -> Path:
    return _data_dir() / "free-for-dev-README.meta.json"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def refresh_catalog(url: str | None = None) -> dict[str, Any]:
    source = url or os.getenv("FREE_FOR_DEV_CATALOG_URL") or UPSTREAM_RAW
    request = urllib.request.Request(source, headers={"User-Agent": f"{SERVER_NAME}/{SERVER_VERSION}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    text = raw.decode("utf-8")
    if "##" not in text or len(text) < 1000:
        raise RuntimeError("Downloaded catalog does not look like the free-for.dev README")
    path = _catalog_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    metadata = {
        "source": source,
        "fetched_at": _now(),
        "sha256": _sha256_text(text),
        "bytes": len(raw),
    }
    _meta_path().write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    _CACHE.update({"sha": None, "entries": None, "source": None})
    return metadata


def load_catalog_text() -> tuple[str, str]:
    path = _catalog_path()
    if path.exists():
        return path.read_text(encoding="utf-8"), str(path)
    try:
        refresh_catalog()
        return path.read_text(encoding="utf-8"), str(path)
    except Exception as exc:
        fixture = ROOT / "tests/fixtures/catalog.md"
        if os.getenv("FREE_DEV_ALLOW_FIXTURE_FALLBACK") == "1" and fixture.exists():
            return fixture.read_text(encoding="utf-8"), str(fixture)
        raise RuntimeError(
            "No catalog snapshot is available. Set FREE_FOR_DEV_CATALOG_PATH or run refresh_catalog on a networked host."
        ) from exc


def catalog_entries() -> tuple[list[Any], dict[str, Any]]:
    text, source = load_catalog_text()
    digest = _sha256_text(text)
    if _CACHE.get("sha") == digest and _CACHE.get("entries") is not None:
        return _CACHE["entries"], {"sha256": digest, "source": source}
    entries = CATALOG.parse_catalog(text)
    _CACHE.update({"sha": digest, "entries": entries, "source": source})
    return entries, {"sha256": digest, "source": source}


def stable_id(entry: Any) -> str:
    payload = "\n".join([str(entry.category), str(entry.name), str(entry.url or "")])
    return "ffd_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def entry_dict(entry: Any, score: float | None = None) -> dict[str, Any]:
    d = asdict(entry) if is_dataclass(entry) else dict(entry)
    d["id"] = stable_id(entry)
    if score is not None:
        d["score"] = score
    d["evidence_status"] = "catalog-claim"
    return d


def find_entry(item_id: str) -> Any:
    entries, _ = catalog_entries()
    for e in entries:
        if stable_id(e) == item_id:
            return e
    raise KeyError(f"Unknown catalog id: {item_id}")


def search_catalog(query: str, *, category: str | None = None, no_card: bool = False,
                   commercial: bool = False, no_trials: bool = False, limit: int = 10) -> list[dict[str, Any]]:
    entries, _ = catalog_entries()
    pairs = CATALOG.search_entries(
        entries,
        query=query,
        category=category,
        exclude_card_required=no_card,
        commercial=commercial,
        exclude_trial_mentions=no_trials,
        limit=max(1, min(int(limit), 50)),
    )
    return [entry_dict(e, score=float(score)) for score, e in pairs]


def compare_services(services: list[dict[str, Any]], constraints: dict[str, Any]) -> dict[str, Any]:
    weights = dict(COMPARATOR.DEFAULT_WEIGHTS)
    weights.update(constraints.get("weights", {}))
    viable, disqualified = [], []
    for service in services:
        reasons = COMPARATOR.hard_fail(service, constraints)
        if reasons:
            disqualified.append({"name": service.get("name"), "reasons": reasons})
            continue
        value, components, missing = COMPARATOR.score(service, weights)
        viable.append({
            "name": service.get("name"),
            "score": round(value, 4),
            "components": components,
            "missing": missing,
        })
    viable.sort(key=lambda x: (-x["score"], str(x["name"]).lower()))
    return {"viable": viable, "disqualified": disqualified, "weights": weights}


def estimate_cost(model: dict[str, Any]) -> dict[str, Any]:
    dimensions = [COST.analyze_dimension(d) for d in model.get("dimensions", [])]
    known_costs = [d["estimated_overage_cost"] for d in dimensions if d["estimated_overage_cost"] is not None]
    exhausted = [d["name"] for d in dimensions if d["headroom"] < 0]
    near = [d["name"] for d in dimensions if d["utilization"] is not None and d["utilization"] >= 0.8 and d["headroom"] >= 0]
    return {
        "service": model.get("service"),
        "currency": model.get("currency"),
        "dimensions": dimensions,
        "exhausted_dimensions": exhausted,
        "near_limit_dimensions": near,
        "known_estimated_overage_total": round(sum(known_costs), 6),
        "complete_cost_estimate": all(d["paid_rate_known"] or d["overage"] == 0 for d in dimensions),
    }


def compliance_filter(services: list[dict[str, Any]], required: list[str], unknown_policy: str) -> dict[str, Any]:
    if unknown_policy not in {"fail", "flag"}:
        raise ValueError("unknown_policy must be fail or flag")
    return {
        "requirements": required,
        "results": [COMPLIANCE.evaluate(s, required, unknown_policy) for s in services],
    }


def catalog_diff(old_markdown: str, new_markdown: str) -> dict[str, Any]:
    old_entries = CATALOG.parse_catalog(old_markdown)
    new_entries = CATALOG.parse_catalog(new_markdown)
    def key(e: Any) -> str:
        return str(e.url or e.name).strip().lower()
    old = {key(e): e for e in old_entries}
    new = {key(e): e for e in new_entries}
    added, removed, changed = [], [], []
    for k in sorted(new.keys() - old.keys()):
        added.append(entry_dict(new[k]))
    for k in sorted(old.keys() - new.keys()):
        removed.append(entry_dict(old[k]))
    for k in sorted(old.keys() & new.keys()):
        before, after = old[k], new[k]
        if before.raw_text != after.raw_text or before.category != after.category:
            changed.append({"id": stable_id(after), "before": entry_dict(before), "after": entry_dict(after)})
    return {"added": added, "removed": removed, "changed": changed,
            "summary": {"added": len(added), "removed": len(removed), "changed": len(changed)}}


def export_records(data: Any, fmt: str) -> dict[str, Any]:
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = next((data[k] for k in ("records", "results", "viable", "services") if isinstance(data.get(k), list)), [data])
    else:
        raise ValueError("data must be an object or array")
    if fmt == "json":
        text = json.dumps(records, indent=2, ensure_ascii=False) + "\n"
        mime = "application/json"
    else:
        fields: list[str] = []
        seen: set[str] = set()
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("tabular exports require object records")
            for field in record:
                if field not in seen:
                    seen.add(field); fields.append(field)
        def cell(v: Any) -> str:
            if isinstance(v, (dict, list)):
                return json.dumps(v, ensure_ascii=False, sort_keys=True)
            return "" if v is None else str(v)
        if fmt == "markdown":
            def esc(v: Any) -> str:
                return cell(v).replace("|", "\\|").replace("\n", " ")
            lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
            lines.extend("| " + " | ".join(esc(r.get(f)) for f in fields) + " |" for r in records)
            text = "\n".join(lines) + "\n"; mime = "text/markdown"
        elif fmt in {"csv", "tsv"}:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=fields, delimiter="," if fmt == "csv" else "\t")
            writer.writeheader()
            for r in records:
                writer.writerow({f: cell(r.get(f)) for f in fields})
            text = buf.getvalue(); mime = "text/csv" if fmt == "csv" else "text/tab-separated-values"
        else:
            raise ValueError("format must be json, csv, tsv, or markdown")
    return {"format": fmt, "mime_type": mime, "text": text, "record_count": len(records)}


def _obj_schema(properties: dict[str, Any] | None = None, required: list[str] | None = None, additional: bool = False) -> dict[str, Any]:
    return {"type": "object", "properties": properties or {}, "required": required or [], "additionalProperties": additional}


def _tool(name: str, title: str, description: str, input_schema: dict[str, Any], handler: Callable[[dict[str, Any]], Any],
          *, read_only: bool = True, open_world: bool = False, meta: dict[str, Any] | None = None, output_schema: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "descriptor": {
            "name": name,
            "title": title,
            "description": description,
            "inputSchema": input_schema,
            "outputSchema": output_schema or {"type": "object", "additionalProperties": True},
            "annotations": {"readOnlyHint": read_only, "destructiveHint": False, "openWorldHint": open_world},
            **({"_meta": meta} if meta else {}),
        },
        "handler": handler,
    }


TOOLS: dict[str, dict[str, Any]] = {}


def register_tools() -> None:
    if TOOLS:
        return
    TOOLS["search"] = _tool(
        "search", "Search free-for.dev", "Use this when the user wants to find relevant free-tier services in the free-for.dev catalog. Use fetch on returned IDs for full catalog text.",
        _obj_schema({"query": {"type": "string", "minLength": 1}}, ["query"]),
        lambda a: {"results": [
            {"id": r["id"], "title": f'{r["name"]} — {r["category"]}', "url": UPSTREAM_CATALOG}
            for r in search_catalog(a["query"], limit=10)
        ]},
        open_world=True,
        output_schema=_obj_schema({"results": {"type": "array", "items": _obj_schema({
            "id": {"type": "string"}, "title": {"type": "string"}, "url": {"type": "string"}}, ["id", "title", "url"]) }}, ["results"]),
    )
    TOOLS["fetch"] = _tool(
        "fetch", "Fetch free-for.dev item", "Use this after search when the user needs the complete catalog entry and its discovery metadata.",
        _obj_schema({"id": {"type": "string", "minLength": 1}}, ["id"]),
        lambda a: (lambda e: {
            "id": stable_id(e), "title": f"{e.name} — {e.category}",
            "text": e.raw_text, "url": UPSTREAM_CATALOG,
            "metadata": {"category": e.category, "provider_url": e.url, "description": e.description, "flags": e.flags,
                         "catalog_line": e.line, "evidence_status": "catalog-claim"}
        })(find_entry(a["id"])),
        open_world=True,
        output_schema=_obj_schema({
            "id": {"type": "string"}, "title": {"type": "string"}, "text": {"type": "string"},
            "url": {"type": "string"}, "metadata": {"type": "object", "additionalProperties": True}},
            ["id", "title", "text", "url"]),
    )
    TOOLS["catalog_search"] = _tool(
        "catalog_search", "Advanced catalog search", "Use this when the user wants filtered free-tier discovery by category, credit-card risk, commercial-use hints, or trial exclusion.",
        _obj_schema({
            "query": {"type": "string"}, "category": {"type": "string"}, "no_card": {"type": "boolean"},
            "commercial": {"type": "boolean"}, "no_trials": {"type": "boolean"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50}}, ["query"]),
        lambda a: {"results": search_catalog(a["query"], category=a.get("category"), no_card=bool(a.get("no_card")),
                                                commercial=bool(a.get("commercial")), no_trials=bool(a.get("no_trials")),
                                                limit=int(a.get("limit", 10)))},
        open_world=True,
    )
    TOOLS["route_query"] = _tool(
        "route_query", "Route free-tier request", "Use this when a natural-language request should be normalized into intent, categories, constraints, and downstream workflow hints.",
        _obj_schema({"query": {"type": "string"}}, ["query"]), lambda a: ROUTER.route(a["query"]),
    )
    TOOLS["provider_profile"] = _tool(
        "provider_profile", "Build provider evidence profile", "Use this when provider claims from official pages need to be normalized, coverage-scored, and checked for conflicts without inventing missing facts.",
        _obj_schema({"profile": {"type": "object", "additionalProperties": True}}, ["profile"]), lambda a: PROFILE.build(a["profile"]),
    )
    TOOLS["compare_services"] = _tool(
        "compare_services", "Compare candidate services", "Use this when the user wants a deterministic ranking after hard constraints have been stated. Hard constraints disqualify candidates before weighted scoring.",
        _obj_schema({"services": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                     "constraints": {"type": "object", "additionalProperties": True}}, ["services", "constraints"]),
        lambda a: compare_services(a["services"], a["constraints"]),
    )
    TOOLS["estimate_cost"] = _tool(
        "estimate_cost", "Estimate free-tier headroom and overage", "Use this when verified free allowances and expected usage are available and the user wants headroom, exhausted dimensions, and known overage cost.",
        _obj_schema({"model": {"type": "object", "additionalProperties": True}}, ["model"]), lambda a: estimate_cost(a["model"]),
    )
    TOOLS["check_capacity"] = _tool(
        "check_capacity", "Check capacity against free limits", "Use this when the user wants usage utilization and safety-buffer status for one or more free-tier components.",
        _obj_schema({"payload": {"type": "object", "additionalProperties": True}}, ["payload"]), lambda a: CAPACITY.analyze(a["payload"]),
    )
    TOOLS["compliance_filter"] = _tool(
        "compliance_filter", "Filter by verified requirements", "Use this when candidates must satisfy explicit boolean requirements such as EU region, DPA availability, commercial use, or no-card policy. Unknowns are never treated as true.",
        _obj_schema({"services": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                     "required": {"type": "array", "items": {"type": "string"}},
                     "unknown_policy": {"type": "string", "enum": ["fail", "flag"]}}, ["services", "required"]),
        lambda a: compliance_filter(a["services"], a["required"], a.get("unknown_policy", "fail")),
    )
    TOOLS["audit_risks"] = _tool(
        "audit_risks", "Audit free-tier operational risks", "Use this when explicit provider facts should be checked for billing, trial, commercial-use, TLS, region, inactivity, backup, egress, support, and evidence-age risks.",
        _obj_schema({"payload": {"type": "object", "additionalProperties": True}, "date": {"type": "string", "format": "date"}}, ["payload"]),
        lambda a: RISK.audit(a["payload"], date.fromisoformat(a["date"]) if a.get("date") else date.today()),
    )
    TOOLS["design_architecture"] = _tool(
        "design_architecture", "Analyze free-tier architecture", "Use this when the user wants structural checks for quotas, stateful backups, regions, cross-region dependencies, egress-sensitive edges, and single dependencies.",
        _obj_schema({"architecture": {"type": "object", "additionalProperties": True}}, ["architecture"]), lambda a: ARCH.analyze(a["architecture"]),
    )
    TOOLS["plan_migration"] = _tool(
        "plan_migration", "Plan provider migration", "Use this when the user wants a gated migration plan between services, including export/import readiness, rollback, downtime, data volume, and cutover phases.",
        _obj_schema({"migration": {"type": "object", "additionalProperties": True}}, ["migration"]), lambda a: MIGRATION.plan(a["migration"]),
    )
    TOOLS["compare_profiles"] = _tool(
        "compare_profiles", "Detect provider-profile changes", "Use this when two normalized provider profiles should be compared for decision-relevant changes such as free limits, card requirement, regions, or free-tier status.",
        _obj_schema({"old": {"type": "object", "additionalProperties": True}, "new": {"type": "object", "additionalProperties": True}}, ["old", "new"]),
        lambda a: WATCH.compare(a["old"], a["new"]),
    )
    TOOLS["compare_catalog_snapshots"] = _tool(
        "compare_catalog_snapshots", "Compare catalog snapshots", "Use this when two free-for.dev Markdown snapshots should be diffed for added, removed, and changed entries. Do not use this to generate upstream pull requests.",
        _obj_schema({"old_markdown": {"type": "string"}, "new_markdown": {"type": "string"}}, ["old_markdown", "new_markdown"]),
        lambda a: catalog_diff(a["old_markdown"], a["new_markdown"]),
    )
    TOOLS["export_results"] = _tool(
        "export_results", "Export structured results", "Use this when analyzed results should be converted to JSON, CSV, TSV, or Markdown text for downstream use.",
        _obj_schema({"data": {}, "format": {"type": "string", "enum": ["json", "csv", "tsv", "markdown"]}}, ["data", "format"]),
        lambda a: export_records(a["data"], a["format"]),
    )
    TOOLS["catalog_status"] = _tool(
        "catalog_status", "Inspect catalog status", "Use this when the user or operator needs the active catalog source, hash, entry count, and cache metadata.",
        _obj_schema(), lambda a: (lambda pair: {
            "entries": len(pair[0]), "sha256": pair[1]["sha256"], "source": pair[1]["source"],
            "upstream": UPSTREAM_CATALOG,
            "metadata": json.loads(_meta_path().read_text(encoding="utf-8")) if _meta_path().exists() else None,
        })(catalog_entries()),
        open_world=True,
    )
    TOOLS["refresh_catalog"] = _tool(
        "refresh_catalog", "Refresh catalog snapshot", "Use this only when the local server should fetch and replace its cached free-for.dev README snapshot from the operator-configured upstream source.",
        _obj_schema(), lambda a: refresh_catalog(), read_only=False, open_world=True,
    )
    TOOLS["render_comparison"] = _tool(
        "render_comparison", "Render service comparison", "Use this only after data tools have produced the final candidate set. Render the prepared comparison once; do not perform discovery or scoring in this tool.",
        _obj_schema({"title": {"type": "string"}, "services": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                     "notes": {"type": "array", "items": {"type": "string"}}}, ["services"]),
        lambda a: {"title": a.get("title") or "Free-tier comparison", "services": a["services"], "notes": a.get("notes", [])},
        meta={"ui": {"resourceUri": WIDGET_URI}, "openai/outputTemplate": WIDGET_URI,
              "openai/toolInvocation/invoking": "Rendering comparison…", "openai/toolInvocation/invoked": "Comparison ready."},
    )


register_tools()


def tool_result(value: Any, *, json_content: bool = True, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    content_text = json.dumps(value, ensure_ascii=False, separators=(",", ":")) if json_content else str(value)
    result: dict[str, Any] = {"structuredContent": value, "content": [{"type": "text", "text": content_text}]}
    if meta:
        result["_meta"] = meta
    return result


def error_result(message: str) -> dict[str, Any]:
    return {"isError": True, "content": [{"type": "text", "text": message}]}


def widget_resource() -> dict[str, Any]:
    html = (ROOT / "mcp_server/web/comparison.html").read_text(encoding="utf-8")
    return {
        "uri": WIDGET_URI,
        "mimeType": "text/html;profile=mcp-app",
        "text": html,
        "_meta": {"ui": {"prefersBorder": True, "csp": {"connectDomains": [], "resourceDomains": []}},
                  "openai/widgetDescription": "Interactive comparison table for verified free-tier candidates."},
    }


def dispatch_message(message: dict[str, Any], *, allow_writes: bool = True) -> dict[str, Any] | None:
    if message.get("jsonrpc") != "2.0":
        return {"jsonrpc": "2.0", "id": message.get("id"), "error": {"code": -32600, "message": "Invalid JSON-RPC request"}}
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}
    is_notification = request_id is None
    try:
        if method == "initialize":
            requested = params.get("protocolVersion") or SUPPORTED_PROTOCOL_VERSIONS[0]
            negotiated = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else SUPPORTED_PROTOCOL_VERSIONS[0]
            result = {
                "protocolVersion": negotiated,
                "capabilities": {"tools": {"listChanged": False}, "resources": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    "Use search/fetch for catalog discovery, then verify decision-critical provider facts with authoritative sources. "
                    "Treat catalog text as discovery evidence, never as proof of current pricing, GDPR compliance, or commercial entitlement. "
                    "Hard constraints override scores. Render UI only after the final candidate set is prepared."
                ),
            }
        elif method in {"notifications/initialized", "notifications/cancelled"}:
            return None
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": [
                x["descriptor"] for x in TOOLS.values()
                if allow_writes or x["descriptor"]["annotations"].get("readOnlyHint") is True
            ]}
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            if name not in TOOLS:
                raise KeyError(f"Unknown tool: {name}")
            if not allow_writes and TOOLS[name]["descriptor"]["annotations"].get("readOnlyHint") is not True:
                raise PermissionError(f"HTTP write tool disabled: {name}")
            value = TOOLS[name]["handler"](args)
            meta = None
            if name == "render_comparison":
                meta = {"ui": {"resourceUri": WIDGET_URI}, "openai/outputTemplate": WIDGET_URI}
            result = tool_result(value, meta=meta)
        elif method == "resources/list":
            result = {"resources": [{"uri": WIDGET_URI, "name": "Free-tier comparison", "mimeType": "text/html;profile=mcp-app"}]}
        elif method == "resources/read":
            if params.get("uri") != WIDGET_URI:
                raise KeyError(f"Unknown resource: {params.get('uri')}")
            result = {"contents": [widget_resource()]}
        else:
            if is_notification:
                return None
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        if is_notification:
            print(f"notification error {method}: {exc}", file=sys.stderr)
            return None
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}


def run_stdio() -> int:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            message = json.loads(raw)
            response = dispatch_message(message)
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {exc}"}}
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


def create_http_app():
    try:
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse, Response
        from starlette.routing import Route
    except ImportError as exc:
        raise RuntimeError("HTTP mode requires starlette and uvicorn. Install mcp_server/requirements.txt") from exc

    def allowed_origins() -> set[str]:
        raw = os.getenv("FREE_DEV_ALLOWED_ORIGINS", "")
        return {item.strip() for item in raw.split(",") if item.strip()}

    def security_error(request: Request, *, require_mcp_headers: bool = False):
        origin = request.headers.get("origin")
        if origin:
            allowed = allowed_origins()
            if origin not in allowed:
                return JSONResponse({"error": "Origin not allowed"}, status_code=403)
        token = os.getenv("FREE_DEV_API_TOKEN")
        if token:
            auth = request.headers.get("authorization", "")
            if auth != f"Bearer {token}":
                return JSONResponse({"error": "Unauthorized"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
        if require_mcp_headers:
            version = request.headers.get("mcp-protocol-version") or "2025-03-26"
            if version not in SUPPORTED_PROTOCOL_VERSIONS:
                return JSONResponse({"error": f"Unsupported MCP protocol version: {version}"}, status_code=400)
            accept = request.headers.get("accept", "")
            if accept and not any(x in accept for x in ("application/json", "*/*")):
                return JSONResponse({"error": "Client must accept application/json"}, status_code=406)
        return None

    async def health(request: Request):
        try:
            entries, info = catalog_entries()
            catalog = {"available": True, "entries": len(entries), **info}
        except Exception as exc:
            catalog = {"available": False, "error": str(exc)}
        return JSONResponse({"status": "ok", "server": SERVER_NAME, "version": SERVER_VERSION, "catalog": catalog})

    async def mcp(request: Request):
        if request.method == "GET":
            return Response(status_code=405, headers={"Allow": "POST"})
        if request.method == "DELETE":
            return Response(status_code=405, headers={"Allow": "POST"})
        denied = security_error(request, require_mcp_headers=True)
        if denied is not None:
            return denied
        try:
            payload = await request.json()
        except Exception as exc:
            return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {exc}"}}, status_code=400)
        allow_writes = os.getenv("FREE_DEV_ENABLE_HTTP_WRITES") == "1"
        response = dispatch_message(payload, allow_writes=allow_writes)
        if response is None:
            return Response(status_code=202)
        negotiated = payload.get("params", {}).get("protocolVersion")
        if negotiated not in SUPPORTED_PROTOCOL_VERSIONS:
            negotiated = SUPPORTED_PROTOCOL_VERSIONS[0]
        return JSONResponse(response, headers={"MCP-Protocol-Version": negotiated})

    async def api_search(request: Request):
        denied = security_error(request)
        if denied is not None:
            return denied
        q = request.query_params.get("q", "").strip()
        if not q:
            return JSONResponse({"error": "q is required"}, status_code=400)
        return JSONResponse({"results": search_catalog(q, limit=min(int(request.query_params.get("limit", "10")), 50))})

    async def api_fetch(request: Request):
        denied = security_error(request)
        if denied is not None:
            return denied
        try:
            e = find_entry(request.path_params["item_id"])
        except KeyError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return JSONResponse(entry_dict(e))

    async def api_tools(request: Request):
        denied = security_error(request)
        if denied is not None:
            return denied
        allow_writes = os.getenv("FREE_DEV_ENABLE_HTTP_WRITES") == "1"
        return JSONResponse({"tools": [
            x["descriptor"] for x in TOOLS.values()
            if allow_writes or x["descriptor"]["annotations"].get("readOnlyHint") is True
        ]})

    return Starlette(routes=[
        Route("/health", health, methods=["GET"]),
        Route("/mcp", mcp, methods=["GET", "POST", "DELETE"]),
        Route("/api/v1/search", api_search, methods=["GET"]),
        Route("/api/v1/catalog/{item_id}", api_fetch, methods=["GET"]),
        Route("/api/v1/tools", api_tools, methods=["GET"]),
    ])


def run_http(host: str, port: int) -> int:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("HTTP mode requires uvicorn. Install mcp_server/requirements.txt") from exc
    uvicorn.run(create_http_app(), host=host, port=port, log_level=os.getenv("LOG_LEVEL", "info"))
    return 0


def self_test() -> int:
    fixture = ROOT / "tests/fixtures/catalog.md"
    os.environ["FREE_FOR_DEV_CATALOG_PATH"] = str(fixture)
    tests = []
    init = dispatch_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
    tests.append(("initialize", bool(init and init.get("result", {}).get("serverInfo", {}).get("name") == SERVER_NAME)))
    listing = dispatch_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tests.append(("tools/list", bool(listing and len(listing["result"]["tools"]) >= 15)))
    search = dispatch_message({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "search", "arguments": {"query": "postgres database"}}})
    tests.append(("search", bool(search and search.get("result", {}).get("structuredContent", {}).get("results"))))
    route = dispatch_message({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "route_query", "arguments": {"query": "Vergleiche kostenlose PostgreSQL Datenbanken ohne Kreditkarte in der EU"}}})
    tests.append(("route_query", bool(route and route.get("result", {}).get("structuredContent"))))
    resource = dispatch_message({"jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {"uri": WIDGET_URI}})
    tests.append(("widget", bool(resource and "mcp-app" in resource["result"]["contents"][0]["mimeType"])))
    failed = [name for name, ok in tests if not ok]
    print(json.dumps({"ok": not failed, "tests": [{"name": n, "ok": ok} for n, ok in tests], "failed": failed}, indent=2))
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Free-for.dev Intelligence MCP server")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stdio", action="store_true", help="Run JSON-RPC MCP over stdin/stdout")
    mode.add_argument("--http", action="store_true", help="Run stateless Streamable HTTP MCP endpoint")
    mode.add_argument("--self-test", action="store_true", help="Run deterministic local smoke tests")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    args = parser.parse_args()
    if args.stdio:
        return run_stdio()
    if args.http:
        return run_http(args.host, args.port)
    return self_test()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        if os.getenv("DEBUG") == "1":
            traceback.print_exc(file=sys.stderr)
        raise SystemExit(1)
