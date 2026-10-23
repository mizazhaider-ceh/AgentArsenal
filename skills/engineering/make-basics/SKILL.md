---
name: make-basics
description: "Use when writing or fixing Makefiles with GNU Make 4.4: understanding targets, prerequisites, and recipes, using automatic variables ($@, $<, $^), writing pattern rules, declaring .PHONY targets, using variables and functions (wildcard, patsubst), running parallel builds with -j, debugging with -n and --debug, or converting a pile of shell scripts into a reproducible build. Use when the task mentions Makefile, make targets, build automation, or make errors like \"missing separator\"."
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [git-workflows, python-cli-tooling]
tools:
  - name: GNU Make
    version: 4.4
---
Make builds a dependency graph from a Makefile and rebuilds only what is
stale: if `app` is newer than `main.c`, nothing happens; touch `main.c`
and only the needed steps rerun. That makes it the right tool for
compiled builds and for any repeatable task pipeline (lint, test, build,
deploy). This skill covers GNU Make 4.4: targets, prerequisites, recipes,
variables, pattern rules, functions, phony targets, parallel builds, and
debugging.

## Quick Workflow

1. Name the default target `all`; list the main entry points at the top.
2. Write explicit target: prerequisites rules first, then generalize
   with pattern rules.
3. Declare every non-file target `.PHONY`.
4. Use automatic variables (`$@`, `$<`, `$^`) instead of repeating
   names.
5. Put configuration in variables at the top; override from the
   command line or environment.
6. Test with `make -n` (dry run) before `make`; debug with
   `--debug=b` when rebuilds surprise you.
7. Run `make -j$(nproc)` for parallel builds once the graph is
   correct.
8. Keep recipes portable: POSIX sh by default, one logical line per
   recipe line or joined with backslashes.

## 1. Anatomy: targets, prerequisites, recipes

```make
# Makefile
CC := gcc
CFLAGS := -Wall -Wextra -O2 -g

# target: prerequisites
# <TAB>recipe line (TAB is mandatory, not spaces)
app: main.o util.o
	$(CC) $(CFLAGS) -o $@ $^

main.o: main.c util.h
	$(CC) $(CFLAGS) -c $< -o $@

util.o: util.c util.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f app *.o

.PHONY: all clean
all: app
```

```bash
make            # builds app (first target is the default)
make -n         # dry run: print recipes without running them
make clean && make -j"$(nproc)"
```

Core rules: recipes MUST start with a tab ("missing separator" means
spaces); each recipe line runs in a fresh shell, so `cd` on one line
does not persist (use `; \` continuations or `.ONESHELL`); make decides
staleness by file timestamps.

## 2. Automatic variables

```make
app: main.o util.o
	$(CC) -o $@ $^
# $@ = target name (app)
# $^ = all prerequisites (main.o util.o)
# $< = first prerequisite (main.o)
# $? = prerequisites newer than target
# $* = stem matched by % in pattern rules
# $(@D) / $(@F) = directory / file part of target
```

Use them always: a rule that repeats filenames will drift when the
filenames change.

## 3. Variables and functions

```make
# := immediate (evaluated once), = recursive (evaluated on each use)
BUILD := build
SOURCES := $(wildcard src/*.c)
OBJECTS := $(patsubst src/%.c,$(BUILD)/%.o,$(SOURCES))

# Override from the command line: make CFLAGS="-O0 -g"
CFLAGS ?= -O2

# Functions you will use constantly
FILES := $(wildcard *.md)                 # glob to list
OBJS := $(patsubst %.c,%.o,$(SOURCES))    # pattern substitution
DIRS := $(sort $(dir $(SOURCES)))         # directory parts, deduped
STRIPPED := $(strip $(CFLAGS))            # trim whitespace

$(BUILD)/%.o: src/%.c | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD):
	mkdir -p $@

.PHONY: print-vars
print-vars:
	@echo "SOURCES=$(SOURCES)"
	@echo "OBJECTS=$(OBJECTS)"
```

`|` marks order-only prerequisites: `$(BUILD)` must exist before
compiling, but its timestamp must not trigger rebuilds.

```bash
make print-vars
make CFLAGS="-O0 -g"     # command-line override
```

## 4. Pattern rules and static patterns

```make
# One rule for every .c -> .o (the workhorse)
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Static pattern: apply to a specific list only
$(OBJECTS): $(BUILD)/%.o: src/%.c
	$(CC) $(CFLAGS) -c $< -o $@

# Multiple targets, one recipe
%.h %.c: %.y
	bison -d $<

# Cancel a built-in implicit rule you do not want
%.o: %.s
```

Prefer your own pattern rules over make's built-in implicit rules for
clarity; check what is built in with `make -p | grep -A2 '^%.o'`.

## 5. .PHONY and common task targets

```make
.PHONY: all build test lint clean help

all: build

build: app

test: build
	pytest -q

lint: build
	shellcheck scripts/*.sh
	ruff check src/

clean:
	rm -rf $(BUILD) app *.o

help:
	@echo "Targets:"
	@echo "  build  compile the app"
	@echo "  test   run the test suite"
	@echo "  lint   run linters"
	@echo "  clean  remove build artifacts"
```

Why `.PHONY` matters: without it, a file named `test` or `clean` in
the directory makes make skip the target ("up to date"). Every target
that is not a real file gets `.PHONY`.

## 6. Conditionals and includes

```make
UNAME := $(shell uname -s)

ifeq ($(UNAME),Darwin)
	CFLAGS += -I/opt/homebrew/include
else
	CFLAGS += -pthread
endif

# Optional config file, silently skipped if missing
-include config.mk

ifdef DEBUG
	CFLAGS += -O0 -g -DDEBUG
endif
```

Keep conditionals small; a Makefile full of `ifeq` is a build system
crying for help.

## 7. Parallel builds

```bash
make -j"$(nproc)"        # one job per core
make -j8                 # fixed count
```

For `-j` to be safe, the graph must be complete: every real dependency
must be a prerequisite. Missing prerequisites cause race failures that
vanish on retry (the classic "works with -j1" bug). Mark targets that
must not parallelize:

```make
# These two both write to the same database; serialize them
.NOTPARALLEL: migrate seed
```

## 8. Debugging make

```bash
# Print the database: every variable and rule make sees
make -p | less

# Why did it rebuild? (basic debug)
make --debug=b

# Which makefile, which line defined a variable?
make --debug=v 2>&1 | grep -A2 'CFLAGS'

# Trace recipe execution with the target that triggered it
make --trace

# Check for the tab problem visibly
cat -A Makefile | head -10
# Recipe lines must start with ^I (tab), not spaces
```

Common errors: "missing separator" (spaces instead of tab),
"recipe commences before first target" (a recipe line outside any
rule, often from a stray tab), "No rule to make target" (typo in a
prerequisite or missing file), and circular dependency warnings
(target depends on itself through a chain).

## 9. A complete example: Python project tasks

```make
VENV := .venv
PY := $(VENV)/bin/python

.PHONY: all setup test lint format clean

all: test

setup:
	python3 -m venv $(VENV)
	$(PY) -m pip install -r requirements.txt -r requirements-test.txt

test: setup
	$(PY) -m pytest -q

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff format src/ tests/

clean:
	rm -rf $(VENV) .pytest_cache htmlcov
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
```

Idempotency note: `setup` reruns pip every time here; for real
incremental behavior, use a stamp file:

```make
$(VENV)/.stamp: requirements.txt
	python3 -m venv $(VENV)
	$(PY) -m pip install -r requirements.txt
	touch $@

test: $(VENV)/.stamp
	$(PY) -m pytest -q
```

## Edge cases

- Tabs vs spaces: the eternal trap; configure your editor to keep
  tabs in Makefiles (`:set noexpandtab` in vim for Makefiles).
- `$` in recipes is make syntax: write `$$` for a shell variable
  (`echo $$HOME`), single `$` gets eaten by make.
- Filenames with spaces: make handles them poorly; avoid spaces in
  build trees or use `$(wildcard)` carefully.
- `make clean` deleting too much: scope `rm` to the build dir and
  known patterns, never `rm -rf *`.
- Environment variables vs make variables: `export VAR` in the
  Makefile passes to recipes; command-line assignments override
  everything except `override` directives.
- BSD make vs GNU make: syntax differs (`!=` vs `$(shell)`);
  this skill targets GNU Make 4.4 on Linux.

## Escalation

- Rebuilds everything every time: a prerequisite is newer than the
  target on every run (a `.PHONY` prerequisite, or a generated file
  with a clock-skewed timestamp); inspect with `make --debug=b`.
- Parallel build fails intermittently: incomplete graph; run with
  `-j1` to confirm, then add the missing prerequisites.
- "No rule to make target X": check for typos, check the file
  exists, and check pattern rules actually match (`make -p` shows
  them).
- Variable has an unexpected value: `make print-vars` (section 3)
  plus `make --debug=v` to find where it was set.
- Outgrown make (generated sources, complex matrices): that is the
  signal for CMake, Meson, or a task runner; do not build a second
  build system inside the Makefile.

## Detection and defender view

Makefiles execute arbitrary shell: a malicious Makefile is a
code-execution vector hiding in plain sight, especially via `curl |
bash` recipes or `setup` targets that download binaries. Detect misuse
with:

```bash
# Suspicious recipes: network fetch + execute in build files
grep -rnE 'curl.*\|\s*(ba)?sh|wget.*\|\s*(ba)?sh' --include='Makefile' \
  --include='*.mk' . 2>/dev/null | head

# Makefiles changed recently in unexpected places
find / -name 'Makefile' -mtime -7 2>/dev/null | grep -vE '^/(usr|opt)' | head

# What would this Makefile actually run? Dry-run before trusting it
make -n
```

Defensive rules: read a Makefile before running it (especially from
untrusted repos), never `sudo make install` without reviewing the
install target, pin downloaded artifacts with checksums, and run
builds as an unprivileged user. In CI, treat the Makefile as code:
reviewed, versioned, and scanned like everything else.

## Key references

- GNU Make 4.4 manual: https://www.gnu.org/software/make/manual/
- "Managing Projects with GNU Make" (Mecklenburg): the classic book.
- POSIX make specification: https://pubs.opengroup.org/onlinepubs/9699919799/utilities/make.html
- CWE-78 (OS Command Injection): unsanitized variables in recipes.
- CWE-829 (Inclusion of Functionality from Untrusted Sphere): fetching
  build inputs over the network without verification.
