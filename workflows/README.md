# Workflows

Each workflow is one markdown file directly under this directory:
`workflows/<pattern-name>.md`. Workflows are lightweight patterns, shorter
than playbooks, describing how work moves from intake to done. They carry no
frontmatter requirement; the validator checks structure only.

Every workflow file must contain:

1. A top-level title: the first line is `# <pattern name>`.
2. Phases: at least one `## Phase ...` section describing a stage of the work,
   with entry criteria, actions, and exit criteria.

Example skeleton:

```markdown
# Vulnerability disclosure intake

## Phase 1: Receive
Entry: a report arrives. Actions: acknowledge within one business day...
Exit: report logged with severity guess.

## Phase 2: Triage
...
```

Workflows are written by the workflow content team. This directory currently
holds only this stub.
