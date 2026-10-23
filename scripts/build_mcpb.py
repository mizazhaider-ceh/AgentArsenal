#!/usr/bin/env python3
"""Build the AgentArsenal .mcpb Desktop Extension bundle (stdlib only).

Output: dist/agent-arsenal.mcpb

The bundle is a zip archive containing:
  manifest.json        MCPB manifest (spec version 0.4, server type "uv")
  pyproject.toml       dependencies, installed by the host app with uv
  server/main.py       the AgentArsenal MCP server (list_skills,
                       get_skill, search_skills)
  server/data/         arsenal-manifest.json + the full skills/ tree,
                       so the bundle works fully offline
  icon.png             bundle icon (converted from assets/banner.svg
                       when cairosvg is available)

Build:
  python3 scripts/build_mcpb.py

Requires: nothing beyond the stdlib. Network is not needed.
The host app (for example Claude Desktop) must implement MCPB
manifest 0.4 to use the "uv" server type; see docs/distribution/mcpb.md.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSION = "3.0.0"
OUT_FILE = REPO_ROOT / "dist" / "agent-arsenal.mcpb"

MANIFEST = {
    "manifest_version": "0.4",
    "name": "agent-arsenal",
    "display_name": "AgentArsenal Skills Catalog",
    "version": VERSION,
    "description": (
        "Browse and read the AgentArsenal skills catalog: 246 versioned "
        "skills across 28 domains, from Linux hardening and web pentesting "
        "to incident response and engineering craft."
    ),
    "long_description": (
        "AgentArsenal is a unified agent-skills repo that goes deep on both "
        "software engineering craft and offensive security practice, with "
        "quality enforced by machines, not vibes. This Desktop Extension "
        "bundles the skills catalog as a local MCP server with three tools:\n\n"
        "- list_skills: list skills, filtered by domain or lifecycle\n"
        "- get_skill: read a skill's full SKILL.md content by name\n"
        "- search_skills: keyword search across name, domain, description, "
        "and body\n\n"
        "The catalog is fully offline: the bundle carries the manifest and "
        "every SKILL.md. The server is read-only and never modifies skills. "
        "Offensive skills teach authorized practice only; use them on "
        "systems you own or have written permission to test."
    ),
    "author": {
        "name": "Muhammad Izaz Haider",
        "url": "https://github.com/mizazhaider-ceh",
    },
    "repository": {
        "type": "git",
        "url": "https://github.com/mizazhaider-ceh/AgentArsenal.git",
    },
    "homepage": "https://github.com/mizazhaider-ceh/AgentArsenal",
    "documentation": "https://github.com/mizazhaider-ceh/AgentArsenal/blob/main/README.md",
    "support": "https://github.com/mizazhaider-ceh/AgentArsenal/issues",
    "icon": "icon.png",
    "server": {
        "type": "uv",
        "entry_point": "server/main.py",
    },
    "tools": [
        {
            "name": "list_skills",
            "description": "List AgentArsenal skills, filtered by domain or lifecycle",
        },
        {
            "name": "get_skill",
            "description": "Read a skill's full SKILL.md content and metadata by name",
        },
        {
            "name": "search_skills",
            "description": "Keyword search across the whole skills catalog",
        },
    ],
    "tools_generated": False,
    "keywords": [
        "skills",
        "agent skills",
        "security",
        "pentesting",
        "linux",
        "forensics",
        "engineering",
    ],
    "license": "MIT",
    "compatibility": {
        "claude_desktop": ">=1.0.0",
        "platforms": ["darwin", "win32", "linux"],
        "runtimes": {"python": ">=3.10"},
    },
}

PYPROJECT = """\
[project]
name = "agent-arsenal-mcp"
version = "{version}"
description = "AgentArsenal skills catalog MCP server"
dependencies = ["mcp>=1.9.0"]
requires-python = ">=3.10"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
""".format(version=VERSION)


def have_cairosvg() -> bool:
    try:
        import cairosvg  # noqa: F401
    except ImportError:
        return False
    return True


def make_icon(stage: Path) -> None:
    """Render icon.png from assets/banner.svg. Call only if have_cairosvg()."""
    import cairosvg

    out = stage / "icon.png"
    cairosvg.svg2png(url=str(REPO_ROOT / "assets" / "banner.svg"),
                     write_to=str(out), output_width=256, output_height=256)
    print(f"icon: {out.name} ({out.stat().st_size} bytes)")


def validate_manifest(manifest: dict) -> None:
    required = ["manifest_version", "name", "version", "description",
                "author", "server"]
    missing = [k for k in required if k not in manifest]
    if missing:
        raise ValueError(f"manifest missing required fields: {missing}")
    if "name" not in manifest["author"]:
        raise ValueError("manifest author needs a name")
    server = manifest["server"]
    if server["type"] != "uv" or "entry_point" not in server:
        raise ValueError("expected server.type 'uv' with entry_point")


def main() -> int:
    validate_manifest(MANIFEST)

    src_server = REPO_ROOT / "mcp_server" / "server.py"
    src_manifest = REPO_ROOT / "arsenal-manifest.json"
    src_skills = REPO_ROOT / "skills"
    for path in (src_server, src_manifest, src_skills):
        if not path.exists():
            print(f"error: required source missing: {path}", file=sys.stderr)
            return 1

    with tempfile.TemporaryDirectory(prefix="mcpb-") as tmp:
        stage = Path(tmp) / "stage"
        server_dir = stage / "server"
        data_dir = server_dir / "data"
        (data_dir / "skills").mkdir(parents=True)

        manifest = dict(MANIFEST)
        if have_cairosvg():
            make_icon(stage)
        else:
            manifest.pop("icon", None)
            print("note: cairosvg not installed, bundling without icon.png")

        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2))
        (stage / "pyproject.toml").write_text(PYPROJECT)
        shutil.copy2(src_server, server_dir / "main.py")
        shutil.copy2(src_manifest, data_dir / "arsenal-manifest.json")
        shutil.copytree(src_skills, data_dir / "skills", dirs_exist_ok=True)

        OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(OUT_FILE, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(stage))

    # Verify: manifest.json is at zip root and the entry point is present.
    with zipfile.ZipFile(OUT_FILE) as zf:
        names = zf.namelist()
    checks = ["manifest.json", "pyproject.toml", "server/main.py",
              "server/data/arsenal-manifest.json"]
    missing = [c for c in checks if c not in names]
    if missing:
        print(f"error: bundle missing: {missing}", file=sys.stderr)
        return 1
    skill_files = sum(1 for n in names if n.endswith("SKILL.md"))
    print(f"built {OUT_FILE} ({OUT_FILE.stat().st_size // 1024} KB, "
          f"{len(names)} files, {skill_files} SKILL.md)")

    # Quick manifest sanity check against the bundled copy.
    with zipfile.ZipFile(OUT_FILE) as zf:
        bundled = json.loads(zf.read("manifest.json"))
    validate_manifest(bundled)
    assert bundled["name"] == "agent-arsenal"
    assert bundled["version"] == VERSION
    print("manifest validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
