#!/usr/bin/env python3
"""AgentArsenal scorer (stdlib only).

Scores each skill, agent, and brain 0-100 and writes scores.json at the
repo root:

    {"skills": {name: {"score": N, "breakdown": {...}}},
     "agents": {...},
     "brains": {...}}

keys sorted. Handles zero artifacts gracefully (writes empty maps and
exits 0). Quality gate for every artifact kind: 70.
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

GATE = 70

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


def _trigger_score(desc, extra_terms=None):
    """Score a trigger-dense description 0-20.

    Length 5, "use when" 10, 2+ distinctive tool/technique terms 5.
    """
    trig = 0
    if not isinstance(desc, str):
        return trig
    low = desc.lower()
    if 80 <= len(desc) <= 1500:
        trig += 5
    if "use when" in low:
        trig += 10
    terms = set(GENERIC_TERMS)
    if extra_terms:
        terms.update(extra_terms)
    hits = sum(1 for term in terms if term and term in low)
    if hits >= 2:
        trig += 5
    return trig


def _load_frontmatter(path):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError:
        return {}, ""
    fm_lines, body, fm_err = validate.split_frontmatter(text)
    data = {}
    if not fm_err:
        data, _ = validate.parse_frontmatter_block(fm_lines)
    return data, body


def _score_agent(name, path, skill_names, brain_names):
    """Score an agent 0-100.

    Breakdown: trigger 20, bindings 30, constraints 15, escalation 15,
    role 20. Gate: 70.
    """
    breakdown = {"trigger": 0, "bindings": 0, "constraints": 0,
                 "escalation": 0, "role": 0}
    data, _body = _load_frontmatter(path)
    if not data:
        return 0, breakdown

    breakdown["trigger"] = _trigger_score(data.get("description"))

    bound = 0
    skills = data.get("skills")
    if isinstance(skills, list):
        if skills:
            bound += 10
        if skills and all(isinstance(s, str) and s in skill_names
                          for s in skills):
            bound += 5
    brains = data.get("brains")
    if isinstance(brains, list):
        if brains:
            bound += 5
        if brains and all(isinstance(b, str) and b in brain_names
                          for b in brains):
            bound += 5
    if data.get("memory_mode") in ("stateless", "persistent"):
        bound += 5
    breakdown["bindings"] = min(30, bound)

    constraints = data.get("constraints")
    if isinstance(constraints, list):
        items = [c for c in constraints
                 if isinstance(c, str) and c.strip()]
        if len(items) >= 3:
            breakdown["constraints"] = 15
        elif items:
            breakdown["constraints"] = 8

    esc = data.get("escalation")
    if isinstance(esc, str) and esc.strip():
        full = os.path.normpath(os.path.join(validate.REPO_ROOT, esc))
        if os.path.isfile(full):
            breakdown["escalation"] = 15

    role = data.get("role")
    if isinstance(role, str) and role.strip():
        breakdown["role"] = 20 if len(role.strip()) >= 20 else 10

    total = max(0, min(100, sum(breakdown.values())))
    return total, breakdown


def _score_brain(name, path):
    """Score a brain 0-100.

    Breakdown: trigger 30, provides 40, body sections 30. Gate: 70.
    """
    breakdown = {"trigger": 0, "provides": 0, "depth": 0}
    data, body = _load_frontmatter(path)
    if not data:
        return 0, breakdown

    trig = 0
    desc = data.get("description")
    if isinstance(desc, str):
        if 80 <= len(desc) <= 1500:
            trig += 10
        if "use when" in desc.lower():
            trig += 10
        terms = set(GENERIC_TERMS)
        low = desc.lower()
        if sum(1 for t in terms if t and t in low) >= 2:
            trig += 10
    breakdown["trigger"] = trig

    provides = data.get("provides")
    if isinstance(provides, list):
        items = [p for p in provides if isinstance(p, str) and p.strip()]
        if len(items) >= 5:
            breakdown["provides"] = 40
        elif len(items) >= 3:
            breakdown["provides"] = 30
        elif items:
            breakdown["provides"] = 15

    headings = sum(1 for line in body.splitlines()
                   if line.strip().startswith("## "))
    if headings >= 5:
        breakdown["depth"] = 30
    elif headings >= 3:
        breakdown["depth"] = 20
    elif headings >= 1:
        breakdown["depth"] = 10

    total = max(0, min(100, sum(breakdown.values())))
    return total, breakdown


def main():
    skill_results = {}
    for _domain, name, path, _parent in validate.find_skills():
        score, breakdown = _score_skill(name, path)
        skill_results[name] = {"score": score, "breakdown": breakdown}

    skill_names = set(skill_results)
    brain_names = set()
    brain_results = {}
    for name, path in validate.find_brains():
        score, breakdown = _score_brain(name, path)
        brain_results[name] = {"score": score, "breakdown": breakdown}
        brain_names.add(name)

    agent_results = {}
    for name, path in validate.find_agents():
        score, breakdown = _score_agent(name, path, skill_names, brain_names)
        agent_results[name] = {"score": score, "breakdown": breakdown}

    results = {
        "skills": dict(sorted(skill_results.items())),
        "agents": dict(sorted(agent_results.items())),
        "brains": dict(sorted(brain_results.items())),
    }
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print("Scored %d skill(s), %d agent(s), %d brain(s). Wrote %s."
          % (len(skill_results), len(agent_results), len(brain_results),
             os.path.relpath(OUT_PATH, os.getcwd())))
    below = [(kind, name, info["score"])
             for kind, group in (("skill", skill_results),
                                 ("agent", agent_results),
                                 ("brain", brain_results))
             for name, info in group.items()
             if info["score"] < GATE]
    for kind, name, score in sorted(below):
        print("below gate (%d): %s '%s'" % (GATE, kind, name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
