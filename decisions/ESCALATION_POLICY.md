# Escalation Policy

When an agent or operator hits a limit it cannot resolve alone, it escalates.
This policy defines severity tiers, response times, who acts, and how the
escalation is recorded. Every AGENT.md points here (or at a stricter local
policy) via its `escalation` field.

## Severity tiers

### SEV-1: Stop work, get a human now

- Suspected active compromise of client infrastructure during an engagement.
- Any action that could destroy data, brick a device, or affect production
  systems outside the agreed scope.
- Discovery of live credentials, personal data, or illegal material you did
  not expect to find.
- Response time: immediate. Halt the run, preserve state, page the engagement
  lead.
- Who: engagement lead, then the client contact defined in the scope doc.

### SEV-2: Human review before continuing

- A tool behaves unexpectedly against in-scope targets (crash loop, wrong
  host responding, scope boundary unclear).
- A finding that changes the engagement risk picture (e.g. domain admin
  achieved two hours in, critical vuln on a production-adjacent host).
- Response time: within 1 hour during working hours, 4 hours outside them.
- Who: engagement lead. The agent pauses the affected phase; unrelated phases
  may continue.

### SEV-3: Log it, continue, review at the next checkpoint

- Edge cases the skill documents but cannot fully handle (odd banner,
  unsupported firmware version, rate-limited API).
- Minor scope ambiguity that a reasonable reading resolves (a hostname that
  resolves to an in-scope IP, a new subdomain of an in-scope domain).
- Response time: reviewed at the next phase gate or daily standup.
- Who: the agent itself logs it; the reviewer reads the log.

### SEV-4: Note and move on

- Cosmetic issues: typos in docs, slow but working tools, noisy logs.
- Response time: next scheduled review. No page, no pause.

## How to escalate

1. Stop the thing that is escalating (SEV-1/2). Do not try one more thing.
2. Record an episodic memory entry: what happened, what you did, what you
   preserved (see `memory/LIFECYCLE.md`).
3. Notify the owner for the tier above, with: severity, one-line summary,
   what is paused, what evidence exists, and what you need from them.
4. Wait for explicit release before resuming a paused phase. Silence is not
   approval.
5. After resolution, add a procedural memory entry so the next agent does
   not hit the same wall.

## Default ownership (override per engagement)

- SEV-1: engagement lead, backup: project owner (izaz).
- SEV-2: engagement lead.
- SEV-3/4: the operating agent, reviewed by the engagement lead.

## Response time summary

| Tier | Human response | Work state |
| --- | --- | --- |
| SEV-1 | Immediate | Halt everything |
| SEV-2 | 1h (working) / 4h (off hours) | Pause affected phase |
| SEV-3 | Next checkpoint | Continue, log it |
| SEV-4 | Next review | Continue, note it |
