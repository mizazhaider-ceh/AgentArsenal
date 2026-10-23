#!/usr/bin/env python3
"""Generate skills.json at the repo root.

npm-based skill managers discover skills through the `skills.json`
manifest at the repo root (the same convention used by
shikanime-labs/skills). Each entry points at the skill's directory
relative to the repo root, so `npx skills add` and friends can list
and install without scanning the whole tree.

Usage: python3 scripts/gen_skills_json.py
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "skills.json"
REPO_URL = "https://github.com/mizazhaider-ceh/AgentArsenal"


def parse_description(path: Path) -> str:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return ""
    for line in m.group(1).splitlines():
        if line.startswith("description:"):
            val = line[len("description:"):].strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                inner = val[1:-1]
                if val[0] == '"':
                    inner = inner.replace('\\"', '"').replace("\\\\", "\\")
                return inner
            return val
    return ""


def main() -> int:
    manifest = json.loads((REPO_ROOT / "arsenal-manifest.json").read_text())
    entries = []
    for skill in manifest["skills"]:
        skill_md = REPO_ROOT / skill["path"] / "SKILL.md"
        entries.append(
            {
                "name": skill["name"],
                "description": parse_description(skill_md),
                "path": skill["path"],
                "version": skill.get("version", ""),
                "domain": skill.get("domain", ""),
                "lifecycle": skill.get("lifecycle", ""),
            }
        )
    doc = {
        "name": "agent-arsenal",
        "repository": REPO_URL,
        "description": (
            "AgentArsenal: 246 versioned agent skills across 28 domains, "
            "covering software engineering craft and offensive security "
            "practice, with machine-enforced quality checks."
        ),
        "skills": entries,
    }
    OUT_PATH.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"wrote {OUT_PATH} ({len(entries)} skills)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
