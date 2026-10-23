#!/usr/bin/env python3
"""AgentArsenal skill scorer (stdlib only).

Scores each skill 0-100 and writes scores.json at the repo root:
{"<name>": {"score": N, "breakdown": {...}}}, keys sorted.
Handles zero skills gracefully (writes {} and exits 0).
"""

import json
import os
import re
import sys
from datetime import date, datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import validate

OUT_PATH = os.path.join(validate.REPO_ROOT, "scores.json")

VERSION_RE = re.compile(r"^[0-9][A-Za-z0-9._+\-]*$")
NON_VERSIONS = {"latest", "unknown", "n/a", "none", "tbd", ""}

# Distinctive technique/tool terms counted toward trigger quality,
# in addition to the tool names listed in frontmatter.
GENERIC_TERMS = {
    "att&ck", "mitre", "cwe", "owasp", "nmap", "masscan", "burpsuite",
    "metasploit", "msfconsole", "wireshark", "tshark", "sqlmap", "hashcat",
    "gobuster", "enum4linux", "bloodhound", "mimikatz", "powershell",
    "openssl", "kerberos", "oauth", "privilege escalation", "brute force",
}


def _section_text(body, heading):
    """Return the markdown text under `heading` up to the next ## heading."""
    lines = body.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            start = i + 1
            break
    if start is None:
        return ""
    collected = []
    for line in lines[start:]:
        if line.strip().startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def _score_skill(name, path):
    breakdown = {"depth": 0, "freshness": 0, "trigger": 0,
                 "tooling": 0, "edge": 0}
    try:
        with open(path, encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError:
        return 0, breakdown

    fm_lines, body, fm_err = validate.split_frontmatter(text)
    data = {}
    if not fm_err:
        data, _ = validate.parse_frontmatter_block(fm_lines)

    # Depth (40): required sections 15, sane body length 15, code blocks 10.
    body_lines = body.splitlines()
    sections = sum(1 for h in validate.REQUIRED_HEADINGS
                   if any(line.strip() == h for line in body_lines))
    depth = sections * 5
    body_len = len(body)
    if body_len >= 2000:
        depth += 15
    elif body_len >= 800:
        depth += 10
    elif body_len >= 300:
        depth += 5
    blocks = body.count("```") // 2
    if blocks >= 2:
        depth += 10
    elif blocks == 1:
        depth += 5
    breakdown["depth"] = min(40, depth)

    # Freshness (20): full marks within 90 days, linear decay to 0 at 365.
    fresh = 0
    last_verified = data.get("last_verified")
    if isinstance(last_verified, str):
        try:
            verified = datetime.strptime(last_verified, "%Y-%m-%d").date()
            age_days = (date.today() - verified).days
            if age_days < 0:
                fresh = 0
            elif age_days <= 90:
                fresh = 20
            else:
                fresh = round(20 * max(0.0, 1.0 - (age_days - 90) / 275.0))
        except ValueError:
            fresh = 0
    breakdown["freshness"] = fresh

    # Trigger quality (20): length 5, "use when" 10, 2+ tool/technique names 5.
    trig = 0
    desc = data.get("description")
    if isinstance(desc, str):
        low = desc.lower()
        if 80 <= len(desc) <= 1500:
            trig += 5
        if "use when" in low:
            trig += 10
        terms = set(GENERIC_TERMS)
        tools = data.get("tools")
        if isinstance(tools, list):
            for tool in tools:
                tname = tool.get("name") if isinstance(tool, dict) else None
                if isinstance(tname, str) and tname.strip():
                    terms.add(tname.strip().lower())
        hits = sum(1 for term in terms if term and term in low)
        if hits >= 2:
            trig += 5
    breakdown["trigger"] = trig

    # Tooling (10): every tool version looks like a version.
    tools = data.get("tools")
    if isinstance(tools, list):
        if not tools:
            breakdown["tooling"] = 5
        else:
            ok = 0
            for tool in tools:
                ver = tool.get("version") if isinstance(tool, dict) else None
                if (isinstance(ver, str) and VERSION_RE.match(ver.strip())
                        and ver.strip().lower() not in NON_VERSIONS):
                    ok += 1
            breakdown["tooling"] = round(10 * ok / len(tools))

    # Edge cases (10): section length, linear up to 400 chars.
    edge_len = len(_section_text(body, "## Edge cases"))
    breakdown["edge"] = round(10 * min(1.0, edge_len / 400.0))

    total = max(0, min(100, sum(breakdown.values())))
    return total, breakdown


def main():
    results = {}
    for _domain, name, path in validate.find_skills():
        score, breakdown = _score_skill(name, path)
        results[name] = {"score": score, "breakdown": breakdown}

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print("Scored %d skill(s). Wrote %s."
          % (len(results), os.path.relpath(OUT_PATH, os.getcwd())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
