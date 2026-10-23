#!/usr/bin/env python3
"""AgentArsenal CI validator (stdlib only).

Validates every skills/<domain>/<skill>/SKILL.md (including nested
sub-skills at skills/<domain>/<skill>/sub/<sub>/SKILL.md) against SPEC.md,
plus agents/<name>/AGENT.md, brains/<name>/BRAIN.md,
playbooks/<name>/PLAYBOOK.md, and workflows/<pattern>.md.

Prints file:line style errors and exits non-zero on ANY failure.
Missing artifact directories are skipped gracefully (exit 0).
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")
AGENTS_DIR = os.path.join(REPO_ROOT, "agents")
BRAINS_DIR = os.path.join(REPO_ROOT, "brains")
PLAYBOOKS_DIR = os.path.join(REPO_ROOT, "playbooks")
WORKFLOWS_DIR = os.path.join(REPO_ROOT, "workflows")
DECISIONS_DIR = os.path.join(REPO_ROOT, "decisions")
MANIFEST_PATH = os.path.join(REPO_ROOT, "arsenal-manifest.json")

DOMAINS = [
    "recon", "network", "web", "auth", "privesc", "ad", "c2",
    "engineering", "incident", "forensics", "linux", "api",
    "cloud", "crypto", "bugbounty",
    "mobile", "binary", "malware", "soc", "osint", "defensive",
    "ai-security", "hardware", "ics-scada", "blockchain",
    "automotive", "privacy", "memory",
]
LIFECYCLES = ["experimental", "stable", "deprecated"]
REQUIRED_FIELDS = [
    "name", "description", "version", "domain", "lifecycle",
    "last_verified", "requires", "extends", "relates", "tools",
]
SUB_REQUIRED_FIELDS = REQUIRED_FIELDS + ["parent"]
AGENT_REQUIRED_FIELDS = [
    "name", "kind", "description", "version", "role",
    "skills", "brains", "memory_mode", "escalation", "constraints",
]
BRAIN_REQUIRED_FIELDS = [
    "name", "kind", "description", "version", "provides", "used_by",
]
PLAYBOOK_REQUIRED_FIELDS = [
    "name", "kind", "description", "version", "bindings",
]
MEMORY_MODES = ["stateless", "persistent"]
REQUIRED_HEADINGS = ["## Quick Workflow", "## Edge cases", "## Key references"]
EM_DASH = "\u2014"

SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# key: value where the colon is followed by whitespace or end of line
# (so "http://x" is NOT treated as a mapping)
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:[ \t]+(.*?))?[ \t]*$")
BINDING_RE = re.compile(r"^(agent|skill|brain|decisions):(.+)$")


# ---------------------------------------------------------------------------
# Minimal YAML parser: scalars, inline lists [a, b], block lists,
# list-of-maps (tools), nested dicts, folded multi-line scalars.
# ---------------------------------------------------------------------------

def _strip_comment(text):
    """Remove a ' #' comment that sits outside of quotes."""
    in_single = False
    in_double = False
    for i, ch in enumerate(text):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if i > 0 and text[i - 1] in (" ", "\t"):
                return text[:i].rstrip()
    return text


def _split_top_commas(text):
    parts = []
    cur = []
    in_single = False
    in_double = False
    for ch in text:
        if ch == "'" and not in_double:
            in_single = not in_single
            cur.append(ch)
        elif ch == '"' and not in_single:
            in_double = not in_double
            cur.append(ch)
        elif ch == "," and not in_single and not in_double:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def _scalar(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        inner = text[1:-1]
        if text[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        else:
            inner = inner.replace("''", "'")
        return inner
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_scalar(p) for p in _split_top_commas(inner)]
    low = text.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "~", ""):
        return None
    return text


def split_frontmatter(text):
    """Return (fm_lines, body, error). fm_lines excludes the --- delimiters."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, "frontmatter missing: file must start with ---"
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:]), None
    return None, text, "frontmatter missing: no closing --- found"


def parse_frontmatter_block(fm_lines):
    """Parse frontmatter lines. Returns (data, errors).

    errors is a list of (line_no, message) where line_no is 1-based
    within the frontmatter block (add 1 for the file line number).
    """
    data = {}
    errors = []

    cur_key = None
    mode = None            # None | "scalar" | "block"
    lst = []
    lst_is_maps = False
    entry = None
    dct = {}
    seen_dash = False

    def store_block():
        if seen_dash:
            data[cur_key] = lst
        elif dct:
            data[cur_key] = dct
        else:
            data[cur_key] = []

    for idx, raw in enumerate(fm_lines):
        lineno = idx + 1
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0:
            if cur_key is not None and mode == "block":
                store_block()
            m = KEY_RE.match(stripped)
            if not m:
                errors.append((lineno, "cannot parse line as 'key: value'"))
                cur_key = None
                mode = None
                continue
            key = m.group(1)
            val = (m.group(2) or "").strip()
            if val == "":
                cur_key = key
                mode = "block"
                lst = []
                dct = {}
                lst_is_maps = False
                seen_dash = False
                entry = None
            else:
                data[key] = _scalar(val)
                cur_key = key
                mode = "scalar"
                entry = None
        else:
            if cur_key is None:
                errors.append((lineno, "indented line has no parent key"))
                continue
            if stripped == "-" or stripped.startswith("- "):
                if mode != "block":
                    errors.append((lineno, "list item outside of a block list"))
                    continue
                seen_dash = True
                item = stripped[1:].strip()
                m = KEY_RE.match(item)
                if m:
                    if lst and not lst_is_maps:
                        errors.append((lineno, "mixed list item types "
                                              "(scalars and maps)"))
                        continue
                    lst_is_maps = True
                    entry = {m.group(1): _scalar((m.group(2) or "").strip())}
                    lst.append(entry)
                else:
                    if lst_is_maps:
                        errors.append((lineno, "mixed list item types "
                                              "(maps and scalars)"))
                        continue
                    lst.append(_scalar(item))
                    entry = None
            else:
                m = KEY_RE.match(stripped)
                if m and entry is not None and mode == "block" and seen_dash:
                    entry[m.group(1)] = _scalar((m.group(2) or "").strip())
                elif m and mode == "block" and not seen_dash:
                    dct[m.group(1)] = _scalar((m.group(2) or "").strip())
                elif (mode == "scalar" and isinstance(data.get(cur_key), str)):
                    data[cur_key] = data[cur_key] + " " + stripped
                else:
                    errors.append((lineno, "cannot parse indented line"))

    if cur_key is not None and mode == "block":
        store_block()
    return data, errors


# ---------------------------------------------------------------------------
# Artifact discovery
# ---------------------------------------------------------------------------

def find_skills():
    """Return (domain, name, skill_md_path, parent) tuples, sorted.

    parent is None for top-level skills. Sub-skills live at
    skills/<domain>/<skill>/sub/<sub>/SKILL.md and carry the parent
    skill name.
    """
    found = []
    if not os.path.isdir(SKILLS_DIR):
        return found
    for domain in sorted(os.listdir(SKILLS_DIR)):
        dpath = os.path.join(SKILLS_DIR, domain)
        if not os.path.isdir(dpath):
            continue
        for name in sorted(os.listdir(dpath)):
            spath = os.path.join(dpath, name)
            if not os.path.isdir(spath):
                continue
            found.append((domain, name, os.path.join(spath, "SKILL.md"), None))
            subdir = os.path.join(spath, "sub")
            if not os.path.isdir(subdir):
                continue
            for sub in sorted(os.listdir(subdir)):
                subpath = os.path.join(subdir, sub)
                if not os.path.isdir(subpath):
                    continue
                found.append((domain, sub,
                              os.path.join(subpath, "SKILL.md"), name))
    return found


def find_agents():
    """Return (name, agent_md_path) tuples, sorted."""
    found = []
    if not os.path.isdir(AGENTS_DIR):
        return found
    for name in sorted(os.listdir(AGENTS_DIR)):
        apath = os.path.join(AGENTS_DIR, name)
        if not os.path.isdir(apath):
            continue
        found.append((name, os.path.join(apath, "AGENT.md")))
    return found


def find_brains():
    """Return (name, brain_md_path) tuples, sorted."""
    found = []
    if not os.path.isdir(BRAINS_DIR):
        return found
    for name in sorted(os.listdir(BRAINS_DIR)):
        bpath = os.path.join(BRAINS_DIR, name)
        if not os.path.isdir(bpath):
            continue
        found.append((name, os.path.join(bpath, "BRAIN.md")))
    return found


def find_playbooks():
    """Return (name, playbook_md_path) tuples, sorted."""
    found = []
    if not os.path.isdir(PLAYBOOKS_DIR):
        return found
    for name in sorted(os.listdir(PLAYBOOKS_DIR)):
        ppath = os.path.join(PLAYBOOKS_DIR, name)
        if not os.path.isdir(ppath):
            continue
        found.append((name, os.path.join(ppath, "PLAYBOOK.md")))
    return found


def find_workflows():
    """Return (name, md_path) tuples for workflows/<pattern>.md, sorted.

    README.md in the workflows dir is documentation, not a workflow.
    """
    found = []
    if not os.path.isdir(WORKFLOWS_DIR):
        return found
    for fname in sorted(os.listdir(WORKFLOWS_DIR)):
        if not fname.endswith(".md") or fname == "README.md":
            continue
        fpath = os.path.join(WORKFLOWS_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        found.append((fname[:-3], fpath))
    return found


def _rel(path):
    return os.path.relpath(path, REPO_ROOT)


def _parse_md_file(path, errors):
    """Read a markdown file with frontmatter. Returns (rel, data, body)
    or None when the file is unreadable or has no usable frontmatter."""
    rel = _rel(path)
    try:
        with open(path, encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError:
        errors.append("%s:0: file not found" % _rel(os.path.dirname(path)))
        return None

    fm_lines, body, fm_err = split_frontmatter(text)
    if fm_err:
        errors.append("%s:1: %s" % (rel, fm_err))
        return None
    data, perrs = parse_frontmatter_block(fm_lines)
    for lineno, msg in perrs:
        errors.append("%s:%d: frontmatter: %s" % (rel, lineno + 1, msg))
    if perrs and not data:
        return None
    return rel, data, body


def _check_name_slug(rel, data, want_name, errors):
    nm = data.get("name")
    if isinstance(nm, str):
        if nm != want_name:
            errors.append("%s:1: name '%s' does not match directory name '%s'"
                          % (rel, nm, want_name))
        if not SLUG_RE.match(nm):
            errors.append("%s:1: name '%s' is not a lowercase slug (a-z0-9-)"
                          % (rel, nm))
    elif "name" in data:
        errors.append("%s:1: name must be a string" % rel)


def _check_description(rel, data, errors, require_trigger=True):
    desc = data.get("description")
    if isinstance(desc, str):
        n = len(desc)
        if n < 80 or n > 1500:
            errors.append("%s:1: description is %d chars, must be 80 to 1500"
                          % (rel, n))
        if require_trigger:
            low = desc.lower()
            if "use when" not in low and "when the" not in low:
                errors.append("%s:1: description lacks a trigger phrase "
                              "('use when' or 'when the')" % rel)
    elif "description" in data:
        errors.append("%s:1: description must be a string" % rel)


def _check_version(rel, data, errors):
    ver = data.get("version")
    if isinstance(ver, str):
        if not SEMVER_RE.match(ver):
            errors.append("%s:1: version '%s' is not semver X.Y.Z" % (rel, ver))
    elif "version" in data:
        errors.append("%s:1: version must be a string" % rel)


def _check_kind(rel, data, want_kind, errors):
    kind = data.get("kind")
    if isinstance(kind, str):
        if kind != want_kind:
            errors.append("%s:1: kind '%s' must be '%s'" % (rel, kind, want_kind))
    elif "kind" in data:
        errors.append("%s:1: kind must be a string" % rel)


def _check_missing_fields(rel, data, required, errors):
    for field in required:
        if field not in data:
            errors.append("%s:1: missing required frontmatter field '%s'"
                          % (rel, field))


def _check_string_list(rel, data, field, errors, known=None, known_label=""):
    """Validate a frontmatter list of strings, optionally against a set of
    known names. Returns the list of valid strings (possibly empty)."""
    refs = data.get(field)
    if not isinstance(refs, list):
        if field in data:
            errors.append("%s:1: %s must be a list" % (rel, field))
        return []
    out = []
    for ref in refs:
        if not isinstance(ref, str):
            errors.append("%s:1: %s entries must be strings" % (rel, field))
        elif known is not None and ref not in known:
            errors.append("%s:1: %s references unknown %s '%s'"
                          % (rel, field, known_label, ref))
        else:
            out.append(ref)
    return out


# ---------------------------------------------------------------------------
# Per-skill validation (top-level and sub-skills)
# ---------------------------------------------------------------------------

def validate_skill(domain, name, path, skill_names, errors,
                   parent=None, top_skill_names=None):
    """Validate one SKILL.md (top-level or sub-skill).

    Returns {"requires": [...], "extends": [...], "parent": name|None}
    for cycle detection, or None when the frontmatter is unusable.
    parent is the enclosing skill name for sub-skills, else None.
    """
    parsed = _parse_md_file(path, errors)
    if parsed is None:
        return None
    rel, data, body = parsed
    is_sub = parent is not None

    _check_missing_fields(rel, data,
                          SUB_REQUIRED_FIELDS if is_sub else REQUIRED_FIELDS,
                          errors)
    _check_name_slug(rel, data, name, errors)
    _check_description(rel, data, errors, require_trigger=True)
    _check_version(rel, data, errors)

    dom = data.get("domain")
    if isinstance(dom, str):
        if dom not in DOMAINS:
            errors.append("%s:1: domain '%s' is not one of the %d known "
                          "domains" % (rel, dom, len(DOMAINS)))
    elif "domain" in data:
        errors.append("%s:1: domain must be a string" % rel)

    life = data.get("lifecycle")
    if isinstance(life, str):
        if life not in LIFECYCLES:
            errors.append("%s:1: lifecycle '%s' must be one of: %s"
                          % (rel, life, ", ".join(LIFECYCLES)))
    elif "lifecycle" in data:
        errors.append("%s:1: lifecycle must be a string" % rel)

    lv = data.get("last_verified")
    if isinstance(lv, str):
        if not DATE_RE.match(lv):
            errors.append("%s:1: last_verified '%s' must be YYYY-MM-DD"
                          % (rel, lv))
        else:
            try:
                datetime.strptime(lv, "%Y-%m-%d")
            except ValueError:
                errors.append("%s:1: last_verified '%s' is not a real "
                              "calendar date" % (rel, lv))
    elif "last_verified" in data:
        errors.append("%s:1: last_verified must be a string" % rel)

    for field in ("requires", "extends", "relates"):
        _check_string_list(rel, data, field, errors,
                           known=skill_names, known_label="skill")

    tools = data.get("tools")
    if isinstance(tools, list):
        for i, tool in enumerate(tools):
            if not isinstance(tool, dict):
                errors.append("%s:1: tools[%d] must be a mapping with "
                              "name and version" % (rel, i))
                continue
            tname = tool.get("name")
            tver = tool.get("version")
            if not isinstance(tname, str) or not tname.strip():
                errors.append("%s:1: tools[%d] is missing a name" % (rel, i))
            if not isinstance(tver, str) or not tver.strip():
                errors.append("%s:1: tools[%d] is missing a version" % (rel, i))
    elif "tools" in data:
        errors.append("%s:1: tools must be a list" % rel)

    body_lines = body.splitlines()
    for heading in REQUIRED_HEADINGS:
        if not any(line.strip() == heading for line in body_lines):
            errors.append("%s:1: body is missing the exact heading '%s'"
                          % (rel, heading))

    if is_sub:
        par = data.get("parent")
        if isinstance(par, str):
            if top_skill_names is not None and par not in top_skill_names:
                errors.append("%s:1: parent '%s' is not a real top-level "
                              "skill" % (rel, par))
            if par != parent:
                errors.append("%s:1: parent '%s' does not match the "
                              "enclosing skill directory '%s'"
                              % (rel, par, parent))
        elif "parent" in data:
            errors.append("%s:1: parent must be a string" % rel)

    reqs = data.get("requires")
    exts = data.get("extends")
    return {
        "requires": [r for r in reqs if isinstance(r, str)]
                    if isinstance(reqs, list) else [],
        "extends": [e for e in exts if isinstance(e, str)]
                   if isinstance(exts, list) else [],
        "parent": parent,
    }


# ---------------------------------------------------------------------------
# Per-agent validation
# ---------------------------------------------------------------------------

def validate_agent(name, path, skill_names, brain_names, errors):
    """Validate one agents/<name>/AGENT.md."""
    parsed = _parse_md_file(path, errors)
    if parsed is None:
        return
    rel, data, _body = parsed

    _check_missing_fields(rel, data, AGENT_REQUIRED_FIELDS, errors)
    _check_name_slug(rel, data, name, errors)
    _check_kind(rel, data, "agent", errors)
    _check_description(rel, data, errors, require_trigger=True)
    _check_version(rel, data, errors)

    role = data.get("role")
    if isinstance(role, str):
        if not role.strip():
            errors.append("%s:1: role must be a non-empty string" % rel)
    elif "role" in data:
        errors.append("%s:1: role must be a string" % rel)

    _check_string_list(rel, data, "skills", errors,
                       known=skill_names, known_label="skill")
    _check_string_list(rel, data, "brains", errors,
                       known=brain_names, known_label="brain")

    mode = data.get("memory_mode")
    if isinstance(mode, str):
        if mode not in MEMORY_MODES:
            errors.append("%s:1: memory_mode '%s' must be one of: %s"
                          % (rel, mode, ", ".join(MEMORY_MODES)))
    elif "memory_mode" in data:
        errors.append("%s:1: memory_mode must be a string" % rel)

    esc = data.get("escalation")
    if isinstance(esc, str):
        full = os.path.normpath(os.path.join(REPO_ROOT, esc))
        if not os.path.isfile(full):
            errors.append("%s:1: escalation file '%s' does not exist"
                          % (rel, esc))
        elif os.path.commonpath([full, DECISIONS_DIR]) != DECISIONS_DIR:
            errors.append("%s:1: escalation '%s' must point at a file under "
                          "decisions/" % (rel, esc))
    elif "escalation" in data:
        errors.append("%s:1: escalation must be a string" % rel)

    constraints = data.get("constraints")
    if isinstance(constraints, list):
        for i, item in enumerate(constraints):
            if not isinstance(item, str) or not item.strip():
                errors.append("%s:1: constraints[%d] must be a non-empty "
                              "string" % (rel, i))
    elif "constraints" in data:
        errors.append("%s:1: constraints must be a list" % rel)


# ---------------------------------------------------------------------------
# Per-brain validation
# ---------------------------------------------------------------------------

def validate_brain(name, path, errors):
    """Validate one brains/<name>/BRAIN.md."""
    parsed = _parse_md_file(path, errors)
    if parsed is None:
        return
    rel, data, _body = parsed

    _check_missing_fields(rel, data, BRAIN_REQUIRED_FIELDS, errors)
    _check_name_slug(rel, data, name, errors)
    _check_kind(rel, data, "brain", errors)
    _check_description(rel, data, errors, require_trigger=False)
    _check_version(rel, data, errors)

    provides = data.get("provides")
    if isinstance(provides, list):
        if not provides:
            errors.append("%s:1: provides must list at least one item" % rel)
        for i, item in enumerate(provides):
            if not isinstance(item, str) or not item.strip():
                errors.append("%s:1: provides[%d] must be a non-empty string"
                              % (rel, i))
    elif "provides" in data:
        errors.append("%s:1: provides must be a list" % rel)

    used_by = data.get("used_by")
    if isinstance(used_by, list):
        for i, item in enumerate(used_by):
            if not isinstance(item, str):
                errors.append("%s:1: used_by[%d] must be a string" % (rel, i))
    elif "used_by" in data:
        errors.append("%s:1: used_by must be a list" % rel)


# ---------------------------------------------------------------------------
# Per-playbook validation
# ---------------------------------------------------------------------------

def _parse_phase_table_bindings(body, rel, errors):
    """Extract bindings from a playbook phase table.

    Looks for a markdown table whose header names the columns
    "owner agent", "skills used", "brains used", and "decision gates".
    Returns a list of (kind, target) tuples where kind is one of
    "agent", "skill", "brain", "decisions".
    """
    bindings = []
    lines = body.splitlines()
    col_index = None
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip().lower() for c in stripped.strip("|").split("|")]
        if col_index is None:
            if "owner agent" in cells and "skills used" in cells:
                col_index = {
                    "agent": cells.index("owner agent"),
                    "skill": cells.index("skills used"),
                    "brain": cells.index("brains used") if "brains used" in cells else None,
                    "decisions": cells.index("decision gates") if "decision gates" in cells else None,
                }
            continue
        if set(cells) <= {"", "-", "---", ":---", "---:", ":---:"}:
            continue
        if all(re.match(r"^:?-+:?$", c) for c in cells):
            continue  # markdown table separator row
        raw_cells = [c.strip() for c in stripped.strip("|").split("|")]
        for kind, idx in col_index.items():
            if idx is None or idx >= len(raw_cells):
                continue
            for target in re.split(r"[,;]", raw_cells[idx]):
                target = target.strip()
                if target and target not in ("-", "n/a", "none"):
                    bindings.append((kind, target))
    return bindings


def validate_playbook(name, path, skill_names, agent_names, brain_names,
                      errors):
    """Validate one playbooks/<name>/PLAYBOOK.md.

    Bindings may be listed in frontmatter ("bindings:" with kind:target
    entries) or in a phase table with "owner agent", "skills used",
    "brains used", and "decision gates" columns. At least one binding
    must be listed, and every binding must resolve.
    """
    parsed = _parse_md_file(path, errors)
    if parsed is None:
        return
    rel, data, body = parsed

    _check_missing_fields(rel, data,
                          [f for f in PLAYBOOK_REQUIRED_FIELDS
                           if f != "bindings"],
                          errors)
    _check_name_slug(rel, data, name, errors)
    _check_kind(rel, data, "playbook", errors)
    _check_description(rel, data, errors, require_trigger=False)
    _check_version(rel, data, errors)

    bindings = []  # (kind, target, where)
    fm_bindings = data.get("bindings")
    if isinstance(fm_bindings, list):
        for i, item in enumerate(fm_bindings):
            if not isinstance(item, str):
                errors.append("%s:1: bindings[%d] must be a string" % (rel, i))
                continue
            m = BINDING_RE.match(item.strip())
            if not m:
                errors.append("%s:1: bindings[%d] '%s' must look like "
                              "'kind:target' (agent:, skill:, brain:, "
                              "decisions:)" % (rel, i, item))
                continue
            bindings.append((m.group(1), m.group(2).strip(), "frontmatter"))
    elif "bindings" in data:
        errors.append("%s:1: bindings must be a list" % rel)
    for kind, target in _parse_phase_table_bindings(body, rel, errors):
        bindings.append((kind, target, "phase table"))

    if not bindings:
        errors.append("%s:1: playbook lists no bindings (add a frontmatter "
                      "'bindings' list or a phase table with 'owner agent', "
                      "'skills used', 'brains used', 'decision gates' "
                      "columns)" % rel)
        return

    for kind, target, where in bindings:
        if kind == "agent" and target not in agent_names:
            errors.append("%s:1: %s references unknown agent '%s'"
                          % (rel, where, target))
        elif kind == "skill" and target not in skill_names:
            errors.append("%s:1: %s references unknown skill '%s'"
                          % (rel, where, target))
        elif kind == "brain" and target not in brain_names:
            errors.append("%s:1: %s references unknown brain '%s'"
                          % (rel, where, target))
        elif kind == "decisions":
            fname = target if target.endswith(".md") else target + ".md"
            full = os.path.normpath(os.path.join(DECISIONS_DIR, fname))
            if not os.path.isfile(full):
                errors.append("%s:1: %s references unknown decisions file "
                              "'%s'" % (rel, where, target))
        elif kind not in ("agent", "skill", "brain", "decisions"):
            errors.append("%s:1: %s has unknown binding kind '%s'"
                          % (rel, where, kind))


# ---------------------------------------------------------------------------
# Per-workflow validation
# ---------------------------------------------------------------------------

WORKFLOW_PHASE_RE = re.compile(
    r"^#{2,3}\s*(phase\b|step\s+sequence\b)", re.IGNORECASE)


def validate_workflow(name, path, errors):
    """Validate one workflows/<pattern>.md.

    The body (after frontmatter, when present) must start with a '# Title'
    line and contain at least one phase section: a '## Phase' or
    '### Phase' heading, or a '## Step sequence' section describing the
    ordered stages.
    """
    rel = _rel(path)
    try:
        with open(path, encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError:
        errors.append("%s:0: workflow file not found" % rel)
        return
    _fm_lines, body, _fm_err = split_frontmatter(text)
    if _fm_err:
        body = text
    lines = [line for line in body.splitlines() if line.strip()]
    if not lines or not re.match(r"^#\s+\S", lines[0]):
        errors.append("%s:1: workflow must start with a '# Title' line" % rel)
    if not any(WORKFLOW_PHASE_RE.match(line.strip()) for line in lines):
        errors.append("%s:1: workflow has no phase section (need a '## Phase' "
                      "heading or a '## Step sequence' section)" % rel)


# ---------------------------------------------------------------------------
# Repo-wide checks
# ---------------------------------------------------------------------------

def check_cycles(deps, errors):
    """DFS cycle detection over requires+extends+parent edges.

    A sub-skill's parent edge is checked for cycles but is NOT a requires
    edge: it never counts toward dependency closure.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {name: WHITE for name in deps}
    stack = []

    def targets(node):
        info = deps[node]
        out = list(info["requires"]) + list(info["extends"])
        if info.get("parent"):
            out.append(info["parent"])
        return out

    def visit(node):
        color[node] = GRAY
        stack.append(node)
        for target in targets(node):
            if target not in deps:
                continue
            if color[target] == GRAY:
                cycle = stack[stack.index(target):] + [target]
                errors.append("repo:0: dependency cycle: %s"
                              % " -> ".join(cycle))
            elif color[target] == WHITE:
                visit(target)
        stack.pop()
        color[node] = BLACK

    for node in sorted(deps):
        if color[node] == WHITE:
            visit(node)


def check_em_dashes(errors):
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        if ".git" in dirnames:
            dirnames.remove(".git")
        for fname in sorted(filenames):
            if not fname.endswith(".md"):
                continue
            path = os.path.join(dirpath, fname)
            rel = _rel(path)
            try:
                with open(path, encoding="utf-8-sig") as fh:
                    for lineno, line in enumerate(fh, 1):
                        count = line.count(EM_DASH)
                        if count:
                            errors.append(
                                "%s:%d: em dash (U+2014) found "
                                "(%d occurrence(s))" % (rel, lineno, count))
            except OSError as exc:
                errors.append("%s:0: cannot read file: %s" % (rel, exc))


def _sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_manifest_dict_key(manifest, key, paths, errors):
    """Check one dict-shaped manifest key: name -> {"sha256": ...}.

    Skipped when the key is absent (older manifests). Every artifact on
    disk must be listed with a matching sha256; every entry must point at
    a real artifact file.
    """
    raw = manifest.get(key)
    if raw is None:
        return
    if not isinstance(raw, dict):
        errors.append('arsenal-manifest.json:1: "%s" must be an object' % key)
        return
    for name in sorted(paths):
        rel = _rel(paths[name])
        info = raw.get(name)
        if not isinstance(info, dict):
            errors.append('%s:1: %s is missing from arsenal-manifest.json '
                          '("%s")' % (rel, name, key))
            continue
        want = info.get("sha256")
        try:
            got = _sha256_of(paths[name])
        except OSError as exc:
            errors.append("%s:1: cannot hash file: %s" % (rel, exc))
            continue
        if not isinstance(want, str) or want.lower() != got:
            errors.append('%s:1: manifest sha256 mismatch ("%s") '
                          "(manifest: %s, disk: %s)"
                          % (rel, key, want, got))
    for mname in sorted(raw):
        if mname not in paths:
            errors.append('arsenal-manifest.json:1: manifest "%s" entry '
                          "'%s' has no matching file" % (key, mname))


def check_manifest(artifact_paths, errors):
    """If arsenal-manifest.json exists, every artifact must be listed with a
    matching sha256 of the file on disk, and every manifest entry must
    point at a real artifact file.

    artifact_paths maps manifest key -> {name: file_path}.
    The "skills" key supports both manifest shapes:
      {"skills": [{"name": ..., "path": ..., "sha256": ...}, ...]}
      {"skills": {name: {"sha256": ...}, ...}}
    Other keys are dict-shaped only.
    """
    if not os.path.isfile(MANIFEST_PATH):
        return
    try:
        with open(MANIFEST_PATH, encoding="utf-8-sig") as fh:
            manifest = json.load(fh)
    except (OSError, ValueError) as exc:
        errors.append("arsenal-manifest.json:1: invalid JSON: %s" % exc)
        return
    if not isinstance(manifest, dict):
        errors.append("arsenal-manifest.json:1: manifest must be a JSON object")
        return

    skill_paths = artifact_paths.get("skills", {})
    raw = manifest.get("skills")
    entries = {}  # name -> (sha256, path or None)
    if isinstance(raw, dict):
        for mname, info in raw.items():
            sha = info.get("sha256") if isinstance(info, dict) else None
            entries[mname] = (sha, None)
    elif isinstance(raw, list):
        for i, info in enumerate(raw):
            if not isinstance(info, dict) or not isinstance(info.get("name"), str):
                errors.append("arsenal-manifest.json:1: skills[%d] must be an "
                              "object with a string name" % i)
                continue
            entries[info["name"]] = (info.get("sha256"), info.get("path"))
    elif raw is not None:
        errors.append('arsenal-manifest.json:1: "skills" must be a list or '
                      "an object")
    else:
        errors.append('arsenal-manifest.json:1: "skills" key is missing')

    for name in sorted(skill_paths):
        rel = _rel(skill_paths[name])
        if name not in entries:
            errors.append("%s:1: skill is missing from arsenal-manifest.json"
                          % rel)
            continue
        want, _ = entries[name]
        try:
            got = _sha256_of(skill_paths[name])
        except OSError as exc:
            errors.append("%s:1: cannot hash file: %s" % (rel, exc))
            continue
        if not isinstance(want, str) or want.lower() != got:
            errors.append("%s:1: manifest sha256 mismatch "
                          "(manifest: %s, disk: %s)" % (rel, want, got))

    for mname in sorted(entries):
        _, mpath = entries[mname]
        if mname not in skill_paths:
            errors.append("arsenal-manifest.json:1: manifest entry '%s' has "
                          "no matching skill directory" % mname)
        elif isinstance(mpath, str):
            full = os.path.normpath(os.path.join(REPO_ROOT, mpath))
            real = os.path.normpath(os.path.dirname(skill_paths[mname]))
            if full != real:
                errors.append("arsenal-manifest.json:1: manifest entry '%s' "
                              "path '%s' does not match skill directory '%s'"
                              % (mname, mpath, os.path.relpath(real, REPO_ROOT)))

    for key in ("sub_skills", "agents", "brains", "playbooks", "workflows"):
        _check_manifest_dict_key(manifest, key,
                                 artifact_paths.get(key, {}), errors)


# ---------------------------------------------------------------------------
# install.sh platform check
# ---------------------------------------------------------------------------

PLATFORM_DOC = os.path.join(REPO_ROOT, "platforms", "PLATFORM_SUPPORT.md")
INSTALL_SH = os.path.join(REPO_ROOT, "install.sh")
PLATFORM_SLUG_RE = re.compile(r"^\s*([a-z0-9-]+)\)")
TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|")


def _platforms_from_install():
    """Parse platform slugs accepted by install.sh --platform.

    Reads the case statement between the PLATFORM_MAP_START and
    PLATFORM_MAP_END markers. Returns (slugs, error) where error is None
    on success.
    """
    try:
        with open(INSTALL_SH, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        return None, "cannot read install.sh: %s" % exc
    inside = False
    slugs = []
    for line in lines:
        if "PLATFORM_MAP_START" in line:
            inside = True
            continue
        if "PLATFORM_MAP_END" in line:
            inside = False
            continue
        if inside:
            m = PLATFORM_SLUG_RE.match(line)
            if m:
                slugs.append(m.group(1))
    if not slugs:
        return None, ("no platforms parsed from install.sh "
                      "(markers PLATFORM_MAP_START/END missing or empty)")
    return slugs, None


def _platforms_from_doc():
    """Parse the Platform column of the table in
    platforms/PLATFORM_SUPPORT.md. Returns (slugs, error)."""
    try:
        with open(PLATFORM_DOC, encoding="utf-8-sig") as fh:
            lines = fh.readlines()
    except OSError as exc:
        return None, "cannot read platforms/PLATFORM_SUPPORT.md: %s" % exc
    slugs = []
    for line in lines:
        m = TABLE_ROW_RE.match(line.strip())
        if not m:
            continue
        slug = m.group(1).strip().strip("`")
        if not SLUG_RE.match(slug) or slug.lower() == "platform":
            continue
        slugs.append(slug)
    if not slugs:
        return None, "no platform rows parsed from platforms/PLATFORM_SUPPORT.md"
    return slugs, None


def check_install_platforms(errors):
    """Every --platform value accepted by install.sh must have a matching
    row in platforms/PLATFORM_SUPPORT.md, and vice versa."""
    install_slugs, install_err = _platforms_from_install()
    if install_err:
        errors.append("install.sh:1: %s" % install_err)
        return
    doc_slugs, doc_err = _platforms_from_doc()
    if doc_err:
        errors.append("platforms/PLATFORM_SUPPORT.md:1: %s" % doc_err)
        return
    install_set = set(install_slugs)
    doc_set = set(doc_slugs)
    for slug in sorted(install_set - doc_set):
        errors.append("install.sh:1: platform '%s' accepted by --platform "
                      "has no row in platforms/PLATFORM_SUPPORT.md" % slug)
    for slug in sorted(doc_set - install_set):
        errors.append("platforms/PLATFORM_SUPPORT.md:1: platform '%s' listed "
                      "in the doc but not accepted by install.sh --platform"
                      % slug)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    errors = []

    skills = find_skills()
    top = [(d, n, p) for d, n, p, parent in skills if parent is None]
    subs = [(d, n, p, parent) for d, n, p, parent in skills if parent is not None]
    all_skill_names = set(n for _, n, _, _ in skills)
    top_skill_names = set(n for _, n, _ in top)

    seen = set()
    for _d, name, path, _parent in skills:
        if name in seen:
            errors.append("%s:0: duplicate skill name '%s' used in more "
                          "than one directory" % (_rel(os.path.dirname(path)),
                                                  name))
        seen.add(name)

    agents = find_agents()
    brains = find_brains()
    playbooks = find_playbooks()
    workflows = find_workflows()
    agent_names = set(n for n, _ in agents)
    brain_names = set(n for n, _ in brains)

    deps = {}
    for domain, name, path in top:
        info = validate_skill(domain, name, path, all_skill_names, errors)
        if info is not None:
            deps[name] = info
    for domain, name, path, parent in subs:
        info = validate_skill(domain, name, path, all_skill_names, errors,
                              parent=parent, top_skill_names=top_skill_names)
        if info is not None:
            deps[name] = info

    for name, path in agents:
        validate_agent(name, path, all_skill_names, brain_names, errors)
    for name, path in brains:
        validate_brain(name, path, errors)
    for name, path in playbooks:
        validate_playbook(name, path, all_skill_names, agent_names,
                          brain_names, errors)
    for name, path in workflows:
        validate_workflow(name, path, errors)

    check_cycles(deps, errors)
    check_em_dashes(errors)
    check_install_platforms(errors)
    check_manifest({
        "skills": {name: path for _, name, path in top
                   if os.path.isfile(path)},
        "sub_skills": {name: path for _, name, path, _ in subs
                       if os.path.isfile(path)},
        "agents": {name: path for name, path in agents
                   if os.path.isfile(path)},
        "brains": {name: path for name, path in brains
                   if os.path.isfile(path)},
        "playbooks": {name: path for name, path in playbooks
                      if os.path.isfile(path)},
        "workflows": {name: path for name, path in workflows
                      if os.path.isfile(path)},
    }, errors)

    if errors:
        for line in errors:
            print(line)
        print("%d error(s) found." % len(errors))
        return 1
    parts = ["%d skill(s)" % len(top)]
    if subs:
        parts.append("%d sub-skill(s)" % len(subs))
    if agents:
        parts.append("%d agent(s)" % len(agents))
    if brains:
        parts.append("%d brain(s)" % len(brains))
    if playbooks:
        parts.append("%d playbook(s)" % len(playbooks))
    if workflows:
        parts.append("%d workflow(s)" % len(workflows))
    print("All checks passed for %s." % ", ".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
