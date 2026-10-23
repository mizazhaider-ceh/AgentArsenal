#!/usr/bin/env python3
"""AgentArsenal skill spotlight rotator (stdlib only).

Picks the next skill in a curated round-robin list, regenerates
SKILL_OF_THE_WEEK.md at the repo root with a short showcase, and prints
the pick. State lives in scripts/spotlight_state.json so the rotation
survives across runs and machines.

Usage:
    python3 scripts/rotate_spotlight.py

The showcase body is generated from the skill's own frontmatter (name,
domain, description, pinned tools), so it can never drift from the
skill file. The "why it shines" line comes from the curated WHY table
below; edit that table when adding skills to the rotation.
"""

import json
import os
import sys
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import validate

REPO_ROOT = validate.REPO_ROOT
OUT_PATH = os.path.join(REPO_ROOT, "SKILL_OF_THE_WEEK.md")
STATE_PATH = os.path.join(SCRIPT_DIR, "spotlight_state.json")

# Curated rotation, in order. Every entry needs a WHY line below.
SPOTLIGHT_ORDER = [
    "web-sqli",
    "nmap-methodology",
    "bloodhound-methodology",
    "llm-red-teaming",
    "incident-response",
    "ghidra-basics",
    "kubernetes-rbac",
    "jwt-attacks",
]

WHY = {
    "web-sqli": "The deepest single-skill SQL injection coverage in the "
                "arsenal: manual probes, blind extraction, second-order "
                "cases, sqlmap automation, and a defender's view.",
    "nmap-methodology": "The scan-planning backbone behind every recon "
                        "engagement. If you learn one network skill first, "
                        "make it this one.",
    "bloodhound-methodology": "Shows how graph thinking turns raw Active "
                              "Directory data into real attack paths.",
    "llm-red-teaming": "Fresh AI-security coverage: prompt injection, "
                       "guardrail bypass testing, and model extraction, "
                       "all scoped to authorized testing.",
    "incident-response": "The calm voice of the repo. Structured triage, "
                         "containment, and evidence handling for when "
                         "everything is on fire.",
    "ghidra-basics": "A full reverse-engineering starter on an NSA-built, "
                     "free tool. Disassembly to decompilation in one skill.",
    "kubernetes-rbac": "RBAC is where clusters are won or lost. This skill "
                       "drills roles, bindings, and common misconfigurations "
                       "hard.",
    "jwt-attacks": "Compact and practical. Every web tester meets JWTs; "
                   "this skill teaches how they break and how to check them.",
}


def _read_skill(name):
    for domain, sname, path, parent in validate.find_skills():
        if sname == name:
            try:
                with open(path, encoding="utf-8-sig") as fh:
                    text = fh.read()
            except OSError:
                return None
            fm_lines, _body, fm_err = validate.split_frontmatter(text)
            if fm_err:
                return None
            data, _errs = validate.parse_frontmatter_block(fm_lines)
            data["_domain"] = domain
            return data
    return None


def _load_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as fh:
            state = json.load(fh)
        if isinstance(state, dict) and isinstance(state.get("index"), int):
            return state
    except (OSError, ValueError):
        pass
    return {"index": -1, "skill": None, "updated": None}


def _shorten(text, limit=280):
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut + "..."


def render(name, data, week):
    domain = data.get("_domain", "?")
    desc = _shorten(data.get("description", ""))
    tools = data.get("tools") or []
    tool_lines = []
    for tool in tools:
        if isinstance(tool, dict) and tool.get("name"):
            tool_lines.append("- %s %s" % (tool.get("name"),
                                           tool.get("version", "")))
    if not tool_lines:
        tool_lines.append("- (no tools pinned)")
    lines = []
    lines.append("# Skill of the week: %s" % name)
    lines.append("")
    lines.append("Week of %s. Domain: `%s`." % (week, domain))
    lines.append("")
    lines.append("## What it is")
    lines.append("")
    lines.append(desc)
    lines.append("")
    lines.append("## Why it shines")
    lines.append("")
    lines.append(WHY[name])
    lines.append("")
    lines.append("## Pinned tools")
    lines.append("")
    lines.extend(tool_lines)
    lines.append("")
    lines.append("## How to use it")
    lines.append("")
    lines.append("Open `skills/%s/%s/SKILL.md` and follow the Quick Workflow"
                 % (domain, name))
    lines.append("section. Every skill in the rotation is stable, scored,")
    lines.append("and benchmarked; check `scores.json` and `BENCHMARKS.md`")
    lines.append("for its current numbers.")
    lines.append("")
    lines.append("_Spotlight rotates weekly via "
                 "`python3 scripts/rotate_spotlight.py`. Edit SPOTLIGHT_ORDER "
                 "in that script to change the lineup._")
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    del argv
    state = _load_state()
    next_index = (state["index"] + 1) % len(SPOTLIGHT_ORDER)
    name = SPOTLIGHT_ORDER[next_index]
    data = _read_skill(name)
    if data is None:
        print("error: skill '%s' not found in the repo" % name,
              file=sys.stderr)
        return 1
    week = date.today().isoformat()
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(render(name, data, week))
    new_state = {"index": next_index, "skill": name, "updated": week}
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(new_state, fh, indent=2)
        fh.write("\n")
    print("Spotlight rotated to: %s (week of %s)" % (name, week))
    return 0


if __name__ == "__main__":
    sys.exit(main())
