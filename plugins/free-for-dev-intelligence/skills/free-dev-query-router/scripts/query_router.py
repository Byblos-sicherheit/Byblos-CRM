#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re

INTENT_RULES = {
    "compare": [r"\bcompare\b", r"\bcomparison\b", r"vergleich", r"gegenueber", r"vs\.?\b"],
    "verify": [r"\bverify\b", r"\bconfirm\b", r"pruef", r"verifiz"],
    "stack": [r"\bstack\b", r"tech stack", r"komplette.*architektur", r"full[- ]stack"],
    "architecture": [r"\barchitecture\b", r"architektur", r"topolog", r"failure domain"],
    "cost": [r"\bcost\b", r"\bprice\b", r"kosten", r"budget", r"overage", r"headroom"],
    "compliance": [r"gdpr", r"dsgvo", r"privacy", r"datenschutz", r"dpa", r"eu[- ]only", r"data residency"],
    "risk": [r"\brisk\b", r"risiko", r"lock[- ]?in", r"billing risk", r"ausfall"],
    "alternatives": [r"alternative", r"replacement", r"ersatz", r"substitute"],
    "migrate": [r"migrat", r"umzug", r"wechseln von", r"move from"],
    "diff": [r"\bdiff\b", r"changed? between", r"aenderung", r"version.*vergleich"],
    "watch": [r"\bwatch\b", r"monitor changes", r"ueberwach", r"benachrichtig", r"notify.*change"],
    "profile": [r"provider profile", r"anbieterprofil", r"dossier", r"evidence profile"],
    "export": [r"\bexport\b", r"\bcsv\b", r"\bjson\b", r"\btsv\b", r"markdown file"],
}

CATEGORY_RULES = {
    "database": ["database", "db", "postgres", "postgresql", "mysql", "mongodb", "redis", "sql", "nosql"],
    "hosting": ["hosting", "deploy", "deployment", "paas", "iaas", "serverless", "static site", "web app"],
    "auth": ["auth", "authentication", "identity", "sso", "oauth", "oidc"],
    "monitoring": ["monitoring", "observability", "uptime", "metrics", "apm"],
    "logging": ["logging", "logs", "log management"],
    "email": ["email", "smtp", "transactional mail", "newsletter"],
    "storage": ["storage", "object storage", "file storage", "cdn", "media"],
    "security": ["security", "tls", "ssl", "pki", "secrets", "vulnerability", "waf", "ddos"],
    "ai": [" ai ", "llm", "machine learning", "inference", "model api", "generative ai"],
    "ci-cd": ["ci/cd", " ci ", " cd ", "pipeline", "build minutes", "continuous integration"],
    "api": [" api ", "apis", "webhook", "integration api"],
    "analytics": ["analytics", "product analytics", "traffic analytics", "events"],
    "collaboration": ["collaboration", "project management", "issue tracking", "team chat"],
    "testing": ["testing", "browser test", "load test", "visual regression", " qa "],
}

CONSTRAINT_RULES = {
    "no_card": [r"no (?:credit )?card", r"without (?:a )?(?:credit )?card", r"keine kreditkarte", r"ohne kreditkarte"],
    "eu_region": [r"\beu\b", r"europe", r"europa", r"eu[- ]region"],
    "gdpr_evidence": [r"gdpr", r"dsgvo", r"datenschutz"],
    "commercial_use": [r"commercial", r"kommerziell", r"business use", r"geschaeftlich"],
    "no_trial": [r"no trial", r"not a trial", r"keine testversion", r"kein trial", r"dauerhaft kostenlos"],
    "no_self_hosted": [r"saas only", r"managed only", r"kein self[- ]host", r"not self[- ]hosted"],
}

ROUTES = {
    "discover": ["free-dev-catalog-index", "free-dev-catalog-search", "free-dev-tier-verifier"],
    "compare": ["free-dev-service-comparator", "free-dev-tier-verifier"],
    "verify": ["free-dev-tier-verifier", "free-dev-provider-profile"],
    "stack": ["free-dev-stack-planner", "free-dev-architecture-designer", "free-dev-tier-verifier"],
    "architecture": ["free-dev-architecture-designer", "free-dev-risk-auditor"],
    "cost": ["free-dev-cost-estimator", "free-dev-tier-verifier"],
    "compliance": ["free-dev-compliance-filter", "free-dev-tier-verifier", "free-dev-provider-profile"],
    "risk": ["free-dev-risk-auditor", "free-dev-provider-profile"],
    "alternatives": ["free-dev-alternative-finder", "free-dev-tier-verifier"],
    "migrate": ["free-dev-migration-planner", "free-dev-alternative-finder"],
    "diff": ["free-dev-catalog-diff"],
    "watch": ["free-dev-change-watch", "free-dev-live-sync"],
    "profile": ["free-dev-provider-profile", "free-dev-tier-verifier"],
    "export": ["free-dev-exporter"],
}

def matches(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)

def route(query: str) -> dict:
    t = " " + query.lower() + " "
    intents = [name for name, patterns in INTENT_RULES.items() if matches(t, patterns)]
    if not intents:
        intents = ["discover"]
    categories = []
    for name, terms in CATEGORY_RULES.items():
        if any(term in t for term in terms):
            categories.append(name)
    constraints = [name for name, patterns in CONSTRAINT_RULES.items() if matches(t, patterns)]
    budget = None
    m = re.search(r"(?:budget|max(?:imum)?|under|unter|bis)\s*(?:of\s*)?(?:€|eur\s*)?\s*(\d+(?:[.,]\d+)?)", t, re.I)
    if m:
        budget = float(m.group(1).replace(",", "."))
        constraints.append("max_budget")
    route_order = []
    for intent in intents:
        for skill in ROUTES.get(intent, []):
            if skill not in route_order:
                route_order.append(skill)
    return {
        "query": query,
        "primary_intent": intents[0],
        "secondary_intents": intents[1:],
        "categories": categories,
        "hard_constraints": sorted(set(constraints)),
        "max_budget": budget,
        "routing_sequence": route_order,
        "missing_inputs": ["workload scale"] if any(i in intents for i in ("cost", "stack", "architecture")) else [],
        "routing_confidence": "baseline-rule-match",
    }

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--query", required=True)
    args = p.parse_args()
    print(json.dumps(route(args.query), indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
