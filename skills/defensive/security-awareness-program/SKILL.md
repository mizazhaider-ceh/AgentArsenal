---
name: security-awareness-program
description: Use when building or improving a security awareness
  program. Covers phishing simulations, role based training, metrics
  that matter, and building a reporting culture. Also use when
  phishing keeps working and training needs to actually change
  behavior.
version: 1.0.0
domain: defensive
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [phishing-defense, incident-response]
tools:
  - name: Python
    version: 3.12
---

Awareness programs fail when they are annual slide decks; they work
when they are frequent, relevant, and measured. This skill covers
building one that changes behavior: simulations people learn from,
training for real roles, and metrics beyond click rates. It is for
organizations improving their human layer.

## Quick Workflow

1. Baseline: run a phishing simulation and measure reporting, not
   just clicks.
2. Segment by role: finance gets invoice fraud, devs get supply
   chain, execs get whaling.
3. Train in small frequent doses, not annual marathons.
4. Make reporting easy: one button, no blame, fast feedback.
5. Measure behavior change: report rate up, click rate down, time
   to report down.
6. Follow up with clickers: coaching, not punishment.
7. Cover the rest: passwords, MFA, physical, and AI era scams.
8. Report to leadership in risk terms, not training completion.

## 1. Simulation and metrics

```bash
# Simulation program basics:
# - monthly cadence, varied lures (not just "package delivery")
# - difficulty ramps: easy lures first, spear phish later
# - never use real HR disciplinary threats as lures (destroys trust)
# - always include a teaching moment on landing, win or lose
echo "metrics: report rate (target up), click rate (target down),"
echo "repeat clickers (coach), time to first report (target down)"
```

```python
#!/usr/bin/env python3
"""Awareness metrics sketch."""
months = [
    ("Jan", 22, 8), ("Feb", 19, 12), ("Mar", 15, 18),
    ("Apr", 12, 25), ("May", 10, 31), ("Jun", 9, 38),
]
print(f"{'month':>5} {'click%':>6} {'report%':>7}")
for m, click, report in months:
    print(f"{m:>5} {click:>6} {report:>7}")
print("the report rate is the metric that predicts real incidents")
```

## 2. Reporting culture

```bash
# Make reporting the hero action:
# - one click report button in the mail client
# - SLA: security acknowledges within the hour
# - feedback: "thanks, that was a real phish, you stopped it"
# - no blame for clicks; blame for not reporting
echo "a reported phish is a win even if clicked; an unreported one is the loss"
```

## Edge cases

- Click rates plateau. Change the lures and the training; the
  audience adapted, which is good, now raise the bar.
- Executives skip training. Get leadership buy in first; the
  program fails without it.
- Union or works council concerns. Involve them early; simulations
  are safer with agreement.

## Escalation

- Real phish reported: the SOC workflow takes over; the program's
  job was getting the report fast.
- Systemic failures (whole department clicks): targeted coaching
  and process fixes, not more slides.

## Detection and defender view

Awareness is a detection layer: trained users are sensors who
report. Attackers adapt with better lures (AI generated, deepfake
voices), so the program must too. The durable measure is the
reporting pipeline's health: volume, speed, and accuracy of user
reports feeding the SOC.

## Key references

- NIST SP 800-50: security awareness program building.
- Related skills: phishing-defense, incident-response.
