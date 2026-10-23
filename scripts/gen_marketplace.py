import json, re, glob, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MP = os.path.join(ROOT, ".claude-plugin", "marketplace.json")

def get_field(fm_lines, key):
    """Extract a possibly multiline field value."""
    out = []
    started = False
    for line in fm_lines:
        m = re.match(r'^' + re.escape(key) + r':\s*(.*)$', line)
        if m and not started:
            started = True
            out.append(m.group(1))
            continue
        if started:
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*\s*:', line):
                break
            out.append(line)
    return '\n'.join(out).strip()

def get_tool_names(fm_lines):
    names = []
    in_tools = False
    for line in fm_lines:
        if re.match(r'^tools:\s*$', line):
            in_tools = True
            continue
        if in_tools:
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*\s*:', line):
                break
            m = re.match(r'^\s*-\s*name:\s*(.+)$', line)
            if m:
                names.append(m.group(1).strip().strip('"').strip("'"))
    return names

mp = json.load(open(MP))
existing = {p["name"]: p for p in mp["plugins"]}

STOP = {"basics", "fundamentals", "methodology", "advanced", "attacks", "testing", "analysis"}
kw_stop = {"basics", "fundamentals", "methodology", "the", "and", "with", "for"}

def keywords_for(name, domain, tool_names):
    kws = [domain]
    for tok in name.split("-"):
        if tok not in STOP and tok not in kws:
            kws.append(tok)
    for t in tool_names:
        tl = t.lower().replace(" ", "-")
        if tl not in kws and len(tl) <= 24:
            kws.append(tl)
    return kws[:6]

def short_desc(desc):
    d = " ".join(desc.split())
    parts = re.split(r'\.\s+', d)
    first = parts[0]
    if not first.endswith("."):
        first += "."
    if len(first) > 220:
        first = first[:217].rsplit(" ", 1)[0] + "..."
    return first

plugins = []
for f in sorted(glob.glob(os.path.join(ROOT, "skills", "*", "*", "SKILL.md"))):
    text = open(f).read()
    parts = text.split("---", 2)
    fm_lines = parts[1].splitlines()
    name = get_field(fm_lines, "name").strip()
    desc = get_field(fm_lines, "description")
    domain = get_field(fm_lines, "domain").strip()
    version = get_field(fm_lines, "version").strip()
    tools = get_tool_names(fm_lines)
    if name in existing:
        plugins.append(existing[name])
    else:
        plugins.append({
            "author": "Muhammad Izaz Haider",
            "category": domain,
            "description": short_desc(desc),
            "keywords": keywords_for(name, domain, tools),
            "name": name,
            "source": "./skills/%s/%s" % (domain, name),
            "version": version or "1.0.0",
        })

plugins.sort(key=lambda p: p["name"])
mp["plugins"] = plugins
json.dump(mp, open(MP, "w"), indent=2, ensure_ascii=False)
open(MP, "a").write("\n")
print("marketplace.json now lists %d plugins" % len(plugins))
missing = [p["name"] for p in plugins if not os.path.isdir(os.path.join(ROOT, p["source"][2:]))]
print("missing source dirs:", missing)
