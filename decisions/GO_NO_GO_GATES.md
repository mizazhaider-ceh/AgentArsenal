# Go / No-Go Gates

An engagement proceeds through five gates. Each gate is a question with a
pass condition. A No-Go at any gate stops the engagement until the condition
is met. Gates are checked in order; a later gate is never used to excuse an
earlier No-Go.

## Gate 1: Authorization

Question: do we have written permission to do exactly this work?

- Pass: a signed scope document names the targets, the time window, the
  allowed techniques, and a client contact. The agent can quote the scope
  line for any action it takes.
- No-Go: verbal permission only, scope document missing, targets described
  vaguely ("the network"), or the time window has expired.
- Remedy: get the written scope. There is no shortcut.

## Gate 2: Safety

Question: can we do this work without harming systems, data, or people?

- Pass: every planned action scores Low or Medium on `RISK_MATRIX.md`, High
  actions have lead approval plus safeguards, no Extreme actions remain.
- No-Go: any Extreme action, or a High action without a documented safeguard
  and rollback plan.
- Remedy: redesign the action (slower, narrower, off-hours) or drop it.

## Gate 3: Capability

Question: do we have the skills, tools, and access to do this well?

- Pass: the needed skills exist in the arsenal (or the gap is named and
  accepted), tools are installed and tested, credentials provided by the
  client work.
- No-Go: core technique missing, tool untested against the target type, or
  access not yet provisioned.
- Remedy: lab-test first, provision access, or narrow the scope to what is
  covered.

## Gate 4: Detection posture

Question: does the client know what to expect, and do we know what they
will see?

- Pass: the client contact confirmed the test window, the SOC or NOC knows
  the source IPs if the engagement is not meant to be stealthy, and the
  defender-view section of each skill used has been read.
- No-Go: unannounced testing against a defended network, or nobody can say
  who gets paged if we trip an alarm.
- Remedy: confirm the window and the contact list. For red-team (stealth)
  work, the No-Go becomes a documented, explicitly approved exception.

## Gate 5: Exit readiness

Question: can we stop cleanly and prove what we did?

- Pass: rollback steps exist for every state-changing action, evidence
  collection is planned (commands logged, memory entries captured), and the
  report outline is ready.
- No-Go: actions with no undo path, or no plan to show the client what
  happened.
- Remedy: write the rollback steps and the evidence plan before starting.

## Gate log

Record each gate check as one line: date, gate, Go/No-Go, who decided,
and the evidence (scope doc id, risk scores, tool test output). A No-Go
that later becomes a Go gets a second line; the first line is never
edited, only superseded.
