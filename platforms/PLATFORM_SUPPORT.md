# Platform Support

Every AgentArsenal skill is a folder with a `SKILL.md` file (name plus
description frontmatter), which is now a cross-platform standard. This
page lists where each supported platform looks for skills, so
`install.sh --platform <name>` can copy the repo's skills to the right
place. The platform names in the first column are the exact values
accepted by `install.sh --platform` (run `install.sh --list-platforms`
to print this table from the terminal).

## Works with

| Platform | Skills folder path | Agent file path (if any) | Status |
| --- | --- | --- | --- |
| claude-code | `~/.claude/skills/` | `CLAUDE.md` | per vendor docs |
| opencode | `~/.config/opencode/skills/` | `AGENTS.md` | per vendor docs |
| codex-cli | `~/.agents/skills/` | `AGENTS.md` | per vendor docs |
| gemini-cli | `~/.gemini/skills/` or `~/.agents/skills/` | `GEMINI.md` | per vendor docs |
| cursor | `~/.cursor/skills/` or `~/.agents/skills/` | `.muse/rules/` | per vendor docs |
| github-copilot | `~/.copilot/skills/` or `~/.agents/skills/` | `.github/copilot-instructions.md` | per vendor docs |
| amp | `~/.agents/skills/` | `AGENTS.md` | per vendor docs |
| goose | `~/.agents/skills/` | `AGENTS.md` | per vendor docs |
| cline | `~/.agents/skills/` | `.clinerules/` | per vendor docs |
| roo-code | `~/.agents/skills/` | `.roo/rules/` | per vendor docs |
| kilo-code | `~/.agents/skills/` | `AGENTS.md` | per vendor docs |
| zed | `~/.agents/skills/` | `AGENTS.md` | per vendor docs |
| warp | `~/.agents/skills/` | `AGENTS.md` | per vendor docs |
| windsurf | `~/.agents/skills/` | `.windsurfrules` | per vendor docs |
| kiro | `~/.kiro/skills/` | `.kiro/steering/` | per vendor docs |
| qwen-code | `~/.qwen/skills/` or `~/.agents/skills/` | `AGENTS.md` | per vendor docs |
| crush | `~/.agents/skills/` | `AGENTS.md` | per vendor docs |
| aider | - (no skills support) | `AGENTS.md` | per vendor docs |
| continue | `~/.agents/skills/` | `.continuerules` | per vendor docs |

Install target for a platform is the skills folder above plus
`/agent-arsenal`. Example: `--platform opencode` installs into
`~/.config/opencode/skills/agent-arsenal`.

Status note: no row is marked "verified" because none of these
platforms were installed and live-tested in this environment. Every
path above comes from vendor documentation or community guides (see
the notes below), which change over time. If a path is wrong for your
setup, override it with `install.sh --target <dir>`.

## Per-platform notes

### claude-code

Claude Code reads user skills from `~/.claude/skills/` and project
skills from `.claude/skills/`. Skills work through the standard
`SKILL.md` format and also surface as slash commands. Personal memory
lives in `CLAUDE.md`. Restart the session or run `/reload-skills`
after installing.

### opencode

OpenCode has native skills support: a `skill` tool loads skills
on demand from the project `.opencode/skills/` directory and the
global `~/.config/opencode/skills/` directory (it also reads
`.claude/skills/` and `.agents/skills/` for compatibility). Quirk:
OpenCode supports per-skill permissions in `opencode.json`:

```json
{
  "permission": {
    "skill": {
      "nmap-methodology": "allow",
      "*": "ask"
    }
  }
}
```

The last matching rule wins. A `deny` rule hides the skill from the
agent instead of only refusing the call. OpenCode-specific behavior
can go in frontmatter `metadata` (for example
`opencode/slash: "true"` to expose the skill as a `/name` command).

### codex-cli

Codex CLI scans `.agents/skills/` from the working directory up to
the repository root, plus the global `$HOME/.agents/skills/`.
Skills follow the open format and may carry an optional
`agents/openai.yaml` sidecar. Memory file: `AGENTS.md`.

### gemini-cli

Gemini CLI discovers skills in `~/.gemini/skills/` (user) and
`.gemini/skills/` (workspace), with `~/.agents/skills/` accepted as
an alias. When a task matches a skill, Gemini CLI asks to activate it
and shows a confirmation prompt before loading the instructions. Use
`/skills list` and `/skills reload` inside a session to check what
was discovered. Memory file: `GEMINI.md`.

### cursor

Cursor reads skills from `~/.cursor/skills/` (user-wide, the only
folder that syncs to Cursor Cloud Agents) and `.cursor/skills/`
(project), and also scans `~/.agents/skills/` plus Claude Code and
Codex folders for compatibility. A skill placed in a nested project
skills directory is scoped to the files under it. Skills can be
invoked as `/skill-name` or attached with `@skill-name`. Standing
instructions go in `.muse/rules/`.

### github-copilot

GitHub Copilot and VS Code discover skills in `.github/skills/`
(project), `~/.copilot/skills/` (user), and the shared
`~/.agents/skills/`. Skills work in the Copilot cloud agent, code
review, the CLI, and agent mode. Repository instructions go in
`.github/copilot-instructions.md`.

### amp

Amp follows the shared `AGENTS.md` convention and reads skills from
the cross-platform `~/.agents/skills/` folder. Use the shared
standard folder to keep one install working across tools.

### goose

Goose reads skills from the shared `~/.agents/skills/` folder. If
your Goose version does not pick them up, add a pointer line in the
project `AGENTS.md` naming the skills directory.

### cline

Cline natively reads `.clinerules/` (one rule file per rule) and
also picks up `.cursorrules` and `.windsurfrules` as fallbacks. A
`SKILL.md` maps onto Cline by copying the skill body into
`.clinerules/<skill-name>.md` (strip the frontmatter, or keep a
plain heading as the description). The shared `~/.agents/skills/`
folder is also scanned by newer builds.

### roo-code

Roo Code is a Cline fork, so the same rules apply: skills live in
the shared `~/.agents/skills/` folder, and standing instructions go
in `.roo/rules/`. Check the Roo Code docs for your version, since
skill support follows Cline's upstream behavior.

### kilo-code

Kilo Code supports native skills (one `SKILL.md` per folder) and
reads the shared `~/.agents/skills/` folder. The frontmatter `name`
must match the parent directory name, using lowercase letters,
numbers, and single hyphens.

### zed

Zed reads global skills from `~/.agents/skills/` and project-local
skills from the project's `.agents/skills/` folder. Manage them in
Settings under AI, Skills (the User tab shows global skills, each
Project tab shows project skills). Standing instructions go in
`AGENTS.md`.

### warp

Warp reads skills from the shared `~/.agents/skills/` folder. If a
skill does not appear, restart the Warp session and confirm the
skills directory setting in your Warp configuration.

### windsurf

Windsurf's Cascade agent discovers `.agents/skills/` natively, so a
user-wide install goes in `~/.agents/skills/` and a project install
in the project's `.agents/skills/`. Standing rules live in
`.windsurfrules`.

### kiro

Kiro keeps its own skills folder: `.kiro/skills/` per project and
`~/.kiro/skills/` user-wide. Steering files (standing context) live
in `.kiro/steering/`. Kiro skills use the standard `SKILL.md`
format.

### qwen-code

Qwen Code is a fork of Gemini CLI, so it shares the same skill
folders: `~/.qwen/skills/` natively and `~/.agents/skills/` as the
shared alias. Install to `~/.agents/skills/` to share one copy
between Qwen Code, Gemini CLI, and Codex.

### crush

Crush reads skills from the shared `~/.agents/skills/` folder.
Standing instructions go in `AGENTS.md` at the project root.

### aider

Aider has no skills support: it does not scan any skills folder.
Instead, Aider reads `AGENTS.md` (or `CONVENTIONS.md`) at session
start. `--platform aider` does not copy skills; it prints a short
`AGENTS.md` pointer snippet you can paste, naming the skills you
want Aider to follow. This keeps every token cost visible, since
Aider loads the whole file every session.

### continue

Continue reads skills from the shared `~/.agents/skills/` folder.
Project rules live in `.continuerules`. Confirm skill support in
your Continue version, since it follows the shared standard folder.

## After installing

1. Restart your agent session (or use the platform's reload command).
2. Ask the agent to list its skills to confirm the new folders were picked up.
3. If a skill does not trigger, check the trigger words in the skill's
   `description` frontmatter (see HOW_IT_WORKS.md).
