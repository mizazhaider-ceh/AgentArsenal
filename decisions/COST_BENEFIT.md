# Cost Benefit Framework

Use this when deciding whether an engagement, a tool build, or a process
change is worth doing. It forces the costs and the benefits into the same
units so the comparison is honest.

## Step 1: Name the decision

One line. "Run a two-week external pentest of client acme." "Build an
automated report generator." If it does not fit one line, it is two
decisions.

## Step 2: List the costs (be pessimistic)

| Cost | Estimate | Notes |
| --- | --- | --- |
| Operator time | ___ hours x ___ rate | Include prep, execution, reporting, rework. |
| Tooling and infra | $___ | Licenses, cloud hosts, lab time. |
| Client disruption | ___ hours of their staff | Interviews, firewall changes, incident triage if we trip alarms. |
| Risk reserve | score from RISK_MATRIX.md | Convert High/Extreme bands into contingency time or insurance. |
| Opportunity cost | ___ | What we do not do while doing this. |

Rule: double the time estimate for any task you have not done twice before.

## Step 3: List the benefits (be skeptical)

| Benefit | Estimate | Notes |
| --- | --- | --- |
| Findings prevented | $___ | Expected loss avoided. Use the client's incident history, not industry averages, when you have it. |
| Compliance value | pass/fail | Some work is worth doing because a contract or regulation demands it. Say so plainly. |
| Capability gained | ___ | Skills, tools, or playbooks the team keeps afterward. Real, reusable, named. |
| Relationship value | ___ | Trust earned with this client. Do not put a dollar figure on it; describe it. |

Rule: a benefit you cannot name specifically is not a benefit, it is a hope.
Hopes go in the risks column as uncertainty.

## Step 4: Compare

- If total benefit clearly exceeds total cost: Go, and say which benefit
  carries the decision.
- If they are close: Go only if the top risk has a mitigation you trust, or
  shrink the scope until the math is clear.
- If cost exceeds benefit: No-Go, or redesign. "We already started" is not
  a benefit.

## Step 5: Record

One paragraph in the engagement or project log: the decision, the two or
three numbers that carried it, and the date. Revisit when a number changes
by more than half; a framework you never recheck is decoration.

## Worked mini-example

Decision: build an automated PDF report generator (one week of work).

- Costs: 40 hours x internal rate, plus 10 hours of rework reserve (never
  built one twice before, so time is doubled already). Total: 50 hours.
- Benefits: each manual report takes 6 hours; the team writes ~20 reports a
  year. 120 hours saved yearly, minus 10 hours yearly maintenance = 110
  hours. Capability gained: a reusable tool for every future engagement.
- Compare: 50 hours once vs 110 hours every year. Go. The carrying benefit
  is the yearly time saving; the capability gain is the tiebreaker if the
  numbers were close.
