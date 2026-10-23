---
name: vim-mastery
description: Use when editing text at speed with Vim 9.1: learning motions,
  operators, and text objects, combining them into composable editing
  commands, managing buffers, windows, and tabs, recording and replaying
  macros, using registers and marks, searching and replacing across files,
  editing columns with visual block mode, writing a sane vimrc, or fixing a
  broken Vim configuration. Use when the task mentions vim, vi, text
  editing efficiency, macros, or vimrc configuration.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: []
tools:
  - name: Vim
    version: 9.1
  - name: Neovim
    version: 0.10
---

Vim rewards a simple mental model: motions move, operators act, text
objects select structure, and everything composes. `d` deletes, `w` moves
a word, `i"` selects inside quotes, so `di"` deletes inside quotes and
`ci"` deletes and starts typing. This skill covers Vim 9.1 fluency:
the composable core, buffers and windows, macros, registers, search and
replace, visual block editing, and a maintainable vimrc. Most of it
applies to Neovim 0.10 as well.

## Quick Workflow

1. Learn the grammar first: operator + motion, or operator + text
   object; everything else is vocabulary.
2. Move by meaning (paragraphs, brackets, search), not by character.
3. Edit with text objects (`iw`, `i"`, `ip`, `at`) instead of visual
   selection.
4. Repeat with `.`, record with `q` when `.` is not enough.
5. Navigate files with buffers, splits, and the quickfix list, not one
   file at a time.
6. Search precisely, replace with confirmation on risky patterns.
7. Keep a small, understood vimrc; add plugins only for real pain.
8. Practice one new motion per day until it is muscle memory.

## 1. The composable core

```text
Operators: d delete, c change, y yank (copy), > indent, < dedent,
           gu lowercase, gU uppercase, = auto-indent

Motions:   w next word, b back word, e end of word,
           0 start of line, ^ first non-blank, $ end of line,
           gg first line, G last line, } next paragraph, { prev,
           f{char} find char forward, t{char} till char,
           % matching bracket, * search word under cursor

Text objects: iw inner word, aw a word (with space),
              i" inner quotes, a" around quotes,
              i( i[ i{ inner brackets, a( a[ a{ around,
              ip inner paragraph, ap around paragraph,
              it inner tag, at around tag (HTML/XML)
```

Composition examples (type these, do not memorize lists):

```text
di"     delete inside quotes (keep the quotes)
ci(     change inside parens (delete + insert mode)
yap     yank a paragraph
gUiw    uppercase inner word
>ip     indent paragraph
dt,     delete till comma
ciw     change inner word (the rename-variable workhorse)
```

Counts multiply: `d3w` deletes three words, `y5j` yanks five lines down.

## 2. Moving like you mean it

```text
H M L        top / middle / bottom of screen
Ctrl-d/u     half-page down / up
Ctrl-f/b     full page down / up
zz / zt / zb center / top / bottom the cursor line
n / N        next / previous search match
gd           go to definition (ctags/LSP)
/pattern     search forward, ?pattern backward
```

```bash
# Jump to a line from the shell
vim +42 app.py
vim +/TODO app.py
```

Inside insert mode, `Ctrl-o` runs one normal command then returns:

```text
Ctrl-o A    jump to end of line, stay in insert mode
Ctrl-o zz   center the view without leaving insert mode
```

## 3. Buffers, windows, tabs

```text
:e file       edit (opens in current window)
:ls           list buffers
:b2  / :bnext / :bprev   switch buffers
:bd           delete (close) buffer

:sp / :vsp    horizontal / vertical split
Ctrl-w hjkl   move between splits
Ctrl-w =      equalize split sizes
Ctrl-w o      keep only the current split

:tabnew file  new tab, gt / gT cycle tabs
```

Netrw (built-in file browser) covers 90 percent of file navigation:

```text
:Ex           open netrw in current window
-             go up a directory (inside netrw)
%             create a file, d create a directory
```

For projects, combine with the shell instead of plugins:

```bash
# Open every file matching a pattern, each in an argument slot
vim $(grep -rl "MAX_RETRIES" src/)
# Then :argdo %s/old/new/g | update   (edit all, save all)
```

## 4. Macros: record once, replay everywhere

```text
qa        start recording into register a
...edits...
q         stop recording
@a        replay register a
@@        replay last macro again
10@a      replay 10 times
```

Practical macro: turn a list into quoted CSV values.

```text
# Start:   apple
#          banana
#          cherry
# Record: qa I"<Esc> A",<Esc> j q
# Then: 2@a
# Result: "apple",
#         "banana",
#         "cherry",
```

Recursive macro for "until the end of file": record `q` at the end of
the macro itself (`qa ... j q` then `@a` stops at the last line).

## 5. Registers, marks, and jumps

```text
"ayy       yank line into register a
"ap        paste from register a
"+y / "+p  system clipboard (needs +clipboard build)
"0p        paste last yank (not the last delete)
:reg       show all registers

ma         set mark a at cursor
'a         jump to mark a (line), `a jump exact position
''         jump back to previous position
Ctrl-o/i   jump older / newer through the jump list
```

```bash
# Check clipboard support before relying on "+
vim --version | grep -o '+clipboard'
```

The black hole register `"_` deletes without clobbering the yank:

```text
"_dd       delete line, keep previous yank intact
```

## 6. Search and replace without fear

```text
:%s/old/new/g        whole file
:%s/old/new/gc       confirm each replacement
:'<,'>s/old/new/g    visual selection only
:s/old/new/g         current line
```

Magic modes: `\v` (very magic) makes patterns behave like ERE:

```text
:%s/\v(foo|bar)/X/g      no backslash soup
:%s/\v(\d+)-(\d+)/\2-\1/g   swap number groups
```

```bash
# Replace across many files from the shell (safer preview first)
grep -rl 'old_name' src/ | xargs sed -i 's/old_name/new_name/g'
# Or inside vim with quickfix:
:vimgrep /old_name/ src/**/*.py
:copen        " browse matches
:cfdo %s/old_name/new_name/g | update
```

Case handling: `set ignorecase` + `set smartcase` (lowercase query is
case-insensitive, any uppercase makes it sensitive).

## 7. Visual block mode: column editing

```text
Ctrl-v      visual block select
I / A       insert before / append after every selected line
r{char}     replace the whole block with a char
```

Turn a list into an assignment block:

```text
# Start:        # Select the column before each name with Ctrl-v,
#   apple       # press I, type "name = '", Esc,
#   banana      # then A, type "'," Esc
#   cherry
# Result:
#   name = 'apple',
#   name = 'banana',
#   name = 'cherry',
```

## 8. A sane vimrc

```bash
cat > ~/.vimrc <<'EOF'
" Basics
set nocompatible
syntax on
filetype plugin indent on
set number relativenumber
set cursorline
set encoding=utf-8

" Search
set ignorecase smartcase incsearch hlsearch

" Indentation: spaces, 4 wide, keep it consistent
set expandtab tabstop=4 shiftwidth=4 softtabstop=4
set autoindent smartindent

" Behavior
set hidden            " switch buffers without saving
set mouse=a           " mouse works in terminal vim
set clipboard=unnamedplus
set undofile          " persistent undo across sessions
set undodir=~/.vim/undodir
set wildmenu wildmode=longest:full
set backspace=indent,eol,start

" Leader key and the mappings you will actually use
let mapleader=" "
nnoremap <leader>w :w<CR>
nnoremap <leader>q :q<CR>
nnoremap <leader>f :find<CR>
" Clear search highlight
nnoremap <silent> <leader><space> :nohlsearch<CR>
" Move lines up/down
vnoremap J :m '>+1<CR>gv=gv
vnoremap K :m '<-2<CR>gv=gv

" Find files recursively from cwd
set path+=**
EOF
mkdir -p ~/.vim/undodir
```

Plugins: start with none. Add vim-plug plus one fuzzy finder and one
LSP client only when `:find` and ctags genuinely slow you down. Every
plugin is a dependency you will debug at 2 AM.

## Edge cases

- `vim` opens as `vi` (compatible mode, no arrow keys): your vimrc is
  not loaded; check `:echo $MYVIMRC` and `:set compatible?`.
- Paste mangles indentation: `:set paste` before pasting, `:set
  nopaste` after (or use bracketed paste in a modern terminal).
- Macros break on a slightly different line: add `set nowrapscan`
  awareness, or make the macro end with a search that fails cleanly.
- `d` then `p` pastes the delete, not the yank: use `"0p` for the last
  yank, or delete into the black hole `"_d`.
- Swap files after a crash: `vim -r` lists recoverable sessions;
  delete stale `.swp` files once recovered.
- `Ctrl-s` freezes the terminal: flow control, press `Ctrl-q` to
  resume; disable with `stty -ixon` in your shell rc.

## Escalation

- Vim behaves bizarrely over SSH: check `$TERM` (use
  `xterm-256color`), and test with `vim -u NONE` to rule out your
  config.
- A plugin broke startup: `vim --startuptime /tmp/t.log` shows what
  is slow; bisect plugins by commenting halves of the plug block.
- Key mapping does nothing: `:verbose map <key>` shows what claimed
  it; terminal emulators swallow some keys (Ctrl variants), remap
  around them.
- Still slow on huge files: `set noswapfile`, `syntax off`, and open
  with `vim -u NONE` for emergency edits of multi-GB logs (or use
  `less`/`sed` instead).

## Detection and defender view

Vim artifacts matter in forensics and in spotting tampering: swap files,
undo history, and modelines. Detect misuse and misconfig with:

```bash
# Swap files: unsaved edits, or someone editing where they should not
sudo find / -name '*.swp' -o -name '*.swo' 2>/dev/null | head

# Persistent undo history can leak file contents long after deletion
ls -la ~/.vim/undodir/ 2>/dev/null | head

# Modelines: vim executes options from file headers; malicious modelines
# are a known vector (CVE-2019-20807 and friends)
grep -rn 'vim:' /tmp /var/tmp --include='*' 2>/dev/null | head -5
```

Defensive rules: `set nomodeline` (or `modelines=0`) on any system
where untrusted files are edited, keep Vim patched (modeline and
:source vulnerabilities recur), and remember that editing a file as
root with a user-owned vimrc/plugins runs that code as root; use
`sudo -e` / `sudoedit` or a minimal root vimrc. In forensics, `.swp`
and undo files can recover attacker-edited content.

## Key references

- Vim 9.1 documentation: https://www.vim.org/docs.php
- Vim user manual: https://vimhelp.org/usr_toc.txt.html
- Neovim 0.10 docs: https://neovim.io/doc/
- "Practical Vim" (Drew Neil): the composition model behind this skill.
- vimtutor: run `vimtutor` for the 30-minute interactive basics.
- CVE-2019-20807: modeline code execution (why nomodeline matters).
