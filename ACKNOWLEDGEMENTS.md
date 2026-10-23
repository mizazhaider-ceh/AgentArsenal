# Acknowledgements

All skill content in this repository is original, written from scratch by the AgentArsenal authors. No passages were copied from any source. The two projects below were studied during the design phase to learn structural ideas and discipline. Both are MIT licensed, and their actual LICENSE files were read and verified before any design work began.

## What was learned from alirezarezvani/claude-skills (MIT, copyright 2025 Alireza Rezvani)

Machine-enforced infrastructure: the idea of derived counters (generated docs that count and summarize the collection automatically), frontmatter CI (a validator that rejects malformed skill metadata), generated documentation (docs built from the skill set itself rather than hand-written), and marketplace manifests (a JSON manifest that exposes skills to plugin systems). These are infrastructure ideas; AgentArsenal implements its own validator, scorer, bundler, and manifest from scratch in original code.

## What was learned from SnailSploit/Claude-Red (MIT, copyright 2024-2025 SnailSploit / Kai Aizen)

Content discipline: the strict skill skeleton (one predictable body structure per skill), trigger-dense descriptions (descriptions written to match the situations that should trigger them), one-skill-one-surface (each skill covers exactly one topic, no sprawl), and authorized-use scoping (explicit statements of what the skill may be used for). These are content conventions; every SKILL.md in AgentArsenal was written fresh following these conventions.

## No endorsement

No endorsement by either project or author is implied. This is not a fork or continuation of either project. The project names and author names appear here and in the README solely as factual attribution, never in branding, marketing, or naming.
