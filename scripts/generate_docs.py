#!/usr/bin/env python3
"""Build a static docs site under docs/site/ from the skills/ tree.

The repo landing page lives at docs/index.html (built separately by hand);
this generator owns only docs/site/ underneath it. The landing page links
into the generated reference with relative site/... paths.

Outputs:
  docs/site/index.html          table of all skills (name, domain, version,
                                lifecycle, score badge), client-side JS
                                search filter, links to per-skill pages
                                and the graph page
  docs/site/skills/<name>.html  one page per skill, rendered from SKILL.md
  docs/site/graph.html          dependency graph as inline SVG (radial layout)

Reads scores.json at the repo root when present for quality badges.
Stdlib only. No external assets, no CDN, works from file://.
No em dashes anywhere in this file or its output.
"""

from __future__ import annotations

import argparse
import datetime
import html
import json
import math
import re
import sys
from pathlib import Path

EM_DASH = "\u2014"

DOMAIN_COLORS = {
    "recon": "#4cc9f0",
    "network": "#4895ef",
    "web": "#f72585",
    "auth": "#b5179e",
    "privesc": "#ff9f1c",
    "ad": "#e71d36",
    "c2": "#9b5de5",
    "engineering": "#80ed99",
    "incident": "#ffbf69",
    "forensics": "#00f5d4",
    "linux": "#f15bb5",
    "api": "#fee440",
    "cloud": "#00bbf9",
    "crypto": "#c8b6ff",
    "bugbounty": "#ffd166",
}

FALLBACK_COLORS = [
    "#ff6b6b", "#ffa94d", "#ffd43b", "#69db7c", "#38d9a9",
    "#4dabf7", "#748ffc", "#b197fc", "#e599f7", "#f783ac",
]

CSS = """
:root {
  --bg: #0d1117;
  --panel: #161b22;
  --border: #30363d;
  --text: #e6edf3;
  --muted: #8b949e;
  --accent: #58a6ff;
  --green: #3fb950;
  --yellow: #d29922;
  --red: #f85149;
}
* { box-sizing: border-box; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  margin: 0;
  line-height: 1.6;
}
.wrap { max-width: 1100px; margin: 0 auto; padding: 1.5rem; }
header.site {
  border-bottom: 1px solid var(--border);
  background: var(--panel);
}
header.site .wrap { display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; }
header.site h1 { font-size: 1.25rem; margin: 0; }
header.site h1 a { color: var(--text); text-decoration: none; }
nav a { color: var(--accent); text-decoration: none; margin-right: 1rem; }
nav a:hover { text-decoration: underline; }
table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
th, td { border: 1px solid var(--border); padding: 0.55rem 0.75rem; text-align: left; vertical-align: top; }
th { background: var(--panel); }
tbody tr:hover { background: rgba(88, 166, 255, 0.06); }
a { color: var(--accent); }
.muted { color: var(--muted); }
.badge {
  display: inline-block;
  padding: 0.12rem 0.6rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
}
.badge.green { background: rgba(63, 185, 80, 0.12); color: var(--green); border: 1px solid var(--green); }
.badge.yellow { background: rgba(210, 153, 34, 0.12); color: var(--yellow); border: 1px solid var(--yellow); }
.badge.red { background: rgba(248, 81, 73, 0.12); color: var(--red); border: 1px solid var(--red); }
.badge.gray { background: rgba(139, 148, 158, 0.12); color: var(--muted); border: 1px solid var(--muted); }
#filter {
  width: 100%;
  max-width: 28rem;
  padding: 0.6rem 0.8rem;
  margin-top: 1rem;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 1rem;
}
pre {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1rem;
  overflow-x: auto;
}
code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.9em; }
pre code { font-size: 0.85rem; }
p code, li code, td code {
  background: rgba(88, 166, 255, 0.1);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0.05rem 0.35rem;
}
.meta { display: flex; gap: 0.75rem; flex-wrap: wrap; margin: 1rem 0; align-items: center; }
.deps { margin: 0.5rem 0; }
.deps span.kind { color: var(--muted); font-size: 0.85rem; margin-right: 0.4rem; }
.deps a { margin-right: 0.5rem; }
h2 { border-bottom: 1px solid var(--border); padding-bottom: 0.4rem; }
footer { border-top: 1px solid var(--border); margin-top: 2rem; padding: 1rem 0; color: var(--muted); font-size: 0.85rem; }
.legend { display: flex; gap: 1.5rem; flex-wrap: wrap; margin: 1rem 0; color: var(--muted); font-size: 0.9rem; }
.legend svg { vertical-align: middle; margin-right: 0.4rem; }
.graph-note { color: var(--muted); font-size: 0.9rem; }
"""

FENCE_RE = re.compile(r"```([a-zA-Z0-9+-]*)\s*\n(.*?)```", re.S)


def repo_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Frontmatter parsing (small YAML subset, no external libs)
# ---------------------------------------------------------------------------

def _unquote(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        inner = v[1:-1]
        if v[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    return v


def _scalar(value: str):
    v = value.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_unquote(x) for x in inner.split(",") if x.strip()]
    return _unquote(v)


def _parse_fm_block(raw: str) -> dict:
    data: dict = {}
    lines = raw.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2)
        if val.strip() == "":
            # Block list: either "- name: x" dicts (tools) or plain items.
            items: list = []
            i += 1
            while i < len(lines) and re.match(r"^\s+-\s", lines[i]):
                first = re.match(r"^\s+-\s+([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", lines[i])
                if first:
                    item = {first.group(1): _unquote(first.group(2))}
                    i += 1
                    while i < len(lines) and re.match(r"^\s{2,}[A-Za-z_]", lines[i]) \
                            and not re.match(r"^\s+-\s", lines[i]):
                        m2 = re.match(r"^\s+([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", lines[i])
                        if m2:
                            item[m2.group(1)] = _unquote(m2.group(2))
                        i += 1
                    items.append(item)
                else:
                    items.append(_unquote(lines[i].split("-", 1)[1]))
                    i += 1
            data[key] = items
            continue
        data[key] = _scalar(val)
        i += 1
    return data


def parse_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            raw = text[3:end]
            body = text[end + 4:].lstrip("\n")
            return _parse_fm_block(raw), body
    return {}, text


def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


# ---------------------------------------------------------------------------
# Minimal markdown to HTML (headings, code fences, lists, paragraphs, bold,
# inline code). Everything is HTML-escaped first.
# ---------------------------------------------------------------------------

def _inline(text: str) -> str:
    text = html.escape(text)
    codes: list[str] = []

    def _code_sub(m: re.Match) -> str:
        codes.append(m.group(1))
        return f"\x00C{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", _code_sub, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    for idx, code in enumerate(codes):
        text = text.replace(f"\x00C{idx}\x00", f"<code>{code}</code>")
    return text


def _text_block_to_html(text: str) -> str:
    out: list[str] = []
    para: list[str] = []
    list_open: str | None = None

    def flush_para() -> None:
        if para:
            out.append("<p>" + _inline(" ".join(para)) + "</p>")
            para.clear()

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            out.append(f"</{list_open}>")
            list_open = None

    for line in text.split("\n"):
        s = line.strip()
        if not s:
            flush_para()
            close_list()
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            flush_para()
            close_list()
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            continue
        m = re.match(r"^[-*]\s+(.*)$", s)
        if m:
            flush_para()
            if list_open != "ul":
                close_list()
                out.append("<ul>")
                list_open = "ul"
            out.append("<li>" + _inline(m.group(1)) + "</li>")
            continue
        m = re.match(r"^\d+\.\s+(.*)$", s)
        if m:
            flush_para()
            if list_open != "ol":
                close_list()
                out.append("<ol>")
                list_open = "ol"
            out.append("<li>" + _inline(m.group(1)) + "</li>")
            continue
        para.append(s)
    flush_para()
    close_list()
    return "\n".join(out)


def md_to_html(md: str) -> str:
    out: list[str] = []
    pos = 0
    for m in FENCE_RE.finditer(md):
        block = _text_block_to_html(md[pos:m.start()])
        if block:
            out.append(block)
        lang = m.group(1).strip()
        code = html.escape(m.group(2).rstrip("\n"))
        cls = f' class="language-{html.escape(lang)}"' if lang else ""
        out.append(f"<pre><code{cls}>{code}</code></pre>")
        pos = m.end()
    tail = _text_block_to_html(md[pos:])
    if tail:
        out.append(tail)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def discover_skills(root: Path) -> list[dict]:
    skills: list[dict] = []
    sdir = root / "skills"
    if not sdir.is_dir():
        return skills
    for skill_md in sorted(sdir.glob("*/*/SKILL.md")):
        fm, body = parse_frontmatter(skill_md)
        name = skill_md.parent.name
        domain = skill_md.parent.parent.name
        skills.append(_skill_dict(name, domain, fm, body, parent=None))
    for skill_md in sorted(sdir.glob("*/*/sub/*/SKILL.md")):
        fm, body = parse_frontmatter(skill_md)
        name = skill_md.parent.name
        parent = skill_md.parent.parent.parent.name
        domain = skill_md.parent.parent.parent.parent.name
        skills.append(_skill_dict(name, domain, fm, body, parent=parent))
    return skills


def _skill_dict(name: str, domain: str, fm: dict, body: str,
                parent: str | None) -> dict:
    return {
        "name": name,
        "domain": domain,
        "version": str(fm.get("version", "?")),
        "lifecycle": str(fm.get("lifecycle", "?")),
        "description": str(fm.get("description", "")),
        "last_verified": str(fm.get("last_verified", "")),
        "requires": _as_list(fm.get("requires")),
        "extends": _as_list(fm.get("extends")),
        "relates": _as_list(fm.get("relates")),
        "tools": fm.get("tools", []) if isinstance(fm.get("tools"), list) else [],
        "body": body,
        "parent": parent,
        "is_sub": parent is not None,
    }


def _kind_file_dict(name: str, fm: dict, body: str) -> dict:
    return {
        "name": name,
        "version": str(fm.get("version", "?")),
        "description": str(fm.get("description", "")),
        "body": body,
    }


def discover_agents(root: Path) -> list[dict]:
    agents: list[dict] = []
    adir = root / "agents"
    if not adir.is_dir():
        return agents
    for agent_md in sorted(adir.glob("*/AGENT.md")):
        fm, body = parse_frontmatter(agent_md)
        entry = _kind_file_dict(agent_md.parent.name, fm, body)
        entry.update({
            "role": str(fm.get("role", "")),
            "skills": _as_list(fm.get("skills")),
            "brains": _as_list(fm.get("brains")),
            "memory_mode": str(fm.get("memory_mode", "")),
            "escalation": str(fm.get("escalation", "")),
            "constraints": _as_list(fm.get("constraints")),
        })
        agents.append(entry)
    return agents


def discover_brains(root: Path) -> list[dict]:
    brains: list[dict] = []
    bdir = root / "brains"
    if not bdir.is_dir():
        return brains
    for brain_md in sorted(bdir.glob("*/BRAIN.md")):
        fm, body = parse_frontmatter(brain_md)
        entry = _kind_file_dict(brain_md.parent.name, fm, body)
        entry.update({
            "provides": _as_list(fm.get("provides")),
            "used_by": _as_list(fm.get("used_by")),
        })
        brains.append(entry)
    return brains


def discover_playbooks(root: Path) -> list[dict]:
    playbooks: list[dict] = []
    pdir = root / "playbooks"
    if not pdir.is_dir():
        return playbooks
    for pb_md in sorted(pdir.glob("*/PLAYBOOK.md")):
        fm, body = parse_frontmatter(pb_md)
        entry = _kind_file_dict(pb_md.parent.name, fm, body)
        entry.update({
            "bindings": _as_list(fm.get("bindings")),
        })
        playbooks.append(entry)
    return playbooks


def discover_workflows(root: Path) -> list[dict]:
    workflows: list[dict] = []
    wdir = root / "workflows"
    if not wdir.is_dir():
        return workflows
    for wf_md in sorted(wdir.glob("*.md")):
        if wf_md.name == "README.md":
            continue
        workflows.append({
            "name": wf_md.stem,
            "body": wf_md.read_text(encoding="utf-8"),
        })
    return workflows


def discover_decisions(root: Path) -> list[dict]:
    decisions: list[dict] = []
    ddir = root / "decisions"
    if not ddir.is_dir():
        return decisions
    for d_md in sorted(ddir.glob("*.md")):
        decisions.append({
            "name": d_md.stem,
            "file": d_md.name,
            "body": d_md.read_text(encoding="utf-8"),
        })
    return decisions


def decision_page_href(repo_rel: str) -> str:
    """Convert a repo-relative decisions/*.md path to a docs decisions/*.html href."""
    stem = Path(repo_rel).stem
    return f"../decisions/{stem}.html"


def _score_group(data: dict, key: str) -> dict[str, float]:
    """Extract one {name: score} map from a scores.json group value."""
    group = data.get(key)
    out: dict[str, float] = {}
    if isinstance(group, dict):
        for name, value in group.items():
            if isinstance(value, dict) and isinstance(value.get("score"), (int, float)):
                out[str(name)] = float(value["score"])
            elif isinstance(value, (int, float)):
                out[str(name)] = float(value)
    return out


def load_all_scores(root: Path) -> dict[str, dict[str, float]]:
    """Read scores.json into {"skills": {...}, "agents": {...}, "brains": {...}}.

    Tolerates the wave-3 shape, the {"scores": {...}} wrapper, {name: n},
    and {name: {"score": n}} shapes for the skills group.
    """
    empty = {"skills": {}, "agents": {}, "brains": {}}
    path = root / "scores.json"
    if not path.exists():
        return empty
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return empty
    if not isinstance(data, dict):
        return empty
    if (set(data.keys()) <= {"skills", "agents", "brains"}
            and isinstance(data.get("skills"), dict)):
        return {
            "skills": _score_group(data, "skills"),
            "agents": _score_group(data, "agents"),
            "brains": _score_group(data, "brains"),
        }
    if "scores" in data and isinstance(data["scores"], dict):
        data = data["scores"]
    out: dict[str, float] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (int, float)):
                out[str(key)] = float(value)
            elif isinstance(value, dict) and isinstance(value.get("score"), (int, float)):
                out[str(key)] = float(value["score"])
    return {"skills": out, "agents": {}, "brains": {}}


def load_scores(root: Path) -> dict[str, float]:
    """Read scores.json tolerantly (skills group only).

    Accepts the wave-3 shape {"skills": {name: ...}, "agents": {...},
    "brains": {...}} (uses the "skills" map), the {"scores": {...}}
    wrapper, {name: n}, and {name: {"score": n}}.
    """
    return load_all_scores(root)["skills"]


# ---------------------------------------------------------------------------
# Shared page chrome
# ---------------------------------------------------------------------------

def domain_color(domain: str) -> str:
    if domain in DOMAIN_COLORS:
        return DOMAIN_COLORS[domain]
    idx = abs(hash(domain)) % len(FALLBACK_COLORS)
    return FALLBACK_COLORS[idx]


def lifecycle_badge(lifecycle: str) -> str:
    cls = {"stable": "green", "experimental": "yellow", "deprecated": "red"}.get(
        lifecycle.lower(), "gray"
    )
    return f'<span class="badge {cls}">{html.escape(lifecycle)}</span>'


def score_badge(scores: dict[str, float], name: str) -> str:
    if name not in scores:
        return '<span class="badge gray">n/a</span>'
    score = scores[name]
    cls = "green" if score >= 90 else ("yellow" if score >= 70 else "red")
    shown = int(score) if float(score).is_integer() else round(score, 1)
    return f'<span class="badge {cls}">{shown}/100</span>'


def page(title: str, body_html: str, prefix: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<header class="site">
<div class="wrap">
<h1><a href="{prefix}index.html">AgentArsenal</a></h1>
<nav>
<a href="{prefix}index.html">Skills</a>
<a href="{prefix}index.html#agents">Agents</a>
<a href="{prefix}index.html#brains">Brains</a>
<a href="{prefix}index.html#playbooks">Playbooks</a>
<a href="{prefix}index.html#decisions">Decisions</a>
<a href="{prefix}graph.html">Dependency graph</a>
</nav>
</div>
</header>
<main class="wrap">
{body_html}
</main>
<footer class="wrap">
<p>AgentArsenal docs. Generated {datetime.date.today().isoformat()}.</p>
</footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def build_index(skills: list[dict], agents: list[dict], brains: list[dict],
                playbooks: list[dict], scores: dict[str, float],
                agent_scores: dict[str, float],
                brain_scores: dict[str, float],
                decisions: list[dict] | None = None) -> str:
    decisions = decisions or []
    top_skills = [s for s in skills if not s["is_sub"]]
    sub_skills = [s for s in skills if s["is_sub"]]
    rows = []
    for s in top_skills:
        name = html.escape(s["name"])
        domain = html.escape(s["domain"])
        version = html.escape(s["version"])
        desc = s["description"]
        if len(desc) > 160:
            desc = desc[:157].rstrip() + "..."
        sub_note = ""
        children = [c["name"] for c in sub_skills if c["parent"] == s["name"]]
        if children:
            sub_note = f' <span class="muted">(+{len(children)} sub)</span>'
        rows.append(
            "<tr>"
            f'<td><a href="skills/{name}.html">{name}</a>{sub_note}</td>'
            f'<td><span class="badge gray">{domain}</span></td>'
            f"<td>{version}</td>"
            f"<td>{lifecycle_badge(s['lifecycle'])}</td>"
            f"<td>{score_badge(scores, s['name'])}</td>"
            f'<td class="muted">{html.escape(desc)}</td>'
            "</tr>"
        )
    if rows:
        table = (
            "<table id=\"skills\">\n<thead><tr>"
            "<th>Name</th><th>Domain</th><th>Version</th>"
            "<th>Lifecycle</th><th>Score</th><th>Description</th>"
            "</tr></thead>\n<tbody>\n" + "\n".join(rows) + "\n</tbody>\n</table>"
        )
    else:
        table = '<p class="muted">No skills found yet. Scaffold one with <code>python3 scripts/new_skill.py</code>.</p>'

    agent_rows = []
    for a in agents:
        name = html.escape(a["name"])
        role = a["role"]
        if len(role) > 140:
            role = role[:137].rstrip() + "..."
        nbind = len(a["skills"]) + len(a["brains"])
        agent_rows.append(
            "<tr>"
            f'<td><a href="agents/{name}.html">{name}</a></td>'
            f'<td class="muted">{html.escape(role)}</td>'
            f"<td>{html.escape(a['version'])}</td>"
            f"<td>{nbind}</td>"
            f"<td>{score_badge(agent_scores, a['name'])}</td>"
            "</tr>"
        )
    agents_section = (
        '<h2 id="agents">Agents (%d)</h2>\n' % len(agents)
        + ("<table><thead><tr><th>Name</th><th>Role</th><th>Version</th>"
           "<th>Bindings</th><th>Score</th></tr></thead><tbody>\n"
           + "\n".join(agent_rows) + "\n</tbody></table>"
           if agent_rows else
           '<p class="muted">No agents yet. See <code>agents/README.md</code> for the AGENT.md standard.</p>')
    )

    brain_rows = []
    for b in brains:
        name = html.escape(b["name"])
        brain_rows.append(
            "<tr>"
            f'<td><a href="brains/{name}.html">{name}</a></td>'
            f"<td>{html.escape(b['version'])}</td>"
            f"<td>{len(b['provides'])}</td>"
            f"<td>{score_badge(brain_scores, b['name'])}</td>"
            "</tr>"
        )
    brains_section = (
        '<h2 id="brains">Brains (%d)</h2>\n' % len(brains)
        + ("<table><thead><tr><th>Name</th><th>Version</th>"
           "<th>Provides</th><th>Score</th></tr></thead><tbody>\n"
           + "\n".join(brain_rows) + "\n</tbody></table>"
           if brain_rows else
           '<p class="muted">No brains yet. See <code>brains/README.md</code> for the BRAIN.md standard.</p>')
    )

    pb_rows = []
    for p in playbooks:
        name = html.escape(p["name"])
        pb_rows.append(
            "<tr>"
            f'<td><a href="playbooks/{name}.html">{name}</a></td>'
            f"<td>{html.escape(p['version'])}</td>"
            f"<td>{len(p['bindings'])}</td>"
            "</tr>"
        )
    playbooks_section = (
        '<h2 id="playbooks">Playbooks (%d)</h2>\n' % len(playbooks)
        + ("<table><thead><tr><th>Name</th><th>Version</th>"
           "<th>Bindings</th></tr></thead><tbody>\n"
           + "\n".join(pb_rows) + "\n</tbody></table>"
           if pb_rows else
           '<p class="muted">No playbooks yet. See <code>playbooks/README.md</code> for the PLAYBOOK.md standard.</p>')
    )

    decisions_section = (
        '<h2 id="decisions">Decision docs (%d)</h2>\n' % len(decisions)
        + ("<table><thead><tr><th>Name</th><th>Source file</th></tr></thead><tbody>\n"
           + "\n".join(
               f'<tr><td><a href="decisions/{html.escape(d["name"])}.html">'
               f'{html.escape(d["name"])}</a></td>'
               f'<td><code>{html.escape(d["file"])}</code></td></tr>'
               for d in decisions)
           + "\n</tbody></table>"
           if decisions else
           '<p class="muted">No decision docs yet.</p>')
    )

    body = f"""<h2>Skills ({len(top_skills)})</h2>
<input type="text" id="filter" placeholder="Filter skills by name, domain, or text...">
{table}
<script>
document.getElementById("filter").addEventListener("input", function (e) {{
  var q = e.target.value.toLowerCase();
  document.querySelectorAll("#skills tbody tr").forEach(function (tr) {{
    tr.style.display = tr.textContent.toLowerCase().indexOf(q) !== -1 ? "" : "none";
  }});
}});
</script>
{agents_section}
{brains_section}
{playbooks_section}
{decisions_section}"""
    return page("AgentArsenal skills", body)


def _dep_links(names: list[str], known: set[str]) -> str:
    if not names:
        return '<span class="muted">none</span>'
    parts = []
    for n in names:
        esc = html.escape(n)
        if n in known:
            parts.append(f'<a href="{esc}.html">{esc}</a>')
        else:
            parts.append(f'<span class="muted">{esc} (missing)</span>')
    return " ".join(parts)


def build_skill_page(skill: dict, scores: dict[str, float], known: set[str],
                     sub_skills: list[dict] | None = None) -> str:
    name = html.escape(skill["name"])
    body = skill["body"]
    first = body.split("\n", 1)
    if first and re.match(rf"^#\s+{re.escape(skill['name'])}\s*$", first[0]):
        body = first[1] if len(first) > 1 else ""
    rendered = md_to_html(body)

    sub_tree = ""
    if skill.get("is_sub"):
        parent = skill.get("parent")
        if parent:
            pesc = html.escape(parent)
            sub_tree = (
                '<div class="deps"><span class="kind">sub-skill of:</span> '
                f'<a href="{pesc}.html">{pesc}</a></div>'
            )
    elif sub_skills:
        children = [c for c in sub_skills if c["parent"] == skill["name"]]
        if children:
            items = []
            for c in sorted(children, key=lambda c: c["name"]):
                cesc = html.escape(c["name"])
                cdesc = html.escape(c["description"][:140])
                items.append(
                    f'<li><a href="{cesc}.html">{cesc}</a> '
                    f'<span class="muted">v{html.escape(c["version"])}: {cdesc}</span></li>'
                )
            sub_tree = ("<h2>Sub-skills</h2><ul>" + "".join(items) + "</ul>")

    tools = skill["tools"]
    if tools:
        tool_rows = []
        for t in tools:
            if isinstance(t, dict):
                tool_rows.append(
                    f"<tr><td>{html.escape(str(t.get('name', '')))}</td>"
                    f"<td>{html.escape(str(t.get('version', '')))}</td></tr>"
                )
        tools_html = (
            "<h2>Tools</h2><table><thead><tr><th>Tool</th><th>Version</th></tr></thead>"
            "<tbody>" + "".join(tool_rows) + "</tbody></table>"
            if tool_rows else ""
        )
    else:
        tools_html = ""

    meta = (
        '<div class="meta">'
        f'<span class="badge gray">{html.escape(skill["domain"])}</span>'
        f'<span class="muted">v{html.escape(skill["version"])}</span>'
        f"{lifecycle_badge(skill['lifecycle'])}"
        f"{score_badge(scores, skill['name'])}"
        + (f'<span class="muted">verified {html.escape(skill["last_verified"])}</span>'
           if skill["last_verified"] else "")
        + "</div>"
    )
    deps = (
        '<div class="deps"><span class="kind">requires:</span> '
        + _dep_links(skill["requires"], known) + "</div>"
        '<div class="deps"><span class="kind">extends:</span> '
        + _dep_links(skill["extends"], known) + "</div>"
        '<div class="deps"><span class="kind">relates:</span> '
        + _dep_links(skill["relates"], known) + "</div>"
    )
    desc_html = f"<p>{html.escape(skill['description'])}</p>" if skill["description"] else ""

    body_html = (
        f'<p><a href="../index.html">&larr; All skills</a></p>'
        f"<h2>{name}</h2>"
        + meta + desc_html + sub_tree + deps + tools_html + rendered
    )
    return page(f"AgentArsenal: {skill['name']}", body_html, prefix="../")


def _linked_list(names: list[str], known: set[str], subdir: str) -> str:
    if not names:
        return '<span class="muted">none</span>'
    parts = []
    for n in names:
        esc = html.escape(n)
        if n in known:
            parts.append(f'<a href="../{subdir}/{esc}.html">{esc}</a>')
        else:
            parts.append(f'<span class="muted">{esc} (missing)</span>')
    return " ".join(parts)


def build_agent_page(agent: dict, agent_scores: dict[str, float],
                     skill_names: set[str], brain_names: set[str]) -> str:
    name = html.escape(agent["name"])
    rendered = md_to_html(agent["body"])
    meta = (
        '<div class="meta">'
        f'<span class="badge gray">agent</span>'
        f'<span class="muted">v{html.escape(agent["version"])}</span>'
        f"{score_badge(agent_scores, agent['name'])}"
        + (f'<span class="muted">memory: {html.escape(agent["memory_mode"])}</span>'
           if agent["memory_mode"] else "")
        + "</div>"
    )
    desc_html = f"<p>{html.escape(agent['description'])}</p>" if agent["description"] else ""
    esc = agent["escalation"]
    esc_html = (
        f'<div class="deps"><span class="kind">escalation:</span> '
        f'<a href="{decision_page_href(html.escape(esc))}">{html.escape(esc)}</a></div>'
        if esc else ""
    )
    constraints = agent["constraints"]
    constraints_html = ""
    if constraints:
        items = "".join(f"<li>{html.escape(c)}</li>" for c in constraints)
        constraints_html = f"<h2>Constraints</h2><ul>{items}</ul>"
    deps = (
        '<div class="deps"><span class="kind">skills:</span> '
        + _linked_list(agent["skills"], skill_names, "skills") + "</div>"
        '<div class="deps"><span class="kind">brains:</span> '
        + _linked_list(agent["brains"], brain_names, "brains") + "</div>"
    )
    body_html = (
        f'<p><a href="../index.html">&larr; All artifacts</a></p>'
        f"<h2>{name}</h2>"
        + meta + desc_html
        + (f'<p><strong>Role:</strong> {html.escape(agent["role"])}</p>'
           if agent["role"] else "")
        + deps + esc_html + constraints_html + rendered
    )
    return page(f"AgentArsenal agent: {agent['name']}", body_html, prefix="../")


def build_brain_page(brain: dict, brain_scores: dict[str, float],
                     agent_names: set[str]) -> str:
    name = html.escape(brain["name"])
    rendered = md_to_html(brain["body"])
    meta = (
        '<div class="meta">'
        f'<span class="badge gray">brain</span>'
        f'<span class="muted">v{html.escape(brain["version"])}</span>'
        f"{score_badge(brain_scores, brain['name'])}"
        "</div>"
    )
    desc_html = f"<p>{html.escape(brain['description'])}</p>" if brain["description"] else ""
    provides = brain["provides"]
    provides_html = ""
    if provides:
        items = "".join(f"<li>{html.escape(p)}</li>" for p in provides)
        provides_html = f"<h2>Provides</h2><ul>{items}</ul>"
    used_by_html = (
        '<div class="deps"><span class="kind">used by:</span> '
        + _linked_list(brain["used_by"], agent_names, "agents") + "</div>"
    )
    body_html = (
        f'<p><a href="../index.html">&larr; All artifacts</a></p>'
        f"<h2>{name}</h2>"
        + meta + desc_html + provides_html + used_by_html + rendered
    )
    return page(f"AgentArsenal brain: {brain['name']}", body_html, prefix="../")


def _binding_link(binding: str, skill_names: set[str], agent_names: set[str],
                  brain_names: set[str]) -> str:
    if ":" not in binding:
        return f'<span class="muted">{html.escape(binding)} (bad format)</span>'
    kind, target = binding.split(":", 1)
    kind, target = kind.strip(), target.strip()
    esc_target = html.escape(target)
    if kind == "agent":
        if target in agent_names:
            return f'<a href="../agents/{esc_target}.html">agent:{esc_target}</a>'
    elif kind == "skill":
        if target in skill_names:
            return f'<a href="../skills/{esc_target}.html">skill:{esc_target}</a>'
    elif kind == "brain":
        if target in brain_names:
            return f'<a href="../brains/{esc_target}.html">brain:{esc_target}</a>'
    elif kind == "decisions":
        return f'<a href="{decision_page_href(target)}">{html.escape(binding)}</a>'
    return f'<span class="muted">{html.escape(binding)} (missing)</span>'


def build_playbook_page(playbook: dict, skill_names: set[str],
                        agent_names: set[str],
                        brain_names: set[str]) -> str:
    name = html.escape(playbook["name"])
    rendered = md_to_html(playbook["body"])
    meta = (
        '<div class="meta">'
        f'<span class="badge gray">playbook</span>'
        f'<span class="muted">v{html.escape(playbook["version"])}</span>'
        "</div>"
    )
    desc_html = (f"<p>{html.escape(playbook['description'])}</p>"
                 if playbook["description"] else "")
    bindings = playbook["bindings"]
    bindings_html = ""
    if bindings:
        items = "".join(
            f"<li>{_binding_link(b, skill_names, agent_names, brain_names)}</li>"
            for b in bindings
        )
        bindings_html = f"<h2>Bindings</h2><ul>{items}</ul>"
    body_html = (
        f'<p><a href="../index.html">&larr; All artifacts</a></p>'
        f"<h2>{name}</h2>"
        + meta + desc_html + bindings_html + rendered
    )
    return page(f"AgentArsenal playbook: {playbook['name']}",
                body_html, prefix="../")


def build_decision_page(decision: dict) -> str:
    name = html.escape(decision["name"])
    rendered = md_to_html(decision["body"])
    meta = (
        '<div class="meta">'
        '<span class="badge gray">decision doc</span>'
        f'<span class="muted">{html.escape(decision["file"])}</span>'
        "</div>"
    )
    body_html = (
        '<p><a href="../index.html">&larr; All artifacts</a></p>'
        f"<h2>{name}</h2>"
        + meta + rendered
    )
    return page(f"AgentArsenal decision: {decision['name']}",
                body_html, prefix="../")


def _wrap_label(name: str) -> list[str]:
    """Split a slug into at most two short lines for graph labels."""
    parts = name.split("-")
    if len(parts) <= 1 or len(name) <= 16:
        return [name]
    mid = (len(parts) + 1) // 2
    return ["-".join(parts[:mid]) + "-", "-".join(parts[mid:])]


def build_graph(skills: list[dict], agents: list[dict] | None = None,
                brains: list[dict] | None = None) -> str:
    agents = agents or []
    brains = brains or []
    top_skills = [s for s in skills if not s.get("is_sub")]
    if not top_skills and not agents and not brains:
        body = (
            "<h2>Dependency graph</h2>"
            '<p class="muted">No skills found yet, so there is nothing to draw.</p>'
        )
        return page("AgentArsenal dependency graph", body)

    W = H = 1400
    cx = cy = 700
    R_SKILL = 480
    R_AGENT = 640
    R_BRAIN = 200

    domains = sorted({s["domain"] for s in top_skills})
    pos: dict[str, tuple[float, float]] = {}
    for di, domain in enumerate(domains):
        members = [s for s in top_skills if s["domain"] == domain]
        base = 2 * math.pi * di / len(domains) - math.pi / 2
        spread = 0.35
        for j, s in enumerate(members):
            if len(members) == 1:
                angle = base
            else:
                angle = base + (j / (len(members) - 1) - 0.5) * spread
            pos[s["name"]] = (cx + R_SKILL * math.cos(angle),
                              cy + R_SKILL * math.sin(angle))

    agent_pos: dict[str, tuple[float, float]] = {}
    for i, a in enumerate(agents):
        angle = 2 * math.pi * i / len(agents) - math.pi / 2
        agent_pos[a["name"]] = (cx + R_AGENT * math.cos(angle),
                                cy + R_AGENT * math.sin(angle))

    brain_pos: dict[str, tuple[float, float]] = {}
    for i, b in enumerate(brains):
        angle = 2 * math.pi * i / len(brains) - math.pi / 2
        brain_pos[b["name"]] = (cx + R_BRAIN * math.cos(angle),
                                cy + R_BRAIN * math.sin(angle))

    edge_styles = {
        "requires": ('stroke="#f8f9fa" stroke-width="2.5"', "requires"),
        "extends": ('stroke="#adb5bd" stroke-width="2" stroke-dasharray="8 5"', "extends"),
        "relates": ('stroke="#6c757d" stroke-width="1.5" stroke-dasharray="2 5"', "relates"),
        "binds-skill": ('stroke="#80ed99" stroke-width="2"', "agent binds skill"),
        "binds-brain": ('stroke="#c8b6ff" stroke-width="2"', "agent binds brain"),
    }
    edges: list[str] = []
    seen: set[tuple[str, str, str]] = set()

    def add_edge(x1: float, y1: float, x2: float, y2: float,
                 kind: str, title: str) -> None:
        style = edge_styles[kind][0]
        edges.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {style}/>'
            f"<title>{html.escape(title)}</title>"
        )

    for s in top_skills:
        for kind in ("requires", "extends", "relates"):
            for dep in s[kind]:
                key = (s["name"], dep, kind)
                if dep in pos and key not in seen:
                    seen.add(key)
                    x1, y1 = pos[s["name"]]
                    x2, y2 = pos[dep]
                    add_edge(x1, y1, x2, y2, kind,
                             "%s %s %s" % (s["name"], kind, dep))
    for a in agents:
        if a["name"] not in agent_pos:
            continue
        x1, y1 = agent_pos[a["name"]]
        for skill_name in a["skills"]:
            if skill_name in pos:
                x2, y2 = pos[skill_name]
                add_edge(x1, y1, x2, y2, "binds-skill",
                         "%s binds skill %s" % (a["name"], skill_name))
        for brain_name in a["brains"]:
            if brain_name in brain_pos:
                x2, y2 = brain_pos[brain_name]
                add_edge(x1, y1, x2, y2, "binds-brain",
                         "%s binds brain %s" % (a["name"], brain_name))

    nodes: list[str] = []
    for s in top_skills:
        x, y = pos[s["name"]]
        color = domain_color(s["domain"])
        esc_name = html.escape(s["name"])
        label_lines = _wrap_label(s["name"])
        tspans = "".join(
            f'<tspan x="{x:.1f}" dy="{22 if i == 0 else 16}">{html.escape(line)}</tspan>'
            for i, line in enumerate(label_lines)
        )
        nodes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="30" fill="{color}" opacity="0.9">'
            f"<title>{esc_name} ({html.escape(s['domain'])})</title></circle>"
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'font-size="13" fill="#e6edf3" font-family="system-ui, sans-serif">{tspans}</text>'
        )
    for a in agents:
        x, y = agent_pos[a["name"]]
        esc_name = html.escape(a["name"])
        label_lines = _wrap_label(a["name"])
        tspans = "".join(
            f'<tspan x="{x:.1f}" dy="{22 if i == 0 else 16}">{html.escape(line)}</tspan>'
            for i, line in enumerate(label_lines)
        )
        nodes.append(
            f'<rect x="{x - 34:.1f}" y="{y - 34:.1f}" width="68" height="68" rx="10" '
            f'fill="#1f6f43" opacity="0.9">'
            f"<title>agent {esc_name}</title></rect>"
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'font-size="12" fill="#e6edf3" font-family="system-ui, sans-serif">{tspans}</text>'
        )
    for b in brains:
        x, y = brain_pos[b["name"]]
        esc_name = html.escape(b["name"])
        nodes.append(
            f'<polygon points="{x:.1f},{y - 30:.1f} {x + 30:.1f},{y + 22:.1f} '
            f'{x - 30:.1f},{y + 22:.1f}" fill="#5a3d8a" opacity="0.9">'
            f"<title>brain {esc_name}</title></polygon>"
            f'<text x="{x:.1f}" y="{y + 48:.1f}" text-anchor="middle" '
            f'font-size="12" fill="#e6edf3" font-family="system-ui, sans-serif">{esc_name}</text>'
        )

    legend_edges = "".join(
        f'<span><svg width="40" height="10"><line x1="0" y1="5" x2="40" y2="5" {style}/></svg>{label}</span>'
        for style, label in edge_styles.values()
    )
    legend_domains = " ".join(
        f'<span><span class="badge" style="background:{domain_color(d)}22;'
        f"border:1px solid {domain_color(d)};color:{domain_color(d)}\">{html.escape(d)}</span></span>"
        for d in domains
    )
    legend_kinds = (
        '<span><span class="badge" style="background:#1f6f4322;border:1px solid #1f6f43;'
        'color:#80ed99">agent (square)</span></span> '
        '<span><span class="badge" style="background:#5a3d8a22;border:1px solid #5a3d8a;'
        'color:#c8b6ff">brain (triangle)</span></span>'
    )

    svg = (
        f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
        f'aria-label="Skill dependency graph">'
        + "".join(edges) + "".join(nodes) + "</svg>"
    )
    total_nodes = len(top_skills) + len(agents) + len(brains)
    body = (
        f"<h2>Dependency graph ({total_nodes} nodes)</h2>"
        f'<div class="legend">{legend_edges}</div>'
        f'<div class="legend">{legend_domains}</div>'
        f'<div class="legend">{legend_kinds}</div>'
        f'<p class="graph-note">Node color = domain (skills), squares = agents, '
        f"triangles = brains. Hover a node or edge for details.</p>"
        + svg
    )
    return page("AgentArsenal dependency graph", body)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a static docs site under docs/site/ from the skills/ tree."
    )
    parser.add_argument("--root", help="Repo root (default: parent of the scripts dir).")
    args = parser.parse_args(argv)

    root = repo_root(args.root)
    skills = discover_skills(root)
    agents = discover_agents(root)
    brains = discover_brains(root)
    playbooks = discover_playbooks(root)
    workflows = discover_workflows(root)
    decisions = discover_decisions(root)
    all_scores = load_all_scores(root)
    scores = all_scores["skills"]
    agent_scores = all_scores["agents"]
    brain_scores = all_scores["brains"]
    known = {s["name"] for s in skills}
    sub_skills = [s for s in skills if s["is_sub"]]

    docs = root / "docs" / "site"
    skills_dir = docs / "skills"
    agents_dir = docs / "agents"
    brains_dir = docs / "brains"
    playbooks_dir = docs / "playbooks"
    decisions_dir = docs / "decisions"
    for d in (skills_dir, agents_dir, brains_dir, playbooks_dir, decisions_dir):
        d.mkdir(parents=True, exist_ok=True)

    (docs / "index.html").write_text(
        build_index(skills, agents, brains, playbooks, scores,
                    agent_scores, brain_scores, decisions), encoding="utf-8")
    (docs / "graph.html").write_text(build_graph(skills, agents, brains),
                                     encoding="utf-8")
    for s in skills:
        (skills_dir / f"{s['name']}.html").write_text(
            build_skill_page(s, scores, known, sub_skills), encoding="utf-8"
        )
    agent_names = {a["name"] for a in agents}
    brain_names = {b["name"] for b in brains}
    for a in agents:
        (agents_dir / f"{a['name']}.html").write_text(
            build_agent_page(a, agent_scores, known, brain_names),
            encoding="utf-8")
    for b in brains:
        (brains_dir / f"{b['name']}.html").write_text(
            build_brain_page(b, brain_scores, agent_names), encoding="utf-8")
    for p in playbooks:
        (playbooks_dir / f"{p['name']}.html").write_text(
            build_playbook_page(p, known, agent_names, brain_names),
            encoding="utf-8")
    for d in decisions:
        (decisions_dir / f"{d['name']}.html").write_text(
            build_decision_page(d), encoding="utf-8")

    written = [docs / "index.html", docs / "graph.html"]
    written += [skills_dir / f"{s['name']}.html" for s in skills]
    written += [agents_dir / f"{a['name']}.html" for a in agents]
    written += [brains_dir / f"{b['name']}.html" for b in brains]
    written += [playbooks_dir / f"{p['name']}.html" for p in playbooks]
    written += [decisions_dir / f"{d['name']}.html" for d in decisions]

    print(f"Built docs for {len(skills)} skill(s), {len(agents)} agent(s), "
          f"{len(brains)} brain(s), {len(playbooks)} playbook(s), "
          f"{len(workflows)} workflow(s), {len(decisions)} decision(s) in {docs}/")
    print(f"  index.html, graph.html, skills/ ({len(skills)} page(s)), "
          f"agents/ ({len(agents)}), brains/ ({len(brains)}), "
          f"playbooks/ ({len(playbooks)}), decisions/ ({len(decisions)})")
    for path in written:
        if EM_DASH in path.read_text(encoding="utf-8"):
            print("Error: em dash found in generated docs (%s)." % path,
                  file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
