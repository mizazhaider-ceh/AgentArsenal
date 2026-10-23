#!/usr/bin/env python3
"""Build a static docs site under docs/ from the skills/ tree.

Outputs:
  docs/index.html          table of all skills (name, domain, version, lifecycle,
                           score badge), client-side JS search filter, links to
                           per-skill pages and the graph page
  docs/skills/<name>.html  one page per skill, rendered from SKILL.md
  docs/graph.html          dependency graph as inline SVG (radial layout)

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
        skills.append({
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
        })
    return skills


def load_scores(root: Path) -> dict[str, float]:
    """Read scores.json tolerantly: accepts {name: n}, {name: {score: n}},
    or {"scores": {...}} wrappers."""
    path = root / "scores.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if isinstance(data, dict) and "scores" in data and isinstance(data["scores"], dict):
        data = data["scores"]
    out: dict[str, float] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (int, float)):
                out[str(key)] = float(value)
            elif isinstance(value, dict) and isinstance(value.get("score"), (int, float)):
                out[str(key)] = float(value["score"])
    return out


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

def build_index(skills: list[dict], scores: dict[str, float]) -> str:
    rows = []
    for s in skills:
        name = html.escape(s["name"])
        domain = html.escape(s["domain"])
        version = html.escape(s["version"])
        desc = s["description"]
        if len(desc) > 160:
            desc = desc[:157].rstrip() + "..."
        rows.append(
            "<tr>"
            f'<td><a href="skills/{name}.html">{name}</a></td>'
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

    body = f"""<h2>Skills ({len(skills)})</h2>
<input type="text" id="filter" placeholder="Filter skills by name, domain, or text...">
{table}
<script>
document.getElementById("filter").addEventListener("input", function (e) {{
  var q = e.target.value.toLowerCase();
  document.querySelectorAll("#skills tbody tr").forEach(function (tr) {{
    tr.style.display = tr.textContent.toLowerCase().indexOf(q) !== -1 ? "" : "none";
  }});
}});
</script>"""
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


def build_skill_page(skill: dict, scores: dict[str, float], known: set[str]) -> str:
    name = html.escape(skill["name"])
    body = skill["body"]
    first = body.split("\n", 1)
    if first and re.match(rf"^#\s+{re.escape(skill['name'])}\s*$", first[0]):
        body = first[1] if len(first) > 1 else ""
    rendered = md_to_html(body)

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
        + meta + desc_html + deps + tools_html + rendered
    )
    return page(f"AgentArsenal: {skill['name']}", body_html, prefix="../")


def _wrap_label(name: str) -> list[str]:
    """Split a slug into at most two short lines for graph labels."""
    parts = name.split("-")
    if len(parts) <= 1 or len(name) <= 16:
        return [name]
    mid = (len(parts) + 1) // 2
    return ["-".join(parts[:mid]) + "-", "-".join(parts[mid:])]


def build_graph(skills: list[dict]) -> str:
    if not skills:
        body = (
            "<h2>Dependency graph</h2>"
            '<p class="muted">No skills found yet, so there is nothing to draw.</p>'
        )
        return page("AgentArsenal dependency graph", body)

    W = H = 1200
    cx = cy = 600
    R = 430

    domains = sorted({s["domain"] for s in skills})
    pos: dict[str, tuple[float, float]] = {}
    for di, domain in enumerate(domains):
        members = [s for s in skills if s["domain"] == domain]
        base = 2 * math.pi * di / len(domains) - math.pi / 2
        spread = 0.35
        for j, s in enumerate(members):
            if len(members) == 1:
                angle = base
            else:
                angle = base + (j / (len(members) - 1) - 0.5) * spread
            pos[s["name"]] = (cx + R * math.cos(angle), cy + R * math.sin(angle))

    edge_styles = {
        "requires": ('stroke="#f8f9fa" stroke-width="2.5"', "requires"),
        "extends": ('stroke="#adb5bd" stroke-width="2" stroke-dasharray="8 5"', "extends"),
        "relates": ('stroke="#6c757d" stroke-width="1.5" stroke-dasharray="2 5"', "relates"),
    }
    edges: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for s in skills:
        for kind in ("requires", "extends", "relates"):
            for dep in s[kind]:
                key = (s["name"], dep, kind)
                if dep in pos and key not in seen:
                    seen.add(key)
                    x1, y1 = pos[s["name"]]
                    x2, y2 = pos[dep]
                    style = edge_styles[kind][0]
                    edges.append(
                        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {style}/>'
                        f'<title>{html.escape(s["name"])} {kind} {html.escape(dep)}</title>'
                    )

    nodes: list[str] = []
    for s in skills:
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

    legend_edges = "".join(
        f'<span><svg width="40" height="10"><line x1="0" y1="5" x2="40" y2="5" {style}/></svg>{label}</span>'
        for style, label in edge_styles.values()
    )
    legend_domains = " ".join(
        f'<span><span class="badge" style="background:{domain_color(d)}22;'
        f"border:1px solid {domain_color(d)};color:{domain_color(d)}\">{html.escape(d)}</span></span>"
        for d in domains
    )

    svg = (
        f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" '
        f'aria-label="Skill dependency graph">'
        + "".join(edges) + "".join(nodes) + "</svg>"
    )
    body = (
        f"<h2>Dependency graph ({len(skills)} skills)</h2>"
        f'<div class="legend">{legend_edges}</div>'
        f'<div class="legend">{legend_domains}</div>'
        f'<p class="graph-note">Node color = domain. Hover a node or edge for details.</p>'
        + svg
    )
    return page("AgentArsenal dependency graph", body)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a static docs site under docs/ from the skills/ tree."
    )
    parser.add_argument("--root", help="Repo root (default: parent of the scripts dir).")
    args = parser.parse_args(argv)

    root = repo_root(args.root)
    skills = discover_skills(root)
    scores = load_scores(root)
    known = {s["name"] for s in skills}

    docs = root / "docs"
    skills_dir = docs / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    (docs / "index.html").write_text(build_index(skills, scores), encoding="utf-8")
    (docs / "graph.html").write_text(build_graph(skills), encoding="utf-8")
    for s in skills:
        (skills_dir / f"{s['name']}.html").write_text(
            build_skill_page(s, scores, known), encoding="utf-8"
        )

    print(f"Built docs for {len(skills)} skill(s) in {docs}/")
    print(f"  index.html, graph.html, skills/ ({len(skills)} page(s))")
    if EM_DASH in "".join(
        [(docs / "index.html").read_text(), (docs / "graph.html").read_text()]
    ):
        print("Error: em dash found in generated docs.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
