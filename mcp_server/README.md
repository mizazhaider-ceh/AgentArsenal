# AgentArsenal MCP server

Exposes the AgentArsenal skills catalog (246 skills, 28 domains) as an
MCP server with three tools:

| Tool | What it does |
| --- | --- |
| `list_skills` | List skills, filtered by `domain` and `lifecycle` |
| `get_skill` | Full SKILL.md content plus metadata, by skill name |
| `search_skills` | Keyword search over name, domain, description, and body |

The server reads `arsenal-manifest.json` and the `skills/` tree next to
it. It is read-only: it never modifies skill content.

## Run it

```bash
cd mcp_server
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ARSENAL_ROOT=/path/to/agent-arsenal .venv/bin/python server.py
```

The server locates the repo root automatically when run from this repo.
From a checkout no extra config is needed: `python server.py` works.

## Connect from Claude Code

Add to `~/.claude.json` (or your project's MCP config):

```json
{
  "mcpServers": {
    "agent-arsenal": {
      "command": "/path/to/agent-arsenal/mcp_server/.venv/bin/python",
      "args": ["/path/to/agent-arsenal/mcp_server/server.py"]
    }
  }
}
```

Restart Claude Code. The three tools appear as
`agent-arsenal__list_skills`, `agent-arsenal__get_skill`, and
`agent-arsenal__search_skills`.

## Connect from any MCP client

Any MCP client that supports stdio servers can use it:

- **Claude Desktop (manual config)**: Settings, Developer, Edit Config,
  add the same JSON entry under `mcpServers`, then restart.
- **Claude Desktop (one-click)**: use the `.mcpb` bundle instead, see
  `docs/distribution/mcpb.md`.
- **Generic clients**: launch the command above over stdio. The server
  speaks MCP over standard input/output, no network ports, no auth.

## Smoke test

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, "mcp_server")
from server import do_list_skills, do_get_skill, do_search_skills
print("total stable:", len(do_list_skills(lifecycle="stable", limit=1000)))
print(do_get_skill("linux-hardening")["description"][:80])
print([s["name"] for s in do_search_skills("nmap", limit=5)])
EOF
```

## Scope note

This server ships the full skill catalog for knowledge and workflow
lookup. The offensive security skills teach authorized practice only;
use them on systems you own or have written permission to test.
