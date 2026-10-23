---
name: tmux-workflows
description: Use when working with tmux 3.4 for persistent terminal
  sessions: creating and managing sessions, windows, and panes, customizing
  key bindings and the status bar in tmux.conf, using copy mode to search
  and copy scrollback, scripting reproducible layouts for projects,
  surviving SSH disconnects with detach and reattach, logging pane output,
  or pairing with a colleague in a shared session. Use when the task
  mentions tmux, terminal multiplexer, persistent sessions, or split
  panes.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [bash-advanced]
tools:
  - name: tmux
    version: 3.4
---

tmux is a terminal multiplexer: it keeps shell sessions alive on the
server, independent of your SSH connection, and tiles them into windows
and panes you can script. The core workflow is attach in the morning,
detach at night, and never lose work to a dropped connection again. This
skill covers tmux 3.4: sessions, windows, panes, copy mode, a practical
tmux.conf, scripted layouts, logging, and shared pairing sessions.

## Quick Workflow

1. Start named sessions per project: `tmux new -s project`.
2. Detach with prefix + d; reattach with `tmux attach -t project`.
3. Split panes for editor/logs/shell; zoom a pane when you need focus.
4. Use copy mode to search scrollback and copy text without a mouse.
5. Put your bindings in `~/.tmux.conf`; reload with prefix + r.
6. Script standard layouts so a project workspace is one command.
7. Log panes for long-running jobs you need to audit later.
8. Share a session for pairing with `tmux attach` on a shared socket.

## 1. Sessions: the unit of persistence

```bash
# New named session
tmux new -s deploy

# List sessions
tmux ls

# Attach (or create if missing)
tmux new -A -s deploy

# Detach from inside: prefix + d  (default prefix is Ctrl-b)
# Kill when done
tmux kill-session -t deploy

# Rename the current session
# prefix + $   (prompt for a new name)
```

Surviving disconnects is the point: start long jobs inside tmux on the
server, detach, close the laptop; the job keeps running and you reattach
later. For jobs that must survive even tmux dying, use systemd or nohup;
tmux survives network drops, not server reboots.

## 2. Windows and panes

```text
prefix + c        new window
prefix + ,        rename window
prefix + n/p      next / previous window
prefix + 0-9      jump to window by number
prefix + &        kill window (confirm)

prefix + %        vertical split (side by side)
prefix + "        horizontal split (stacked)
prefix + arrows   move between panes
prefix + z        zoom pane (toggle fullscreen)
prefix + x        kill pane
prefix + q        show pane numbers, then press one to jump
prefix + { / }    swap panes left / right
prefix + space    cycle pane layouts
```

Resize without the mouse:

```text
prefix + :resize-pane -R 10     grow right by 10 cells
prefix + :resize-pane -D 5      grow down by 5 cells
```

A typical dev layout: window 1 editor, window 2 shell split with logs,
window 3 tests. Name windows (`prefix + ,`) so `tmux ls` reads like a
project map.

## 3. Copy mode: scrollback without a mouse

```text
prefix + [        enter copy mode
  / pattern      search forward, ? backward, n/N next/prev
  space          start selection, Enter copies and exits
  q              exit copy mode
prefix + ]        paste the buffer
```

With vi mode (set in tmux.conf below), copy mode uses vim keys:
`v` starts selection, `y` yanks, just like visual mode.

```bash
# List and manage paste buffers
tmux list-buffers
tmux show-buffer -b 0 | head -20
tmux save-buffer -b 0 /tmp/pane-output.txt
```

## 4. A practical tmux.conf

```bash
cat > ~/.tmux.conf <<'EOF'
# Vi keys in copy mode, mouse on for resizing/scrolling
setw -g mode-keys vi
set -g mouse on

# Bigger scrollback for log-heavy panes
set -g history-limit 50000

# Start numbering at 1 (easier reach) and renumber on close
set -g base-index 1
setw -g pane-base-index 1
set -g renumber-windows on

# Faster key response
set -sg escape-time 10

# Reload config: prefix + r
bind r source-file ~/.tmux.conf \; display "reloaded"

# Sane splits that open in the current directory
bind | split-window -h -c "#{pane_current_path}"
bind - split-window -v -c "#{pane_current_path}"
bind c new-window -c "#{pane_current_path}"

# Vim-style pane movement
bind h select-pane -L
bind j select-pane -D
bind k select-pane -U
bind l select-pane -R

# Status bar: session, window list, date/time
set -g status-bg colour235
set -g status-fg colour231
set -g status-left "#[bold]#S "
set -g status-right "%Y-%m-%d %H:%M"
EOF

# Apply to a running server
tmux source-file ~/.tmux.conf
```

## 5. Scripted layouts

One command builds the whole project workspace:

```bash
cat > ~/bin/workon <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
name="${1:?usage: workon <project-dir>}"
session="$(basename "$name")"
cd "$name"
if ! tmux has-session -t "$session" 2>/dev/null; then
  tmux new-session -d -s "$session" -n editor -c "$PWD"
  tmux new-window -t "$session" -n shell -c "$PWD"
  tmux split-window -h -t "$session:shell" -c "$PWD"
  tmux send-keys -t "$session:shell.1" 'tail -f logs/app.log' Enter
  tmux select-window -t "$session:editor"
fi
tmux attach -t "$session"
EOF
chmod +x ~/bin/workon
workon ~/projects/myapp
```

Patterns used: `new-session -d` (detached build), `-c` for the working
directory, `send-keys ... Enter` to start commands, `-t
session:window.pane` targeting.

## 6. Logging panes

```bash
# Log the current pane to a file (toggle)
# prefix + :pipe-pane -o "cat >> /tmp/deploy.log"
tmux pipe-pane -o "cat >> /tmp/deploy-$(date +%F).log"

# Stop logging
tmux pipe-pane

# Capture the whole scrollback right now
tmux capture-pane -p -S -5000 > /tmp/pane-full.txt
```

Logging is the poor man's audit trail for deploys and incident work:
start it before the risky command, stop after, keep the file.

## 7. Pairing and sharing

```bash
# Two users attach to the same session (read-write both)
tmux -S /tmp/pair attach -t deploy
# Second user: tmux -S /tmp/pair attach -t deploy
# Fix socket permissions so both users can join
chmod 770 /tmp/pair  # plus shared group, or use 777 on trusted boxes

# Read-only observer
tmux attach -t deploy -r
```

Etiquette: announce before typing in a shared session; use the read-only
flag for observers.

## 8. Session hygiene

```bash
# What is running where (find the forgotten job)
tmux ls
for s in $(tmux ls -F '#S'); do echo "== $s"; tmux list-panes -s -t "$s" \
  -F '#W:#P #{pane_current_command}'; done

# Kill dead sessions, keep the list short
tmux kill-session -t old-project

# Server-wide: kill everything (careful)
tmux kill-server
```

## Edge cases

- `tmux attach` says "no sessions": the server died (reboot) or you
  are on a different host; sessions live on the machine where tmux
  runs, not on your laptop.
- Garbage characters after resize: `prefix + r` redraw, or detach and
  reattach; also check `$TERM` matches outside and inside tmux
  (`tmux-256color` or `screen-256color`).
- Copy-paste to the system clipboard over SSH: needs OSC 52 support;
  `set -g set-clipboard on` plus a modern terminal, otherwise paste
  via the buffer file.
- Nested tmux (local tmux + remote tmux): double the prefix for the
  inner session, or set a different prefix remotely to stay sane.
- Scrollback lost on pane close: raise `history-limit`, or log
  important panes from the start.
- `mouse on` steals text selection: hold Shift while selecting to get
  the terminal's native selection back.

## Escalation

- Key binding does nothing: `tmux list-keys | grep <key>` shows the
  binding; `prefix + ?` lists all; check for conflicts with the
  terminal or SSH client.
- Layout script targets the wrong pane: list panes with
  `tmux list-panes -t session -F '#D #W #{pane_current_command}'`
  and fix the `-t` selectors.
- tmux server will not start: stale socket in `/tmp/tmux-<uid>/`;
  remove it if no tmux process is alive (`pgrep tmux`).
- Colors broken inside tmux: set `TERM=tmux-256color` before starting
  the server, and `set -g default-terminal "tmux-256color"` in conf.

## Detection and defender view

tmux sessions are where long-running attacker activity hides: a
detached session survives logout and keeps running implants,
exfiltration loops, or miners. Detect misuse with:

```bash
# Sessions on shared servers: who owns them and what runs inside
tmux ls 2>/dev/null
for s in $(tmux ls -F '#S' 2>/dev/null); do
  echo "== $s"; tmux list-panes -s -t "$s" \
    -F '#{pane_current_command} #{pane_current_path}'; done

# Sockets in /tmp: unexpected tmux servers
ls -la /tmp/tmux-*/ 2>/dev/null
sudo find /tmp -name 'tmux-*' -type d 2>/dev/null

# Processes whose parent is a detached tmux, doing network I/O
ps -ef | grep -iE 'miner|xmrig|ncat|nc ' | grep -v grep
```

Defensive rules: audit tmux sessions on shared jump hosts regularly,
kill orphaned sessions from departed users, restrict socket directory
permissions, and treat an unfamiliar persistent session running network
tools as an incident until proven otherwise. For forensics, pane
scrollback and pipe-pane logs are gold: capture them before killing
anything.

## Key references

- tmux 3.4 manual: https://man.openbsd.org/tmux.1
- tmux GitHub: https://github.com/tmux/tmux
- "tmux 2: Productive Mouse-Free Development" (Hogan): workflow ideas.
- MITRE ATT&CK T1059 context: shells persist via multiplexers too.
