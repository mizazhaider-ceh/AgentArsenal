# AgentArsenal

**24 skills across 15 domains**

AgentArsenal is a unified agent-skills repo: one place that goes deep on both software engineering craft and offensive security practice, with quality enforced by machines, not vibes.

Most skill collections are either engineering-only or security-only, and none of them check their own work. AgentArsenal closes that gap:

- **Per-skill versioning**: every skill carries semver and a changelog entry.
- **Testing harness**: `scripts/validate.py` enforces the frontmatter standard, directory/name rules, and dependency acyclicity in CI.
- **Quality scores**: `scripts/score.py` grades every skill 0-100 on trigger density, command quality, edge cases, references, and more. Merging requires 70+.
- **Dependency graph**: `requires`, `extends`, and `relates` edges between skills are validated and visualized.
- **Freshness tracking**: `last_verified` dates flag stale skills; CI fails on impossible or outdated dates.
- **Lifecycle states**: experimental, stable, deprecated. Deprecated skills stay readable but are excluded from new bundles.
- **Offline bundles**: `scripts/bundle.py` packs skills into a single portable archive with a manifest.
- **Rollback**: every release is a git tag plus a changelog entry, so a bad skill can be reverted cleanly.
- **Marketplace manifest**: `.claude-plugin/marketplace.json` exposes all 24 wave-1 skills to Claude Code directly.

## Quick install

```bash
./install.sh
```

Copies all stable skills into your agent's skill directory and prints what was installed. Run `./install.sh --help` for options.

## Docs

Open `docs/index.html` in a browser for the full browsable reference: all domains, skills, dependency graph, and quality scores.

## Scope

**Authorized security work only.** Red team engagements with written authorization, bug bounty programs within scope, CTF competitions, security research on your own systems, and training labs. See SECURITY.md for the explicit rejection list.

## Credits

This repo was built with original content. The infrastructure ideas it follows were learned from two MIT-licensed projects; see ACKNOWLEDGEMENTS.md for the full, factual attribution.
