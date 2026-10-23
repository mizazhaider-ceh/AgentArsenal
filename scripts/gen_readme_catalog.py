#!/usr/bin/env python3
"""Regenerate the skill-count badge and skill catalog table in README.md.

Reads arsenal-manifest.json, then rewrites the README sections between
<!-- SKILLCOUNT:START --> / <!-- SKILLCOUNT:END --> (shields.io badge with
the live skill count) and <!-- CATALOG:START --> / <!-- CATALOG:END -->
(markdown table grouped by domain, plus a total row).

Idempotent: running it twice produces identical output.
Stdlib only.
"""

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "arsenal-manifest.json"
README = REPO_ROOT / "README.md"

SKILLCOUNT_START = "<!-- SKILLCOUNT:START -->"
SKILLCOUNT_END = "<!-- SKILLCOUNT:END -->"
CATALOG_START = "<!-- CATALOG:START -->"
CATALOG_END = "<!-- CATALOG:END -->"


def load_manifest():
    with open(MANIFEST, encoding="utf-8") as fh:
        data = json.load(fh)
    skills = data.get("skills", [])
    if not skills:
        raise SystemExit("error: arsenal-manifest.json contains no skills")
    return data


def badge_block(count):
    return (
        SKILLCOUNT_START
        + "\n"
        + f"![skills](https://img.shields.io/badge/skills-{count}-blue)"
        + "\n"
        + SKILLCOUNT_END
    )


DOMAIN_BLURB = {
    "ad": "Active Directory attack paths, from enumeration to ticket forging, for authorized internal assessments.",
    "ai-security": "Attacking and defending LLM and AI agent systems: prompt injection, red teaming, guardrails, supply chain.",
    "api": "Testing and reviewing APIs: security testing, gRPC, OpenAPI review, rate limit abuse.",
    "auth": "Breaking and fixing authentication: credential attacks, session handling, WebAuthn.",
    "automotive": "Vehicle security: CAN bus, ECUs, keyless entry, ISO 21434, V2X.",
    "binary": "Reverse engineering and exploitation: pwn basics, ROP, heap, shellcode, Ghidra, angr.",
    "blockchain": "Smart contract audits, DeFi threats, bridge attacks, wallets, on-chain forensics.",
    "bugbounty": "Running a bug bounty workflow end to end, from recon to paid report.",
    "c2": "Command and control fundamentals for authorized red team operations.",
    "ctf": "Capture-the-flag competition skills: pwn, reversing, web, forensics, crypto, and competition playbooks.",
    "cloud": "Cloud attack surface: AWS, Azure, GCP enumeration, IAM privilege escalation, containers, Kubernetes, serverless.",
    "crypto": "Applied cryptography attacks: RSA, padding oracles, hash cracking, TLS analysis.",
    "defensive": "Blue team craft: EDR basics, hardening baselines, phishing defense, ransomware response.",
    "engineering": "Software engineering craft: git, CI/CD, Docker, Kubernetes, secure coding, debugging, performance.",
    "forensics": "Digital forensics: disk, memory, browser, email, mobile, and log forensics.",
    "hardware": "Hardware hacking: UART and JTAG, glitching, side channels, firmware extraction.",
    "ics-scada": "Industrial control systems: Modbus, DNP3, PLCs, SCADA network segmentation.",
    "incident": "Incident response: the IR process, tabletop exercises, crisis communications.",
    "linux": "Linux security: hardening, eBPF security, container hardening.",
    "malware": "Malware analysis: static triage, dynamic sandboxing, packers, YARA rules.",
    "memory": "Agent memory skills: capture, recall, consolidation, hygiene, and state.",
    "mobile": "Mobile security: Android static and dynamic analysis, iOS basics, hardening.",
    "network": "Network attacks and analysis: Nmap, DNS, SMB, VLAN hopping, wireless, pivoting.",
    "osint": "Open source intelligence: domains, usernames, images, social media, threat intel.",
    "privacy": "Privacy engineering: GDPR, anonymization, differential privacy, impact assessments.",
    "privesc": "Privilege escalation on Linux and Windows, step by step.",
    "recon": "Reconnaissance: passive and active target discovery before you touch anything.",
    "soc": "Security operations: SIEM, Sigma rules, Suricata, threat hunting, DFIR timelines, purple team.",
    "web": "Web application attacks: SQLi, XSS, SSRF, SSTI, JWT, OAuth, GraphQL, plus the full pentest methodology.",
}

DOMAIN_EMOJI = {
    "ad": ":key:", "ai-security": ":robot:", "api": ":electric_plug:",
    "auth": ":lock:", "automotive": ":car:", "binary": ":nut_and_bolt:",
    "blockchain": ":link:", "bugbounty": ":moneybag:", "c2": ":satellite:",
    "ctf": ":triangular_flag_on_post:",
    "cloud": ":cloud:", "crypto": ":closed_lock_with_key:",
    "defensive": ":shield:", "engineering": ":wrench:", "forensics": ":mag:",
    "hardware": ":computer:", "ics-scada": ":factory:",
    "incident": ":rotating_light:", "linux": ":penguin:", "malware": ":bug:",
    "memory": ":floppy_disk:", "mobile": ":iphone:",
    "network": ":globe_with_meridians:", "osint": ":eyes:",
    "privacy": ":bust_in_silhouette:", "privesc": ":arrow_up:",
    "recon": ":telescope:", "soc": ":police_car:", "web": ":spider_web:",
}


def _frontmatter_description(path):
    """Read the trigger description from a SKILL.md frontmatter block,
    including wrapped continuation lines."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not m:
        return ""
    lines = m.group(1).split("\n")
    desc = None
    for line in lines:
        if desc is None:
            if line.startswith("description:"):
                desc = line.split(":", 1)[1].strip()
        else:
            # Continuation lines are indented and contain no new key.
            if line.startswith((" ", "\t")) and ":" not in line.split()[0:1]:
                desc += " " + line.strip()
            else:
                break
    return (desc or "").strip().strip('"')


def _one_liner(desc, n=220):
    d = desc.strip()
    if d.lower().startswith("use when "):
        d = d[len("use when "):]
    if d:
        d = d[0].lower() + d[1:]
    d = re.sub(r"\s+", " ", d)
    d = d.strip('"')
    if len(d) > n:
        # Try to extend forward to the next sentence end (up to 120 extra
        # chars) so list-style descriptions finish their thought.
        fwd = d.find(". ", n - 60, n + 120)
        if fwd > 40:
            d = d[: fwd + 1]
        else:
            cut = d[:n]
            # Prefer ending at a sentence boundary.
            sent = cut.rfind(". ")
            if sent > 40:
                d = cut[: sent + 1]
            else:
                # No sentence boundary: end after the last complete list item.
                d = cut.rsplit(", ", 1)[0]
                # Avoid leaving an unclosed parenthesis behind.
                if d.count("(") > d.count(")"):
                    d = d[: d.rfind("(")].rstrip(" ,;:")
    d = d.rstrip(" ,;:")
    if d and not d.endswith("."):
        d += "."
    return d or "Skill."


def catalog_block(manifest):
    skills = manifest.get("skills", [])
    by_domain = OrderedDict()
    for skill in sorted(skills, key=lambda s: (s["domain"], s["name"])):
        by_domain.setdefault(skill["domain"], []).append(skill)

    lines = [CATALOG_START]
    lines.append(
        f"{len(skills)} skills across {len(by_domain)} domains. "
        "Regenerated from `arsenal-manifest.json` by `scripts/gen_readme_catalog.py`."
    )
    lines.append("")
    lines.append("<details>")
    lines.append(
        f"<summary><strong>Expand the full catalog: {len(skills)} skills, one line each</strong></summary>"
    )
    lines.append("")
    for domain, slist in by_domain.items():
        emoji = DOMAIN_EMOJI.get(domain, ":package:")
        lines.append(f"### {emoji} {domain} ({len(slist)} skills)")
        lines.append("")
        blurb = DOMAIN_BLURB.get(domain, "")
        if blurb:
            lines.append(f"*{blurb}*")
            lines.append("")
        for skill in slist:
            name = skill["name"]
            desc = _frontmatter_description(
                REPO_ROOT / skill["path"] / "SKILL.md"
            )
            lines.append(f"- `{name}`: {_one_liner(desc)}")
        lines.append("")
    lines.append("</details>")
    lines.append("")
    lines.append(CATALOG_END)
    return "\n".join(lines)


def replace_section(text, start, end, replacement):
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end), re.DOTALL
    )
    new_text, n = pattern.subn(replacement, text)
    if n != 1:
        raise SystemExit(
            f"error: expected exactly one {start} ... {end} block, found {n}"
        )
    return new_text


def main():
    manifest = load_manifest()
    skills = manifest.get("skills", [])
    count = len(skills)

    text = README.read_text(encoding="utf-8")
    text = replace_section(text, SKILLCOUNT_START, SKILLCOUNT_END, badge_block(count))
    text = replace_section(text, CATALOG_START, CATALOG_END, catalog_block(manifest))
    README.write_text(text, encoding="utf-8")

    if "\u2014" in text:
        print("warning: README contains an em dash", file=sys.stderr)

    print(f"README updated: {count} skills.")


if __name__ == "__main__":
    main()
