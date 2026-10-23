#!/usr/bin/env python3
"""AgentArsenal freshness checker (stdlib only).

Scans every skills/<domain>/<skill>/SKILL.md (including sub-skills) and
raises flags that point a human reviewer at tooling references worth
re-checking:

  FUTURE_TOOL:    the recorded version's release date is AFTER the
                  skill's last_verified date (the version did not exist
                  when the skill was verified; a data-quality smell).
  RETIRED_TOOL:   the recorded version has a known support end date and
                  last_verified is past it.
  AGING_TOOL:     a newer release is known for the tool AND the recorded
                  release is more than 12 months older than last_verified.
  OLD_VERIFICATION: the skill's last_verified date is more than
                  12 months in the past relative to today.

A flag is a hint, not proof of a problem. Languages and runtimes have
long support windows, and a pinned-but-older tool version is often still
correct. Reviewers should treat RETIRED_TOOL and FUTURE_TOOL as high
priority and AGING_TOOL as a suggestion to look at the skill.

Version release dates come from a small built-in table of (tool,
version) pairs verified against public release announcements. Tools NOT
in the table cannot be judged on their version; they are counted in the
report so maintainers can see where the table is thin. The table is
intentionally small and honest about what it does not know. Extend it
in RELEASE_DATES as you verify more releases; each entry carries a
"verified" date (when the fact was checked) so stale table rows are
visible.

Usage:
    python3 scripts/freshness_check.py
    python3 scripts/freshness_check.py --write [path]

With --write, a markdown report is saved (default: freshness-report.md
at the repo root). Stdout always gets the human-readable report.

Exit code is 0 unless --strict is passed and any flag was raised.
"""

import argparse
import os
import re
import sys
from datetime import date, datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import validate

STALE_MONTHS = 12

# Verified (tool, version) -> release info.
# "eol" is the support/security-fix end date when a vendor publishes one.
# "newer" is free text naming a newer known release (used when the exact
# release date of the newer version is not verified yet).
# "verified" is the date the fact was checked against a public source.
RELEASE_DATES = [
    # nmap: 7.98 announced 2025-08-21; 7.96 announced May 2025.
    {"tool": "nmap", "version": "7.98", "released": "2025-08-21",
     "verified": "2026-10-23", "note": "upstream announcement"},
    {"tool": "nmap", "version": "7.96", "released": "2025-05-01",
     "verified": "2026-10-23", "note": "month precision, announcement",
     "newer": "7.98 (2025-08-21)"},
    # Ghidra: 12.1.3 2026-08-18, 12.1.4 2026-09-21, 12.2 2026-10-22.
    {"tool": "ghidra", "version": "12.1.3", "released": "2026-08-18",
     "verified": "2026-10-23", "note": "GitHub releases page",
     "newer": "12.2 (2026-10-22)"},
    {"tool": "ghidra", "version": "12.1.4", "released": "2026-09-21",
     "verified": "2026-10-23", "note": "GitHub releases page",
     "newer": "12.2 (2026-10-22)"},
    {"tool": "ghidra", "version": "12.2", "released": "2026-10-22",
     "verified": "2026-10-23", "note": "GitHub releases page"},
    # Wireshark: 4.4.x branch started 2024-08-28; 4.6.x started 2025-10-08.
    {"tool": "wireshark", "version": "4.4", "released": "2024-08-28",
     "verified": "2026-10-23", "note": "branch first release",
     "newer": "4.6.x branch (2025-10-08)"},
    {"tool": "wireshark", "version": "4.4.9", "released": "2025-08-29",
     "verified": "2026-10-23", "note": "release announcement",
     "newer": "4.6.x branch (2025-10-08)"},
    {"tool": "wireshark", "version": "4.6", "released": "2025-10-08",
     "verified": "2026-10-23", "note": "branch first release"},
    # hashcat 6.2.6: last update 2022-09-02; 7.x line exists since 2025.
    {"tool": "hashcat", "version": "6.2.6", "released": "2022-09-02",
     "verified": "2026-10-23", "note": "upstream download archive",
     "newer": "7.1.x (2025)"},
    # Python: 3.12 2023-10-02 (security fixes to 2028-10),
    # 3.13 2024-10-07 (to 2029-10), 3.14 2025-10-07 (to 2030-10).
    {"tool": "python", "version": "3.12", "released": "2023-10-02",
     "eol": "2028-10-01", "verified": "2026-10-23",
     "note": "python devguide", "newer": "3.14 (2025-10-07)"},
    {"tool": "python", "version": "3.13", "released": "2024-10-07",
     "eol": "2029-10-01", "verified": "2026-10-23",
     "note": "python devguide", "newer": "3.14 (2025-10-07)"},
    {"tool": "python", "version": "3.14", "released": "2025-10-07",
     "eol": "2030-10-01", "verified": "2026-10-23",
     "note": "python devguide"},
    # OpenSSL: 3.4.0 released 2024-10-22, supported to 2026-10-22.
    {"tool": "openssl", "version": "3.4", "released": "2024-10-22",
     "eol": "2026-10-22", "verified": "2026-10-23",
     "note": "openssl-library.org", "newer": "3.5 LTS (2025-04-08)"},
    {"tool": "openssl", "version": "3.5", "released": "2025-04-08",
     "eol": "2030-04-08", "verified": "2026-10-23",
     "note": "openssl-library.org, LTS"},
    # John the Ripper 1.9.0-jumbo-1 announced 2019-05-14 (still the
    # latest stable jumbo release; no newer stable known).
    {"tool": "john the ripper", "version": "1.9.0-jumbo-1",
     "released": "2019-05-14", "verified": "2026-10-23",
     "note": "openwall-announce"},
]

# Burp Suite versions are calendar versions (2026.2 = Feb 2026), per
# PortSwigger's naming convention. This is a documented heuristic, not a
# verified release table entry. It only powers FUTURE_TOOL detection
# (a Burp version dated after the skill's last_verified is impossible).
BURP_RE = re.compile(r"^20\d\d\.(1[0-2]|[1-9])$")


def _parse_date(text):
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _months_between(earlier, later):
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


def _norm_tool(name):
    return " ".join(str(name).strip().lower().split())


def _norm_version(version):
    return str(version).strip().strip('"').strip("'").lower()


def _lookup(tool, version):
    """Return the table row for a (tool, version) pair, or None."""
    t = _norm_tool(tool)
    v = _norm_version(version)
    for row in RELEASE_DATES:
        if row["tool"] == t and row["version"] == v:
            return row
    return None


def _burp_date(tool, version):
    t = _norm_tool(tool)
    v = _norm_version(version)
    if t == "burp suite" and BURP_RE.match(v):
        year, month = v.split(".")
        return date(int(year), int(month), 1)
    return None


def _read_skill(path):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError:
        return None
    fm_lines, _body, fm_err = validate.split_frontmatter(text)
    if fm_err:
        return None
    data, _errs = validate.parse_frontmatter_block(fm_lines)
    return data


def check_all():
    today = date.today()
    flags = []          # (skill, kind, detail)
    unknown_tools = {}  # tool -> count of skills using it
    covered_tool_refs = 0
    total_tool_refs = 0
    skills_seen = 0

    for domain, name, path, parent in validate.find_skills():
        data = _read_skill(path)
        if data is None:
            continue
        skills_seen += 1
        lv = _parse_date(data.get("last_verified") or "")
        if lv is None:
            flags.append((name, "BAD_DATE",
                          "last_verified is missing or not YYYY-MM-DD"))
            continue
        if _months_between(lv, today) > STALE_MONTHS:
            flags.append((name, "OLD_VERIFICATION",
                          "last_verified %s is older than %d months"
                          % (lv.isoformat(), STALE_MONTHS)))
        tools = data.get("tools")
        if not isinstance(tools, list):
            continue
        for tool in tools:
            if not isinstance(tool, dict):
                continue
            tname = tool.get("name")
            tver = tool.get("version")
            if not tname or not tver:
                continue
            total_tool_refs += 1
            row = _lookup(tname, tver)
            if row is not None:
                covered_tool_refs += 1
                released = _parse_date(row["released"])
                eol = _parse_date(row["eol"]) if row.get("eol") else None
                has_newer = bool(row.get("newer")) or any(
                    r["tool"] == row["tool"] and
                    _parse_date(r["released"]) > released
                    for r in RELEASE_DATES)
                if released > lv:
                    flags.append((name, "FUTURE_TOOL",
                                  "%s %s released %s, after last_verified %s"
                                  % (tname, tver, released.isoformat(),
                                     lv.isoformat())))
                elif eol is not None and lv > eol:
                    flags.append((name, "RETIRED_TOOL",
                                  "%s %s support ended %s, before "
                                  "last_verified %s"
                                  % (tname, tver, eol.isoformat(),
                                     lv.isoformat())))
                elif (has_newer and
                      _months_between(released, lv) > STALE_MONTHS):
                    flags.append((name, "AGING_TOOL",
                                  "%s %s released %s; newer known: %s"
                                  % (tname, tver, released.isoformat(),
                                     row.get("newer", "a newer release"))))
                continue
            # Burp calendar-version heuristic: FUTURE_TOOL only.
            bdate = _burp_date(tname, tver)
            if bdate is not None:
                covered_tool_refs += 1
                if bdate > lv:
                    flags.append((name, "FUTURE_TOOL",
                                  "Burp Suite %s is dated %s, after "
                                  "last_verified %s"
                                  % (tver, bdate.isoformat(),
                                     lv.isoformat())))
                continue
            key = _norm_tool(tname)
            unknown_tools[key] = unknown_tools.get(key, 0) + 1

    return {
        "today": today.isoformat(),
        "skills_seen": skills_seen,
        "flags": flags,
        "unknown_tools": unknown_tools,
        "covered_tool_refs": covered_tool_refs,
        "total_tool_refs": total_tool_refs,
    }


def render_report(result):
    lines = []
    lines.append("AgentArsenal freshness report (%s)" % result["today"])
    lines.append("=" * 60)
    lines.append("Skills scanned: %d" % result["skills_seen"])
    lines.append("Tool references scanned: %d" % result["total_tool_refs"])
    if result["total_tool_refs"]:
        pct = 100.0 * result["covered_tool_refs"] / result["total_tool_refs"]
        lines.append("Tool references with a verified release date: %d "
                     "(%.1f%%)" % (result["covered_tool_refs"], pct))
    kinds = ("FUTURE_TOOL", "RETIRED_TOOL", "AGING_TOOL",
             "OLD_VERIFICATION", "BAD_DATE")
    counts = {}
    for _skill, kind, _detail in result["flags"]:
        counts[kind] = counts.get(kind, 0) + 1
    lines.append("Flags raised: %d" % len(result["flags"]))
    for kind in kinds:
        if counts.get(kind):
            lines.append("  %s: %d" % (kind, counts[kind]))
    lines.append("")
    lines.append("What the flags mean (review priority order):")
    lines.append("- FUTURE_TOOL: the pinned version did not exist when the")
    lines.append("  skill was verified. Check the frontmatter for a typo.")
    lines.append("- RETIRED_TOOL: the pinned version's support window closed")
    lines.append("  before the skill was verified. Repin to a supported")
    lines.append("  release and re-verify.")
    lines.append("- AGING_TOOL: a newer release is known and the pinned one")
    lines.append("  is over a year older than the verification date. Low")
    lines.append("  priority for runtimes with long support (Python), higher")
    lines.append("  for fast-moving security tools.")
    lines.append("- OLD_VERIFICATION: the skill has not been re-checked in")
    lines.append("  over a year. Update last_verified after a real review,")
    lines.append("  not by editing the date alone.")
    lines.append("")
    lines.append("Honest limits of this check:")
    lines.append("- The release table is small (currently %d rows) and"
                 % len(RELEASE_DATES))
    lines.append("  covers only the most common tools. Unlisted tools get")
    lines.append("  the last_verified-age check only.")
    lines.append("- A flag is a hint for a human reviewer, not proof the")
    lines.append("  skill content is wrong. Tool commands often stay correct")
    lines.append("  across many versions.")
    lines.append("")
    if result["flags"]:
        order = {k: i for i, k in enumerate(kinds)}
        lines.append("Flagged skills:")
        for skill, kind, detail in sorted(
                result["flags"], key=lambda f: (order.get(f[1], 9), f[0])):
            lines.append("  [%s] %s: %s" % (kind, skill, detail))
    else:
        lines.append("No flags raised. Nothing to report.")
    lines.append("")
    lines.append("Top tools with no release-table entry (extend")
    lines.append("RELEASE_DATES in scripts/freshness_check.py as you verify")
    lines.append("releases):")
    top = sorted(result["unknown_tools"].items(),
                 key=lambda kv: kv[1], reverse=True)[:15]
    for tool, count in top:
        lines.append("  %s: %d tool reference(s)" % (tool, count))
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="AgentArsenal freshness check")
    parser.add_argument("--write", nargs="?", const="freshness-report.md",
                        default=None, metavar="PATH",
                        help="also write the report to PATH "
                             "(default: freshness-report.md)")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 when any flag is raised")
    args = parser.parse_args(argv)

    result = check_all()
    report = render_report(result)
    print(report, end="")

    if args.write:
        out = args.write
        if not os.path.isabs(out):
            out = os.path.join(validate.REPO_ROOT, out)
        parent = os.path.dirname(out)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("# Freshness report (%s)\n\n" % result["today"])
            fh.write(report)
        print("Report written to %s" % os.path.relpath(out,
                                                       validate.REPO_ROOT))

    if args.strict and result["flags"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
