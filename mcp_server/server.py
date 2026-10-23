"""AgentArsenal MCP server: exposes the 246-skill catalog over MCP.

Tools:
  list_skills(domain, lifecycle, limit)  list skills, optionally filtered
  get_skill(name)                        full SKILL.md content plus metadata
  search_skills(query, limit)            substring search over name,
                                         description, domain, and body

Reads arsenal-manifest.json and the skills/ tree. Works both from a
repo checkout (mcp_server/server.py) and from the .mcpb bundle
(server/data/ holds a copy of the manifest and the skills tree).

Read-only: no skill content is modified through this server.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

try:
    # mcp >= 2.0 renamed FastMCP to MCPServer
    from mcp.server.mcpserver import MCPServer

    mcp = MCPServer("agent-arsenal")
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("agent-arsenal")

SERVER_DIR = Path(__file__).resolve().parent


def find_repo_root() -> Path:
    """Locate the AgentArsenal root (or the bundled data dir) from this file."""
    candidates = [
        SERVER_DIR / "data",          # .mcpb bundle layout: server/data/
        SERVER_DIR,                   # repo layout fallback: mcp_server/ has no manifest
        SERVER_DIR.parent,            # repo layout: repo root holds arsenal-manifest.json
    ]
    for cand in candidates:
        if (cand / "arsenal-manifest.json").exists():
            return cand
    raise FileNotFoundError(
        "arsenal-manifest.json not found: checked server/data/, "
        "mcp_server/, and the parent directory."
    )


REPO_ROOT = find_repo_root()
MANIFEST = json.loads((REPO_ROOT / "arsenal-manifest.json").read_text())


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a SKILL.md into (frontmatter dict, body). Stdlib only."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    fm: dict = {}
    for line in raw.splitlines():
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            value = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
        fm[key.strip()] = value
    return fm, body


@lru_cache(maxsize=1)
def load_catalog() -> list[dict]:
    """Load every skill's metadata and body once at startup."""
    catalog: list[dict] = []
    for entry in MANIFEST["skills"]:
        path = REPO_ROOT / entry["path"] / "SKILL.md"
        fm, body = ({}, "")
        if path.exists():
            fm, body = parse_frontmatter(path.read_text())
        catalog.append(
            {
                "name": entry["name"],
                "version": entry.get("version", fm.get("version", "")),
                "domain": entry.get("domain", fm.get("domain", "")),
                "lifecycle": entry.get("lifecycle", fm.get("lifecycle", "")),
                "description": fm.get("description", ""),
                "requires": entry.get("requires", []),
                "extends": entry.get("extends", []),
                "relates": entry.get("relates", []),
                "path": entry["path"],
                "body": body,
            }
        )
    return catalog


def skill_index() -> dict[str, dict]:
    return {s["name"]: s for s in load_catalog()}


def _summary(skill: dict) -> dict:
    return {
        "name": skill["name"],
        "version": skill["version"],
        "domain": skill["domain"],
        "lifecycle": skill["lifecycle"],
        "description": skill["description"],
    }


def do_list_skills(
    domain: str | None = None,
    lifecycle: str = "stable",
    limit: int = 50,
) -> list[dict]:
    skills = load_catalog()
    if lifecycle:
        skills = [s for s in skills if s["lifecycle"] == lifecycle]
    if domain:
        skills = [s for s in skills if s["domain"] == domain]
    return [_summary(s) for s in skills[:limit]]


def do_get_skill(name: str) -> dict:
    skill = skill_index().get(name)
    if skill is None:
        names = sorted(skill_index())
        hint = [n for n in names if name.lower() in n.lower()][:5]
        return {"error": f"unknown skill '{name}'", "similar": hint}
    out = _summary(skill)
    out["requires"] = skill["requires"]
    out["extends"] = skill["extends"]
    out["relates"] = skill["relates"]
    out["content"] = skill["body"]
    return out


def do_search_skills(query: str, limit: int = 20) -> list[dict]:
    q = query.lower().strip()
    if not q:
        return []
    tokens = q.split()
    scored: list[tuple[int, dict]] = []
    for skill in load_catalog():
        haystack = " ".join(
            [skill["name"], skill["domain"], skill["description"], skill["body"]]
        ).lower()
        score = 0
        if skill["name"].lower() == q:
            score += 100
        for tok in tokens:
            if tok in skill["name"].lower():
                score += 20
            if tok in skill["domain"].lower():
                score += 10
            if tok in skill["description"].lower():
                score += 5
            score += haystack.count(tok)
        if score > 0:
            scored.append((score, skill))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [_summary(s) for _, s in scored[:limit]]


mcp  # defined above: MCPServer (mcp 2.x) or FastMCP (mcp 1.x)


@mcp.tool()
def list_skills(
    domain: str | None = None,
    lifecycle: str = "stable",
    limit: int = 50,
) -> list[dict]:
    """List AgentArsenal skills, optionally filtered by domain or lifecycle.

    domain: one of the 28 domains (ad, linux, web, crypto, ...) or null for all.
    lifecycle: stable, experimental, deprecated, or empty string for all.
    limit: max skills to return.
    """
    return do_list_skills(domain=domain, lifecycle=lifecycle, limit=limit)


@mcp.tool()
def get_skill(name: str) -> dict:
    """Return a skill's full SKILL.md content plus its metadata by name."""
    return do_get_skill(name)


@mcp.tool()
def search_skills(query: str, limit: int = 20) -> list[dict]:
    """Search skills by keyword across name, domain, description, and body."""
    return do_search_skills(query, limit=limit)


if __name__ == "__main__":
    mcp.run()
