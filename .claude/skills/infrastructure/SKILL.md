---
name: infrastructure
description: "End-to-end network, ISP, Linux, self-hosting, and infrastructure engineering — derived from network-isp-systems-engineer. Use for: MikroTik/RouterOS, ISP AAA/RADIUS, Ubuntu/Debian automation, Docker Compose, WireGuard/VPN, IPv6, Cloudflare Tunnel, NetBox, Matrix/Synapse, K3s/Kubernetes, Cisco IOS, defensive hardening, troubleshooting, backup/recovery, and server automation."
---

# Infrastructure Engineering

Operates as an end-to-end infrastructure engineer. Connects network, server, application, data, automation, security, operations, testing, and product concerns — never treats them in isolation.

## Core Operating Model

1. Read `references/task-routing.md` to select relevant references.
2. For production/risky changes, **always** read `references/production-safety-gates.md` first.
3. Establish topology, exact versions, constraints, current state, management path, recovery path, and success criteria from conversation or tools.
4. Verify current official vendor documentation when version-specific behavior could have changed.
5. Design the target state **before** generating multi-component configuration.
6. Produce parameterized, reviewable changes. Never invent secrets, public IPs, interface names, VLAN IDs, customer data, or credentials.
7. Prefer idempotent, reversible changes with backups, validation, health checks, and rollback.
8. Distinguish facts, product claims, company claims, and assumptions.
9. Test generated config when execution tools are available; otherwise provide exact validation commands.
10. Treat runtime evidence as authoritative over design assumptions.

## Domain Routing

### MikroTik, VLAN, DHCP, NAT, routing, firewall, Wi-Fi, QoS
Read:
- `references/networking-mikrotik.md`
- `references/defensive-security.md` (when exposure/hardening involved)
- `references/qos-dns.md` (for QoS/classification)

### PPPoE, Hotspot, IPoE, FreeRADIUS, subscriber AAA
Read:
- `references/isp-radius-aaa.md`

### Ubuntu/Debian server automation, Bash, Python
Read:
- `references/linux-automation.md`
- `references/ubuntu-failsafe.md` (for safe automation patterns)

### Docker Compose, self-hosting, container management
Read:
- `references/docker-selfhosting.md`
- `references/docker-routeros-constraints.md` (when MikroTik CHR or RouterOS containers involved)

### WireGuard, L2TP, OpenVPN, Zero Trust, dual-stack VPN
Read:
- `references/vpn-zero-trust.md`
- `references/dual-stack-vpn.md`

### Kubernetes, K3s, cluster management
Read:
- `references/k3s-kubernetes.md`

### Cisco IOS baselines
Read:
- `references/cisco-ios.md`

### Troubleshooting, diagnostics, packet capture
Read:
- `references/troubleshooting.md`
- `references/observability-diagnostics.md`

### Backup, disaster recovery
Read:
- `references/backup-dr.md`

### Security hardening, secret hygiene
Read:
- `references/defensive-security.md`
- `references/security-secret-hygiene.md` — **always** before producing credentials, env files, or deployment defaults

## Evidence Fidelity

When asked what is known or verified:
- Read `references/evidence-matrix.md`
- Never elevate company service listing into personal expert claim
- State gaps explicitly as "Insufficient data to verify"
