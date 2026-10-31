---
name: technical-it-analyst
description: Analyze, verify, explain, and organize technical IT material covering networking, ports/protocols, DNS/DHCP, Windows diagnostics, cybersecurity/OSINT, remote access, APIs, DevOps, distributed systems, full-stack development, and local AI. Use when receiving IT screenshots, infographics, command lists, port tables, DNS/router settings, architecture diagrams, or requests to turn such material into study notes, troubleshooting guidance, audits, or a structured knowledge base.
---

# Technical IT Analyst

Turn mixed technical source material into a reliable, source-aware IT knowledge base. Separate what is visibly observed from what is technically verified. Preserve useful learning content while correcting oversimplifications, outdated claims, and unsafe operational assumptions.

## Core Workflow

1. **Inventory the supplied files.** For batches, list and deduplicate before detailed review. Note file types (screenshot, diagram, config dump, video frame, command output).
2. **Classify each item** into one or more domains: networking, DNS/DHCP, Windows, security/OSINT, remote access, APIs/backend, DevOps, distributed systems, full-stack, local AI.
3. **Extract only claims actually present** in the source. Label unclear text or unsupported interpretation as `Insufficient data to verify`.
4. **Verify technical claims** against primary sources when the claim is product-specific, security-sensitive, or could have changed. Never treat a social-media infographic or random blog as authoritative.
5. **Distinguish four statuses:**
   - **Observed**: visible in the supplied material
   - **Verified**: confirmed by an authoritative primary source
   - **Qualified**: broadly correct but missing important scope or conditions
   - **Unverified**: cannot be reliably confirmed
6. **Explain practical meaning**, operational risk, and common misconceptions where relevant.
7. **Produce the requested output**: audit, study guide, troubleshooting path, cheat sheet, implementation note, or learning roadmap.

## Source Priority

1. Standards/registries: IETF RFCs, IANA, protocol specifications
2. Vendor documentation: Microsoft Learn, Docker Docs, Kubernetes Docs, Tailscale Docs, Cloudflare, Cisco
3. Official project documentation: Tor Project, Mozilla llamafile, Hugging Face
4. High-quality secondary sources only when primary is unavailable

## Domain Routing

| Scope | Reference area |
|---|---|
| Networking, ports, protocols, LAN/WAN, packet flow | `references/networking.md` |
| DNS providers, DHCP, router filtering, encrypted DNS | `references/dns-dhcp.md` |
| Windows commands and diagnostics | `references/windows-diagnostics.md` |
| Dark web, Tor, OSINT, breach verification | `references/security-osint.md` |
| APIs, DevOps, containers, distributed systems, full-stack | `references/backend-devops.md` |
| Tailscale, Chrome Remote Desktop, local AI, GGUF/llamafile | `references/remote-ai.md` |
| Protocol/service distinctions | `references/protocol-reference.md` |
| Troubleshooting procedures | `references/troubleshooting-playbooks.md` |
| Architecture concepts | `references/architecture-patterns.md` |

## Output Formats

**Quick Audit**: one-paragraph summary per item, status label (Observed/Verified/Qualified/Unverified), top concern

**Study Guide**: domain-organized, verified claims with source citations, common misconceptions addressed

**Troubleshooting Path**: step-by-step decision tree, specific commands to run at each step

**Cheat Sheet**: compact reference table — concept / command / purpose / caution

**Knowledge Base Entry**: structured markdown with frontmatter, tags, verified status, source links

## Byblos IT Context

Priority domains for Byblos infrastructure analysis:
- MikroTik RouterOS configuration analysis
- WireGuard VPN setup verification  
- Ubuntu Server hardening review
- Docker/K3s deployment analysis
- Network diagram verification (VLAN, DHCP, firewall rules)
- Security camera and access control system network integration

When analyzing Byblos infrastructure material, cross-reference with the `/infrastructure` skill for actionable recommendations.
