#!/usr/bin/env bash
# install.sh: sparse installer for AgentArsenal skills.
#
# Installs chosen skill directories from this repo into a skills target
# (default: ~/.claude/skills/agent-arsenal). Resolves requires/extends deps
# from arsenal-manifest.json, backs up the target before touching it, and
# supports rollback.
#
# Flags:
#   --all                  install every skill in the manifest
#   --category <name>      install one domain (category)
#   --list                 list categories with skill counts, then exit
#   --version <skill@ver>  install one skill at a pinned version
#   --target <dir>         install target (default ~/.claude/skills/agent-arsenal)
#   --dry-run              print what would be copied, change nothing
#   --rollback             restore the most recent backup, then exit
#   --platform <name>      set the install target for a platform's skills
#                          folder (see platforms/PLATFORM_SUPPORT.md), e.g.
#                          --platform opencode. Overrides --target.
#   --list-platforms       print the supported platform table, then exit
#
# No args: interactive category picker.

set -u

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="$REPO_DIR/arsenal-manifest.json"
BACKUP_ROOT="$HOME/.agent-arsenal-backups"
DEFAULT_TARGET="$HOME/.claude/skills/agent-arsenal"

MODE=""
CATEGORY=""
PINNED=""
PLATFORM=""
TARGET="$DEFAULT_TARGET"
DRY_RUN=0

usage() {
    sed -n '2,21p' "$0" | sed 's/^# \?//'
    exit "${1:-0}"
}

have() { command -v "$1" >/dev/null 2>&1; }

# platform_base_dir <name>: print the user-wide skills folder for a
# platform. The platform names here must match the "Platform" column of
# platforms/PLATFORM_SUPPORT.md exactly (CI checks this).
platform_base_dir() {
    # PLATFORM_MAP_START
    case "$1" in
        claude-code)    echo "$HOME/.claude/skills" ;;
        opencode)       echo "$HOME/.config/opencode/skills" ;;
        codex-cli)      echo "$HOME/.agents/skills" ;;
        gemini-cli)     echo "$HOME/.gemini/skills" ;;
        cursor)         echo "$HOME/.cursor/skills" ;;
        github-copilot) echo "$HOME/.copilot/skills" ;;
        amp)            echo "$HOME/.agents/skills" ;;
        goose)          echo "$HOME/.agents/skills" ;;
        cline)          echo "$HOME/.agents/skills" ;;
        roo-code)       echo "$HOME/.agents/skills" ;;
        kilo-code)      echo "$HOME/.agents/skills" ;;
        zed)            echo "$HOME/.agents/skills" ;;
        warp)           echo "$HOME/.agents/skills" ;;
        windsurf)       echo "$HOME/.agents/skills" ;;
        kiro)           echo "$HOME/.kiro/skills" ;;
        qwen-code)      echo "$HOME/.qwen/skills" ;;
        crush)          echo "$HOME/.agents/skills" ;;
        continue)       echo "$HOME/.agents/skills" ;;
        aider)          echo "" ;;  # aider has no skills folder (AGENTS.md only)
        *)              return 1 ;;
    esac
    # PLATFORM_MAP_END
}

# list_platforms: print the supported platform table, then exit.
# Names match the "Platform" column of platforms/PLATFORM_SUPPORT.md.
list_platforms() {
    printf "%-14s %-32s %s\n" "PLATFORM" "SKILLS FOLDER" "NOTES"
    printf "%-14s %-32s %s\n" "--------------" "--------------------------------" "-----"
    printf "%-14s %-32s %s\n" "claude-code" "~/.claude/skills/" ""
    printf "%-14s %-32s %s\n" "opencode" "~/.config/opencode/skills/" "per-skill permissions in opencode.json"
    printf "%-14s %-32s %s\n" "codex-cli" "~/.agents/skills/" ""
    printf "%-14s %-32s %s\n" "gemini-cli" "~/.gemini/skills/" "~/.agents/skills/ also scanned"
    printf "%-14s %-32s %s\n" "cursor" "~/.cursor/skills/" "~/.agents/skills/ also scanned"
    printf "%-14s %-32s %s\n" "github-copilot" "~/.copilot/skills/" "~/.agents/skills/ also scanned"
    printf "%-14s %-32s %s\n" "amp" "~/.agents/skills/" ""
    printf "%-14s %-32s %s\n" "goose" "~/.agents/skills/" ""
    printf "%-14s %-32s %s\n" "cline" "~/.agents/skills/" "also maps to .clinerules/"
    printf "%-14s %-32s %s\n" "roo-code" "~/.agents/skills/" "rules live in .roo/rules/"
    printf "%-14s %-32s %s\n" "kilo-code" "~/.agents/skills/" ""
    printf "%-14s %-32s %s\n" "zed" "~/.agents/skills/" ""
    printf "%-14s %-32s %s\n" "warp" "~/.agents/skills/" ""
    printf "%-14s %-32s %s\n" "windsurf" "~/.agents/skills/" ""
    printf "%-14s %-32s %s\n" "kiro" "~/.kiro/skills/" ""
    printf "%-14s %-32s %s\n" "qwen-code" "~/.qwen/skills/" "~/.agents/skills/ also scanned"
    printf "%-14s %-32s %s\n" "crush" "~/.agents/skills/" ""
    printf "%-14s %-32s %s\n" "aider" "-" "no skills support, use AGENTS.md"
    printf "%-14s %-32s %s\n" "continue" "~/.agents/skills/" ""
    echo ""
    echo "Use: ./install.sh --platform <name> [--all|--category <d>|--version <s@v>]"
    echo "Paths come from platforms/PLATFORM_SUPPORT.md (per vendor docs)."
}

# aider_guidance: aider has no skills folder; print an AGENTS.md pointer
# snippet instead of copying skills, then exit.
aider_guidance() {
    echo "Aider does not support skills: it has no skills folder to install into."
    echo "Instead, add a pointer in your project's AGENTS.md, for example:"
    echo ""
    echo "  ## AgentArsenal skills"
    echo "  Follow these skill folders when the task matches their description:"
    echo "  (see the repo's skills/<domain>/<name>/SKILL.md files)"
    echo ""
    echo "Then run install.sh with --platform <other-platform> to install the"
    echo "skill folders somewhere your agent reads."
}

# copy_dir <src> <dst>: rsync -a when available, else cp -r.
copy_dir() {
    local src="$1" dst="$2"
    mkdir -p "$dst"
    if have rsync; then
        rsync -a "$src"/ "$dst"/
    else
        cp -r "$src"/. "$dst"/
    fi
}

# manifest helpers: operate on arsenal-manifest.json with python3 if present,
# else with a small fallback. python3 is preferred for JSON correctness.
if have python3; then
    mquery() { python3 - "$MANIFEST" "$@"; }
else
    echo "error: python3 is required to read arsenal-manifest.json" >&2
    exit 1
fi

ensure_manifest() {
    if [ ! -f "$MANIFEST" ]; then
        echo "error: $MANIFEST not found. Run scripts/derive_manifest.py first." >&2
        exit 1
    fi
}

# list_categories: prints "<category> <count>" per line.
list_categories() {
    mquery <<'EOF'
import json, sys, collections
with open(sys.argv[1]) as f:
    manifest = json.load(f)
counts = collections.Counter(s["domain"] for s in manifest.get("skills", []))
for domain in sorted(counts):
    print("%s %d" % (domain, counts[domain]))
EOF
}

# resolve_skills <arg>: print the final set of skill names (one per line),
# including requires/extends deps. <arg> is a filter expression understood
# by the embedded python: all, category=NAME, or skill=NAME@VERSION.
resolve_skills() {
    local filter_expr="$1"
    mquery "$filter_expr" <<'EOF'
import json, sys
manifest_path, filter_expr = sys.argv[1], sys.argv[2]
with open(manifest_path) as f:
    manifest = json.load(f)
skills = {s["name"]: s for s in manifest.get("skills", [])}

selected = []
if filter_expr == "all":
    selected = list(skills.values())
elif filter_expr.startswith("category="):
    domain = filter_expr.split("=", 1)[1]
    selected = [s for s in skills.values() if s["domain"] == domain]
    if not selected:
        print("error: unknown category '%s'" % domain, file=sys.stderr)
        sys.exit(2)
elif filter_expr.startswith("skill="):
    name, _, version = filter_expr.split("=", 1)[1].partition("@")
    s = skills.get(name)
    if not s:
        print("error: unknown skill '%s'" % name, file=sys.stderr)
        sys.exit(2)
    if version and s.get("version") != version:
        print("error: version mismatch for '%s': manifest has %s, requested %s"
              % (name, s.get("version"), version), file=sys.stderr)
        sys.exit(3)
    selected = [s]
else:
    print("error: bad filter '%s'" % filter_expr, file=sys.stderr)
    sys.exit(2)

# Dependency closure over requires + extends.
result = {}
stack = list(selected)
while stack:
    s = stack.pop()
    if s["name"] in result:
        continue
    result[s["name"]] = s
    for dep in (s.get("requires") or []) + (s.get("extends") or []):
        if dep not in skills:
            print("warning: '%s' depends on unknown skill '%s'"
                  % (s["name"], dep), file=sys.stderr)
            continue
        stack.append(skills[dep])

for name in sorted(result):
    print(name)
EOF
}

# skill_path <name>: print the repo-relative skill path from the manifest.
skill_path() {
    mquery "$1" <<'EOF'
import json, sys
with open(sys.argv[1]) as f:
    manifest = json.load(f)
name = sys.argv[2]
for s in manifest.get("skills", []):
    if s["name"] == name:
        print(s["path"])
        break
EOF
}

do_backup() {
    local target="$1"
    if [ ! -d "$target" ]; then
        return 0
    fi
    local stamp
    stamp="$(date +%Y%m%d-%H%M%S)"
    local dest="$BACKUP_ROOT/$stamp"
    mkdir -p "$BACKUP_ROOT"
    copy_dir "$target" "$dest"
    echo "Backup of existing target saved to: $dest"
    echo "$dest"
}

do_rollback() {
    local latest
    latest="$(ls -1 "$BACKUP_ROOT" 2>/dev/null | sort | tail -n 1)"
    if [ -z "$latest" ]; then
        echo "error: no backups found in $BACKUP_ROOT" >&2
        exit 1
    fi
    local src="$BACKUP_ROOT/$latest"
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "[dry-run] would restore $src -> $TARGET"
        return 0
    fi
    rm -rf "$TARGET"
    mkdir -p "$TARGET"
    copy_dir "$src" "$TARGET"
    echo "Rolled back $TARGET from backup $latest"
}

install_names() {
    local names="$1"   # newline-separated skill names
    local count=0
    local dry="$DRY_RUN"

    # Only back up when we will actually change something.
    if [ "$dry" -eq 0 ]; then
        do_backup "$TARGET" >/dev/null 2>&1 || true
    fi

    while IFS= read -r name; do
        [ -n "$name" ] || continue
        local rel
        rel="$(skill_path "$name")"
        [ -n "$rel" ] || { echo "warning: no path for skill '$name', skipping" >&2; continue; }
        local src="$REPO_DIR/$rel"
        if [ ! -d "$src" ]; then
            echo "warning: source dir missing for '$name' ($src), skipping" >&2
            continue
        fi
        local dst="$TARGET/$rel"
        if [ "$dry" -eq 1 ]; then
            echo "[dry-run] would copy $rel -> $TARGET/$rel"
        else
            copy_dir "$src" "$dst"
            echo "installed: $name ($rel)"
        fi
        count=$((count + 1))
    done <<< "$names"

    if [ "$dry" -eq 1 ]; then
        echo ""
        echo "$count skill(s) would be installed into $TARGET."
    else
        echo ""
        echo "$count skill(s) installed into $TARGET."
        echo "Next steps: restart your agent or rescan the skills directory so"
        echo "the new skills are picked up, then ask your agent to list them."
    fi
}

interactive_picker() {
    ensure_manifest
    local -a cats=()
    while IFS= read -r line; do
        cats+=("$line")
    done < <(list_categories)
    if [ "${#cats[@]}" -eq 0 ]; then
        echo "No skills in the manifest yet. Nothing to install." >&2
        exit 1
    fi
    echo "AgentArsenal: pick a category to install (Ctrl-C to cancel)."
    echo ""
    local PS3="Category number> "
    local opts=()
    for c in "${cats[@]}"; do
        opts+=("$c")
    done
    opts+=("all")
    select choice in "${opts[@]}"; do
        if [ -z "$choice" ]; then
            echo "Invalid choice, try again." >&2
            continue
        fi
        if [ "$choice" = "all" ]; then
            resolve_skills "all" > /tmp/arsenal-install-names.$$
        else
            local cat="${choice%% *}"
            resolve_skills "category=$cat" > /tmp/arsenal-install-names.$$
        fi
        install_names "$(cat /tmp/arsenal-install-names.$$)"
        rm -f /tmp/arsenal-install-names.$$
        break
    done
}

main() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --all)        MODE="all"; shift ;;
            --category)   MODE="category"; CATEGORY="${2:?missing category name}"; shift 2 ;;
            --list)       MODE="list"; shift ;;
            --version)    MODE="version"; PINNED="${2:?missing skill@version}"; shift 2 ;;
            --target)     TARGET="$2"; shift 2 ;;
            --dry-run)    DRY_RUN=1; shift ;;
            --rollback)   MODE="rollback"; shift ;;
            --platform)   PLATFORM="${2:?missing platform name}"; shift 2 ;;
            --list-platforms) MODE="list-platforms"; shift ;;
            -h|--help)    usage 0 ;;
            *)            echo "error: unknown flag $1" >&2; usage 1 ;;
        esac
    done

    if [ -n "$PLATFORM" ]; then
        if [ "$PLATFORM" = "aider" ]; then
            aider_guidance
            exit 0
        fi
        local base
        base="$(platform_base_dir "$PLATFORM")" || {
            echo "error: unknown platform '$PLATFORM'" >&2
            echo "run: ./install.sh --list-platforms" >&2
            exit 1
        }
        TARGET="$base/agent-arsenal"
    fi

    case "$MODE" in
        list-platforms)
            list_platforms
            ;;
        list)
            ensure_manifest
            local cats
            cats="$(list_categories)"
            if [ -z "$cats" ]; then
                echo "No skills in the manifest yet."
            else
                echo "Category  Skills"
                echo "--------  ------"
                while IFS= read -r line; do
                    printf "%-10s %s\n" "${line%% *}" "${line##* }"
                done <<< "$cats"
            fi
            ;;
        rollback)
            do_rollback
            ;;
        all)
            ensure_manifest
            names="$(resolve_skills all)" || exit $?
            install_names "$names"
            ;;
        category)
            ensure_manifest
            names="$(resolve_skills "category=$CATEGORY")" || exit $?
            install_names "$names"
            ;;
        version)
            ensure_manifest
            names="$(resolve_skills "skill=$PINNED")" || exit $?
            install_names "$names"
            ;;
        "")
            interactive_picker
            ;;
    esac
}

main "$@"
