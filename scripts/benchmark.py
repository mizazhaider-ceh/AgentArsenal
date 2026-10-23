#!/usr/bin/env python3
"""AgentArsenal static benchmark (stdlib only).

Runs a small set of STATIC scenario checks against every skill and
sub-skill SKILL.md and writes BENCHMARKS.md at the repo root with
per-domain pass rates and an overall rate.

These are text-shape checks, not live tests. Nobody ran the tools, nobody
exploited anything, and a passing check says nothing about whether the
skill's commands actually work. The label "static" is on purpose: treat
these numbers as hygiene metrics (does the skill look complete?) and not
as quality proof. Live verification remains a human job recorded in the
frontmatter `last_verified` field.

Scenarios (applied uniformly to every skill):
  S1 primary-tool-mentioned: the body mentions the first tool listed in
     frontmatter `tools:` (case-insensitive). A skill should talk about
     the tool it pins.
  S2 example-command-block: the body contains at least one fenced code
     block (```bash, ```sh, ```python, ...). Skills teach by example.
  S3 trigger-rich-description: the frontmatter description contains at
     least 3 distinct trigger phrases from TRIGGER_PHRASES. Descriptions
     are how agents find skills, so they must carry several hooks.

Usage:
    python3 scripts/benchmark.py

Writes BENCHMARKS.md at the repo root and prints a short summary.
"""

import os
import re
import sys
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import validate

OUT_PATH = os.path.join(validate.REPO_ROOT, "BENCHMARKS.md")

FENCE_RE = re.compile(r"^```", re.MULTILINE)

# Trigger phrases that make a description discoverable. A good
# description mixes "use when" routing with technique and scenario
# language. Distinct phrases count, not total hits.
TRIGGER_PHRASES = [
    "use when",
    "when the",
    "covers",
    "including",
    "such as",
    "for example",
    "step by step",
    "walkthrough",
    "hands-on",
    "technique",
]


def _read_skill(path):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError:
        return None, None
    fm_lines, body, fm_err = validate.split_frontmatter(text)
    if fm_err:
        return None, body
    data, _errs = validate.parse_frontmatter_block(fm_lines)
    return data, body


def _scenario_s1(data, body):
    """Body mentions the first pinned tool."""
    tools = data.get("tools")
    if not isinstance(tools, list) or not tools:
        return None  # not applicable: no tools pinned
    first = tools[0]
    if not isinstance(first, dict) or not first.get("name"):
        return None
    needle = re.sub(r"\s+", "", str(first["name"]).lower())
    haystack = re.sub(r"\s+", "", body.lower())
    return needle in haystack


def _scenario_s2(data, body):
    """Body contains at least one fenced code block."""
    return bool(FENCE_RE.search(body))


def _scenario_s3(data, body):
    """Description carries at least 3 distinct trigger phrases."""
    desc = data.get("description")
    if not isinstance(desc, str):
        return False
    low = desc.lower()
    hits = sum(1 for phrase in TRIGGER_PHRASES if phrase in low)
    return hits >= 3


SCENARIOS = [
    ("S1", "primary tool mentioned in body", _scenario_s1),
    ("S2", "example command block", _scenario_s2),
    ("S3", "description has 3+ trigger phrases", _scenario_s3),
]


def run():
    """Return {(domain, name): {sid: True|False|None}} plus domain map."""
    results = {}
    for domain, name, path, parent in validate.find_skills():
        data, body = _read_skill(path)
        per = {}
        if data is not None and body is not None:
            for sid, _label, fn in SCENARIOS:
                per[sid] = fn(data, body)
        results[(domain, name)] = per
    return results


def _rate(passes, total):
    if not total:
        return None
    return 100.0 * passes / total


def render(results):
    today = date.today().isoformat()
    # per-domain aggregation
    domains = {}
    for (domain, _name), per in sorted(results.items()):
        agg = domains.setdefault(domain, {s[0]: [0, 0] for s in SCENARIOS})
        for sid, _label, _fn in SCENARIOS:
            outcome = per.get(sid)
            if outcome is None:
                continue
            agg[sid][1] += 1
            if outcome:
                agg[sid][0] += 1
    # overall
    totals = {s[0]: [0, 0] for s in SCENARIOS}
    for agg in domains.values():
        for sid in totals:
            totals[sid][0] += agg[sid][0]
            totals[sid][1] += agg[sid][1]
    total_passes = sum(p for p, _t in totals.values())
    total_checks = sum(t for _p, t in totals.values())
    overall = _rate(total_passes, total_checks)

    lines = []
    lines.append("# AgentArsenal static benchmarks")
    lines.append("")
    lines.append("Generated: %s" % today)
    lines.append("Skills checked: %d (top-level skills and sub-skills)"
                 % len(results))
    lines.append("")
    lines.append("> These are STATIC scenario checks on the shape of the")
    lines.append("> markdown files, not live tests. No tool was executed and")
    lines.append("> no technique was verified against a real target. A passing")
    lines.append("> score means the skill looks complete on the page; it says")
    lines.append("> nothing about whether the commands work. Live verification")
    lines.append("> remains a human job, recorded in each skill's")
    lines.append("> `last_verified` frontmatter field.")
    lines.append("")
    lines.append("## Scenarios")
    lines.append("")
    for sid, label, _fn in SCENARIOS:
        lines.append("- **%s**: %s" % (sid, label))
    lines.append("")
    lines.append("Scenario S1 is skipped (not counted) for skills that pin no")
    lines.append("tools in frontmatter. `None` results never count as passes.")
    lines.append("")
    lines.append("## Per-domain pass rates")
    lines.append("")
    header = "| Domain | Skills | " + " | ".join(
        "%s %%" % sid for sid, _l, _f in SCENARIOS) + " | Domain avg |"
    lines.append(header)
    lines.append("|" + " --- |" * (len(SCENARIOS) + 3))
    for domain in sorted(domains):
        agg = domains[domain]
        n_skills = sum(1 for (d, _n) in results if d == domain)
        cells = []
        avgs = []
        for sid, _label, _fn in SCENARIOS:
            r = _rate(*agg[sid])
            if r is None:
                cells.append("n/a")
            else:
                cells.append("%.1f%%" % r)
                avgs.append(r)
        dom_avg = sum(avgs) / len(avgs) if avgs else 0.0
        lines.append("| %s | %d | %s | %.1f%% |"
                     % (domain, n_skills, " | ".join(cells), dom_avg))
    lines.append("")
    lines.append("## Overall")
    lines.append("")
    for sid, label, _fn in SCENARIOS:
        r = _rate(*totals[sid])
        lines.append("- %s (%s): %d/%d pass (%.1f%%)"
                     % (sid, label, totals[sid][0], totals[sid][1],
                        r if r is not None else 0.0))
    lines.append("")
    lines.append("**Overall static pass rate: %.1f%%** (%d of %d scenario "
                 "checks passed)"
                 % (overall if overall is not None else 0.0,
                    total_passes, total_checks))
    lines.append("")
    lines.append("## Reading these numbers honestly")
    lines.append("")
    lines.append("- A domain at 100% is well-formatted, not well-tested.")
    lines.append("- S3 failures are the most actionable: the description is")
    lines.append("  the discovery surface for agents, so add trigger phrases")
    lines.append("  first when fixing a low score.")
    lines.append("- S1 failures usually mean the body never names its pinned")
    lines.append("  tool; add the tool name where the workflow uses it.")
    lines.append("- S2 failures mean the skill has no copy-pasteable example;")
    lines.append("  add at least one fenced command block.")
    lines.append("")
    return "\n".join(lines) + "\n", overall, total_passes, total_checks


def main(argv=None):
    results = run()
    text, overall, passed, total = render(results)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("Benchmarked %d skills and sub-skills." % len(results))
    print("Overall static pass rate: %.1f%% (%d/%d scenario checks)"
          % (overall if overall is not None else 0.0, passed, total))
    print("Wrote %s" % os.path.relpath(OUT_PATH, validate.REPO_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
