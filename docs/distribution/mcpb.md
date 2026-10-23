# AgentArsenal .mcpb Desktop Extension

A one-click installable Claude Desktop extension (`.mcpb` file) that
bundles the AgentArsenal skills catalog as a local MCP server.

## What the bundle does, honestly

The bundle installs a **read-only** MCP server with three tools:

| Tool | What it does |
| --- | --- |
| `list_skills` | List skills, filtered by domain or lifecycle |
| `get_skill` | Read a skill's full SKILL.md content by name |
| `search_skills` | Keyword search across name, domain, description, body |

It does **not** run any skill's commands for you and it never modifies
skills. It is a catalog browser: Claude reads a skill's content, then
follows the instructions inside it. The offensive security skills teach
authorized practice only; use them on systems you own or have written
permission to test.

The bundle carries the full catalog offline: `arsenal-manifest.json`
plus all 246 SKILL.md files (3.4 MB source, about 1.3 MB zipped). The
only network use is at install time, when the host app fetches the
`mcp` Python package (see "How the server runs" below).

## Bundle layout

```
agent-arsenal.mcpb            (zip archive)
├── manifest.json             MCPB manifest, spec 0.4
├── pyproject.toml            dependencies for the uv runtime
├── icon.png                  bundle icon (from assets/banner.svg)
└── server/
    ├── main.py               the MCP server (copy of mcp_server/server.py)
    └── data/
        ├── arsenal-manifest.json
        └── skills/           the full skills tree
```

Manifest highlights: `name` is `agent-arsenal`, `version` is `3.0.0`,
`server.type` is `uv` with entry point `server/main.py`, tools are
declared statically, license MIT.

## How the server runs

The bundle uses the **`uv` server type** (MCPB manifest spec 0.4). The
host app installs the dependencies from `pyproject.toml` (`mcp>=1.9.0`)
with uv and launches `server/main.py` over stdio. Consequences:

- No Python or dependency setup on your machine; the host handles it.
- The host app must implement MCPB manifest 0.4. Current Claude Desktop
  does. If your app only supports manifest 0.3, use the manual stdio
  config in `mcp_server/README.md` instead.
- Python `>=3.10` is required by the bundled server.

## Build

Stdlib only, no network needed:

```bash
python3 scripts/build_mcpb.py
```

Output: `dist/agent-arsenal.mcpb` (gitignored; kept on disk for
verification). The script validates the manifest, zips the bundle,
then re-opens it to verify `manifest.json` is at the zip root and the
server entry point and catalog data are present. `icon.png` is rendered
from `assets/banner.svg` when `cairosvg` is installed, and omitted
otherwise (the manifest's `icon` field is dropped to match).

To attach the bundle to a GitHub Release, run the script on the tagged
commit and upload `dist/agent-arsenal.mcpb` as a release asset.

## Install (Claude Desktop)

1. Download `agent-arsenal.mcpb` from the GitHub Release assets.
2. Double-click the file, or drag it into Claude Desktop: Settings,
   Extensions, then drop the file (or use the install/import button).
3. Click **Install** in the dialog Claude Desktop shows.
4. Restart Claude Desktop if prompted.

After install, the three tools are available in every conversation. Try:
"list the AgentArsenal skills in the linux domain", then "read me the
linux-hardening skill".

## Uninstall

Claude Desktop, Settings, Extensions, find "AgentArsenal Skills
Catalog", remove. No other traces are left on the machine.

## Troubleshooting

- **Extension does not appear after double-click:** your Claude Desktop
  may predate MCPB manifest 0.4 support. Update Claude Desktop, or use
  the manual stdio server config in `mcp_server/README.md`.
- **Install hangs on dependency download:** the host needs network
  access to PyPI once, to fetch the `mcp` package via uv.
- **Tools return errors:** the server locates its catalog relative to
  itself (`server/data/`); if you unpacked the bundle by hand, keep
  that directory structure intact.
