---
name: security-audit
description: Perform structured security audits, penetration test planning, vulnerability assessments, and threat modeling. Covers web app security (OWASP Top 10), network security, API security, infrastructure hardening, and code review for security issues. Use for "audit this code", "find vulnerabilities", "pentest plan", "threat model", "security review", "harden this config", or CTF challenges. Requires clear authorization context — never performs unauthorized testing.
---

# Security Audit

Security work requires authorization. Before any active testing or exploit development: confirm the target is in scope, the tester has written authorization, and the environment is isolated or approved for testing. Never perform active attacks on production systems or systems you do not own.

## 6-Phase Audit Workflow

### Phase 1: Recon
- Define scope: target systems, IP ranges, domains, applications
- Identify technology stack (framework, language, runtime, infra)
- Map attack surface: exposed endpoints, open ports, public APIs, third-party dependencies
- Collect passive intelligence: DNS records, certificate transparency, public code repos, exposed configs

### Phase 2: Hunt
- Execute systematic checks against identified attack surface
- Prioritize by: exploitability × impact × likelihood
- Apply domain-specific attack class checklists (see Domain Routing below)
- Document every finding with: location, observed behavior, expected behavior, reproduction steps

### Phase 3: Validate
- Reproduce every finding before reporting it
- Classify severity: CRITICAL / HIGH / MEDIUM / LOW / INFO
- Determine exploitability: Proven (PoC exists) / Likely / Theoretical
- Eliminate false positives — only confirmed or strongly plausible findings ship

### Phase 4: Report
- Structured finding format:
  - **Title**: one-line description
  - **Severity**: CRITICAL / HIGH / MEDIUM / LOW / INFO
  - **Location**: file, endpoint, or component
  - **Observed**: what actually happens
  - **Expected**: what should happen
  - **Reproduction**: minimal steps to reproduce
  - **Impact**: what an attacker can achieve
  - **Remediation**: specific fix with code example where applicable
- No vague findings: "SQL injection possible" with no location is not a finding

### Phase 5: Structured Output
- Provide findings as a prioritized list, most severe first
- Include executive summary: total findings by severity, top-3 critical risks
- Provide remediation roadmap: sequence fixes by risk reduction per effort

### Phase 6: Independent Verification
- Verify remediations were implemented correctly, not just acknowledged
- Re-test fixed findings to confirm closure
- Update finding status: Open / In Progress / Fixed / Accepted Risk / Won't Fix

## Severity Model

| Severity | Criteria |
|---|---|
| **CRITICAL** | Remote code execution, authentication bypass, data exfiltration of all records, privilege escalation to admin |
| **HIGH** | SQL injection (limited scope), SSRF, insecure direct object reference, stored XSS, broken access control |
| **MEDIUM** | Reflected XSS, CSRF, sensitive data in logs, weak session management, missing security headers |
| **LOW** | Information disclosure, missing rate limiting, verbose error messages, outdated dependencies (no known exploit) |
| **INFO** | Security best practice recommendations with no direct exploitability |

## Domain Routing

Load only references relevant to the audit scope:

| Scope | Attack Classes / References |
|---|---|
| Web application (OWASP) | Injection, XSS, CSRF, IDOR, broken auth, security misconfig, insecure deserialization |
| API security | Auth bypass, mass assignment, excessive data exposure, rate limit bypass, JWT attacks |
| Network / infrastructure | Port scanning, service fingerprinting, TLS configuration, firewall rules, exposed management interfaces |
| Code review | Hardcoded secrets, unsafe deserialization, path traversal, SQL concatenation, command injection |
| Dependency audit | CVE scanning, transitive vulnerabilities, end-of-life components |
| Cloud / container | IAM misconfig, public S3 buckets, exposed metadata endpoints, container escape vectors |
| Authentication systems | Password policy, MFA bypass, session fixation, credential stuffing exposure |

## Byblos CRM Security Priorities

1. **Access control**: multi-tenant data isolation — customer A must never see customer B data
2. **Authentication**: session management, password hashing (Argon2/bcrypt), MFA readiness
3. **API security**: input validation on all endpoints, parameterized queries only
4. **Secrets hygiene**: no credentials in code, env vars via .env (never committed), rotate on breach
5. **Dependency health**: monthly CVE scan of all direct and transitive dependencies
6. **Infrastructure**: SSH key-only login, fail2ban active, UFW/nftables rules audited quarterly

## Evidence Standards

- Only report findings confirmed by reproduction or strong technical analysis
- Label unconfirmed findings as PLAUSIBLE with explicit caveat
- Never invent CVE numbers, version strings, or exploit payloads
- Do not disclose real credentials, real IP addresses, or real customer data in reports
- If a finding cannot be reproduced: state "Insufficient data to verify" — do not report it as confirmed
