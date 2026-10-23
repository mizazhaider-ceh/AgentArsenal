---
name: git-workflows
description: Use when choosing a branching model for a team, when writing clean atomic commits, when rebasing a feature branch or resolving rebase conflicts, when running a disciplined pull request review, when adding git hooks for pre-commit checks, and when recovering from mistakes such as bad rebases, deleted branches, or bad commits using reflog, reset, revert, and cherry-pick.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: []
tools:
  - name: git
    version: "2.43"
---

This skill covers team-ready git workflows: choosing a branching model, writing clean atomic commits, rebasing safely, running disciplined pull requests, enforcing quality with hooks, and recovering from the mistakes every team eventually makes. The scope is the daily practice of collaborative git, not git internals. Every section gives the exact commands, because workflow advice without commands does not survive contact with a real repository.

## Quick Workflow

1. Choose the branching model for the repo and write it down where the team can find it.
2. Create a short-lived branch from an up-to-date main. One branch, one task.
3. Commit in small atomic units with clear messages. Commit early, polish later.
4. Rebase onto main regularly so conflicts arrive small and early.
5. Run hooks and tests locally before every push.
6. Open a small, well-described pull request and get a review.
7. Merge with the repo's chosen strategy, delete the branch, verify on main.

## Phase 1: Branching models

Pick one per repo. Mixed models in one repo cause the most confusion.

| Model | How it works | Fits when |
|---|---|---|
| Trunk-based | Short branches (hours to a day), merge to main constantly, release from main | Small team, good CI, frequent releases |
| Feature branch | Branches live days to weeks, PR review, then merge | Larger team, needs review gates per change |
| GitFlow-lite | main plus a develop branch, release branches for stabilization | Versioned releases with maintenance branches |

Trunk-based is the default recommendation. It minimizes merge pain and keeps main always releasable. Whatever you pick, protect main: no direct pushes, require PR review and green CI.

```bash
git checkout -b feat/shorten-urls main
git branch --show-current
git push -u origin feat/shorten-urls
```

Branch naming convention: `feat/...`, `fix/...`, `chore/...`, `docs/...`. Short, lowercase, hyphens, no ticket numbers alone (a human should guess the content).

## Phase 2: Commit hygiene

An atomic commit does one thing and leaves the tree working. Future you, and your reviewers, will bisect and revert these.

```bash
git status --short
git add -p                    # stage hunks selectively, review each one
git commit -m "feat: add --output json to logfilter"
git log --oneline -5
```

Message format (Conventional Commits style):

```text
feat: add --output json to logfilter

The JSONL output lets CI pipelines parse results without
fragile text scraping. Text output is unchanged.

Fixes #42.
```

Rules: subject line under 72 chars, imperative mood ("add", not "added"), body explains why, not what (the diff shows what). Separate concerns into separate commits: a refactor commit and a behavior-change commit should never be the same commit.

```bash
git commit --amend --no-edit   # fold a forgotten file into the last commit (unpushed only)
git rebase -i HEAD~3           # squash, fixup, or reword the last 3 commits
```

In the interactive rebase list: `pick` keeps, `squash` folds with combined message, `fixup` folds silently, `reword` edits the message. Never rewrite commits that someone else has already pulled.

## Phase 3: Rebasing

Rebasing keeps history linear and conflicts small. The golden rule: rebase private branches, merge (or let the platform squash) shared ones.

```bash
git fetch origin
git rebase origin/main
```

When a conflict appears, git stops and marks the files:

```bash
git status --short             # shows UU for conflicted files
# edit the files, resolve the markers
git add <resolved-files>
git rebase --continue
git rebase --abort             # give up and return to the pre-rebase state
git rebase --skip              # drop the conflicting commit (use with care)
```

During conflict resolution, `git diff` shows the conflicted state and `git log --merge --oneline` shows which commits are involved. For generated files (lockfiles, build output), pick a side deliberately and regenerate rather than hand-merging:

```bash
git checkout --theirs package-lock.json
npm install                    # regenerate properly
git add package-lock.json
git rebase --continue
```

Keep the branch current: rebase onto main at least daily on active branches. A week-old branch rebased in one go is where painful conflicts come from.

## Phase 4: Pull request discipline

A good PR is small, described, and reviewable. Aim for under 400 changed lines; split anything bigger and propose the split order yourself.

PR description template:

```text
What: one or two sentences.
Why: the problem this solves, link the issue.
How: approach in a few bullets, including what was NOT done.
Testing: commands run and their result.
Risk: what could break, and how to verify after merge.
```

Review checklist for the author before requesting review:

```bash
git diff origin/main...HEAD --stat   # is it small enough?
git log origin/main..HEAD --oneline # does each commit make sense alone?
# tests pass locally, hooks ran, no debug leftovers, no secrets
rg -n "TODO|FIXME|console\.log|pdb|breakpoint\(\)" --type py -tjs .
```

Merge strategies, one per repo: squash (one commit per PR, clean main history), rebase-merge (keeps atomic commits, linear history), or merge commits (preserves exact branch history). Do not mix strategies PR by PR.

## Phase 5: Hooks

Client-side hooks run automatically and catch cheap mistakes before push. They are a convenience, not a security boundary (they can be skipped with `--no-verify`, so server-side checks still matter).

```bash
cat > .git/hooks/pre-commit <<'EOF'
#!/bin/sh
# block commits with debug leftovers or private keys
if git diff --cached --name-only | xargs grep -n "pdb\.set_trace\|breakpoint()\|console\.log" 2>/dev/null; then
  echo "pre-commit: debug leftovers found, commit blocked"
  exit 1
fi
if git diff --cached --name-only | xargs grep -l "BEGIN .*PRIVATE KEY" 2>/dev/null; then
  echo "pre-commit: private key staged, commit blocked"
  exit 1
fi
EOF
chmod +x .git/hooks/pre-commit
```

A commit-message hook enforces the format from Phase 2:

```bash
cat > .git/hooks/commit-msg <<'EOF'
#!/bin/sh
# require conventional-commit style subject line
head -1 "$1" | grep -Eq "^(feat|fix|docs|chore|refactor|test): .{1,60}$" || {
  echo "commit-msg: subject must look like 'feat: description'"
  exit 1
}
EOF
chmod +x .git/hooks/commit-msg
```

For hooks shared across the team, keep them in the repo (for example `hooks/`) and point git at them:

```bash
git config core.hooksPath hooks/
```

## Phase 6: Recovering from mistakes

Almost everything in git is recoverable. The rule for every scenario below: stop, do not run more commands blindly, and copy the current state aside if you are unsure.

Find lost commits with the reflog (a log of where HEAD has been, kept about 90 days):

```bash
git reflog --oneline | head -20
git reflog show feat/shorten-urls | head -20
```

Recover a deleted branch:

```bash
git reflog --oneline | grep "checkout: moving from"
git branch recovered-branch <sha-from-reflog>
```

Undo the last commit but keep the changes staged:

```bash
git reset --soft HEAD~1
```

Undo the last commit and unstage everything (keeps working tree files):

```bash
git reset HEAD~1
```

Throw away local changes to a file (destructive, files are lost):

```bash
git restore path/to/file
git clean -fd    # remove untracked files and dirs (destructive)
```

Undo a commit that is already pushed: never rewrite, revert instead (creates a new commit that undoes it):

```bash
git revert <sha>
git push
```

Move a commit from the wrong branch to the right one:

```bash
git cherry-pick <sha>        # copy it onto the current branch
git rebase --onto main <bad-commit>~1 <bad-commit>  # or transplant a range
```

Fix the author on recent unpushed commits:

```bash
git rebase -i HEAD~3
# change 'pick' to 'edit' for the bad commits, then for each:
git commit --amend --author="Correct Name <correct@example.com>" --no-edit
git rebase --continue
```

Last resort, when the object database still has the data but no ref points to it:

```bash
git fsck --lost-found
```

## Edge cases

- Force-push to a shared branch: announce it in the team channel first, get explicit agreement, never force-push main. Prefer `git push --force-with-lease`, which refuses if someone else pushed since your last fetch.
- Someone force-pushed over your work: do not rebase blindly. Get the old SHA from the PR page or their reflog, then `git cherry-pick` your commits onto the new tip.
- Committed to main by accident: `git branch rescue` to save it, `git reset --hard origin/main` to restore main, then open a proper PR from the rescue branch.
- Rebase conflict in a binary file: decide with `--ours` or `--theirs` deliberately, never hand-edit binaries.
- Huge files committed: remove them with a history-rewriting tool before they spread to every clone, and coordinate the rewrite with the team. Prevention (a pre-commit size check) beats cure.
- Detached HEAD with new commits: `git branch rescue` immediately to keep them, then move to the branch.

## Escalation

- History is broken and the reflog does not cover it: clone fresh from origin, save your work with `git format-patch` or plain file copies, and replay it onto the clean clone.
- A secret was committed and pushed: rotate the secret FIRST. It is compromised the moment it leaves your machine. Then purge it from history, force-push with team notice, and check where the old commits may have been cloned.
- A shared branch needs a force-push: announce, get agreement, use `--force-with-lease`, verify CI is green after.
- You are unsure whether a destructive command is safe: copy the branch (`git branch backup-<name>`) first. The copy costs nothing and saves everything.

## Detection and defender view

For engineering skills this section covers detecting workflow misuse and repository misconfiguration.

- Secrets in history: sweep with `git log --all -S 'BEGIN PRIVATE KEY' --oneline` and `git log --all -S 'AKIA' --oneline`. Add a secret scanner to CI so new leaks are caught at PR time.
- Misconfiguration: main branch without protection, no required reviews, no required status checks, signed commits required by policy but not enforced, allowlisted bypasses nobody reviews.
- Client-side hooks are bypassable (`--no-verify`), so real enforcement belongs server side: pre-receive hooks or platform branch rules.
- Detect process drift: PRs merged without review, direct pushes to main, force-pushes on protected branches. Most platforms expose these in the audit log; review it monthly.

## Key references

- git-scm.com/docs: git-rebase, git-reflog, git-cherry-pick, git-revert, git-reset, githooks
- Conventional Commits (conventionalcommits.org)
- GitHub flow guide (docs.github.com/en/get-started/using-github/github-flow)
