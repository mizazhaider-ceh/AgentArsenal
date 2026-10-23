#!/usr/bin/env python3
"""AgentArsenal CI validator (stdlib only).

Validates every skills/<domain>/<skill>/SKILL.md against SPEC.md.
Prints file:line style errors and exits non-zero on ANY failure.
Handles zero skills gracefully (exit 0).
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO_ROOT, "skills")
MANIFEST_PATH = os.path.join(REPO_ROOT, "arsenal-manifest.json")

DOMAINS = [
    "recon", "network", "web", "auth", "privesc", "ad", "c2",
    "engineering", "incident", "forensics", "linux", "api",
    "cloud", "crypto", "bugbounty",
]
LIFECYCLES = ["experimental", "stable", "deprecated"]
REQUIRED_FIELDS = [
    "name", "description", "version", "domain", "lifecycle",
    "last_verified", "requires", "extends", "relates", "tools",
]
REQUIRED_HEADINGS = ["## Quick Workflow", "## Edge cases", "## Key references"]
EM_DASH = "\u2014"

SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# key: value where the colon is followed by whitespace or end of line
# (so "http://x" is NOT treated as a mapping)
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:[ \t]+(.*?))?[ \t]*$")


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
# Skill discovery
# ---------------------------------------------------------------------------

def find_skills():
    """Return a list of (domain, name, skill_md_path) tuples, sorted."""
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
            found.append((domain, name, os.path.join(spath, "SKILL.md")))
    return found


def _rel(path):
    return os.path.relpath(path, REPO_ROOT)


# ---------------------------------------------------------------------------
# Per-skill validation
# ---------------------------------------------------------------------------

def validate_skill(domain, name, path, skill_names, errors):
    """Validate one SKILL.md. Returns {"requires": [...], "extends": [...]}
    for cycle detection, or None when the frontmatter is unusable."""
    rel = _rel(path)
    try:
        with open(path, encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError:
        errors.append("%s:0: SKILL.md not found" % _rel(os.path.dirname(path)))
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

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append("%s:1: missing required frontmatter field '%s'"
                          % (rel, field))

    nm = data.get("name")
    if isinstance(nm, str):
        if nm != name:
            errors.append("%s:1: name '%s' does not match directory name '%s'"
                          % (rel, nm, name))
        if not SLUG_RE.match(nm):
            errors.append("%s:1: name '%s' is not a lowercase slug (a-z0-9-)"
                          % (rel, nm))
    elif "name" in data:
        errors.append("%s:1: name must be a string" % rel)

    desc = data.get("description")
    if isinstance(desc, str):
        n = len(desc)
        if n < 80 or n > 1500:
            errors.append("%s:1: description is %d chars, must be 80 to 1500"
                          % (rel, n))
        low = desc.lower()
        if "use when" not in low and "when the" not in low:
            errors.append("%s:1: description lacks a trigger phrase "
                          "('use when' or 'when the')" % rel)
    elif "description" in data:
        errors.append("%s:1: description must be a string" % rel)

    ver = data.get("version")
    if isinstance(ver, str):
        if not SEMVER_RE.match(ver):
            errors.append("%s:1: version '%s' is not semver X.Y.Z" % (rel, ver))
    elif "version" in data:
        errors.append("%s:1: version must be a string" % rel)

    dom = data.get("domain")
    if isinstance(dom, str):
        if dom not in DOMAINS:
            errors.append("%s:1: domain '%s' is not one of the 15 spec domains"
                          % (rel, dom))
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
        refs = data.get(field)
        if isinstance(refs, list):
            for ref in refs:
                if not isinstance(ref, str):
                    errors.append("%s:1: %s entries must be strings" % (rel, field))
                elif ref not in skill_names:
                    errors.append("%s:1: %s references unknown skill '%s'"
                                  % (rel, field, ref))
        elif field in data:
            errors.append("%s:1: %s must be a list" % (rel, field))

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

    reqs = data.get("requires")
    exts = data.get("extends")
    return {
        "requires": [r for r in reqs if isinstance(r, str)] if isinstance(reqs, list) else [],
        "extends": [e for e in exts if isinstance(e, str)] if isinstance(exts, list) else [],
    }


# ---------------------------------------------------------------------------
# Repo-wide checks
# ---------------------------------------------------------------------------

def check_cycles(deps, errors):
    """DFS cycle detection over requires+extends edges."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {name: WHITE for name in deps}
    stack = []

    def visit(node):
        color[node] = GRAY
        stack.append(node)
        for target in deps[node]["requires"] + deps[node]["extends"]:
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


def check_manifest(skill_paths, errors):
    """If arsenal-manifest.json exists, every skill must be listed with a
    matching sha256 of the SKILL.md on disk, and every manifest entry must
    point at a real skill directory.

    Supports both manifest shapes:
      {"skills": [{"name": ..., "path": ..., "sha256": ...}, ...]}
      {"skills": {name: {"sha256": ...}, ...}}
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
    else:
        errors.append("arsenal-manifest.json:1: \"skills\" must be a list or "
                      "an object")
        return

    for name in sorted(skill_paths):
        rel = _rel(skill_paths[name])
        if name not in entries:
            errors.append("%s:1: skill is missing from arsenal-manifest.json"
                          % rel)
            continue
        want, _ = entries[name]
        try:
            with open(skill_paths[name], "rb") as fh:
                got = hashlib.sha256(fh.read()).hexdigest()
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    errors = []
    skills = find_skills()
    skill_names = set(name for _, name, _ in skills)

    seen = set()
    for domain, name, path in skills:
        if name in seen:
            errors.append("%s:0: duplicate skill name '%s' used in more "
                          "than one directory" % (_rel(os.path.dirname(path)),
                                                  name))
        seen.add(name)

    deps = {}
    for domain, name, path in skills:
        info = validate_skill(domain, name, path, skill_names, errors)
        if info is not None:
            deps[name] = info

    check_cycles(deps, errors)
    check_em_dashes(errors)
    check_manifest({name: path for _, name, path in skills
                    if os.path.isfile(path)}, errors)

    if errors:
        for line in errors:
            print(line)
        print("%d error(s) found." % len(errors))
        return 1
    if not skills:
        print("No skills found. All checks passed (0 errors).")
    else:
        print("All checks passed for %d skill(s)." % len(skills))
    return 0


if __name__ == "__main__":
    sys.exit(main())
