---
name: cost-of-attack
kind: brain
description: Use when an agent must think in attacker economics: prioritizing which vulnerabilities to fix first, deciding where a limited security budget goes, evaluating whether a control is worth its price, or predicting what an adversary will try next. Provides attacker-cost reasoning: every attack step has a price in time, skill, money, and detection risk; attackers maximize return on effort; defense wins by raising the cost of the cheapest paths above the value of the target. Load this brain when prioritization must be economic, not just technical.
version: 1.0.0
provides:
  - Attacker cost modeling per step (time, skill, money, risk)
  - Attacker ROI and target value assessment
  - Cheapest-path-first fix prioritization
  - Cost-raising control selection
  - Defense budget allocation by leverage
  - Diminishing returns recognition
used_by: []
---

Security advice usually speaks in severity: critical, high, medium. Attackers speak in price: how much does this cost me, and what do I get? A "critical" vulnerability that needs a nation-state lab to exploit is cheaper to ignore than a "medium" misconfiguration that a script kiddie can abuse in ten minutes. The cost-of-attack brain translates technical findings into economic ones. It matters because every team has finite budget and infinite findings. Economics is the only honest way to rank them.

## Core mental models

**Every attack step has a price.** Price has four currencies: time (hours to develop and run), skill (script kiddie to specialist), money (tools, infrastructure, bribes), and detection risk (chance of getting caught, which attackers price very highly). When you evaluate a vulnerability, estimate all four. A default password costs almost nothing in every currency. A kernel zero-day costs months, specialists, and burns a valuable asset. Price the step, and you can predict whether anyone will take it.

**Attackers maximize return on effort.** Like any economic actor, attackers pick targets and paths with the best payoff per unit of cost. This is why phishing and credential stuffing dominate: trivial cost, massive scale, good enough returns. Your threat model should weight attacker-favorite paths (cheap, scalable, low risk) far above exotic ones. Defend against the profitable attacks first, because those are the ones that actually arrive.

**Raise the cost of the cheapest path.** The defender's economic move is not to make attacks impossible but to make the cheapest paths expensive. MFA turns credential theft from free into hard. Patching the internet-facing VPN turns an automated scan into a custom operation. Each control should be judged by one question: how much does this raise the attacker's cheapest path cost? The best controls raise cost across many paths at once.

**Know when to stop spending.** Defense has diminishing returns. Spending a million dollars to raise the cost of attacking a hundred-thousand-dollar asset is bad economics, unless the asset's real value (trust, safety, legal exposure) is higher than it looks. Price the asset honestly, including indirect value, then spend proportionally. Security that costs more than the loss it prevents is a different kind of failure.

## Operating checklist

1. List the attack paths to your key assets (borrow the attack graph from attacker-mindset).
2. Price each path in the four currencies: time, skill, money, detection risk.
3. Estimate the attacker's payoff: what is each asset worth to whom?
4. Rank paths by attacker ROI (payoff divided by cost). The top of this list is your real risk.
5. For each top path, list candidate controls and estimate how much each raises the path cost.
6. Pick controls with the best cost-raised per dollar spent. Prefer ones that raise many paths at once.
7. Price the asset honestly before spending: direct value plus trust, legal, and safety exposure.
8. Stop when the next dollar of defense buys less risk reduction than it costs.
9. Re-price quarterly: attacker tooling gets cheaper over time (yesterday's zero-day is today's script).
10. Document the economics: why this fix before that one, in cost terms, so the reasoning survives review.

## Heuristics

- Fix the ten-dollar attack before the ten-thousand-dollar one, regardless of severity labels.
- If a control does not raise attacker cost, it is decoration. Remove it or replace it.
- Attacker tooling only gets cheaper. Today's expensive attack is tomorrow's automated scan.
- Detection risk is the currency attackers fear most. Raise it visibly.
- Scale matters: a cheap attack that scales to a thousand targets will be used. Price accordingly.
- The cheapest path is usually credentials, phishing, or unpatched edge. Start there, every time.
- A control that raises cost on one path but opens another is a bad trade. Check the graph.
- Spend proportional to asset value, not to fear.

## Anti-patterns

- **Severity worship.** Fixing CVEs in scanner order while the helpdesk has no MFA and the VPN is unpatched.
- **Gold-plating.** Buying the expensive tool to stop the exotic attack while the cheap paths stay open.
- **Ignoring the payoff.** Spending heavily to protect an asset nobody would bother stealing.
- **One-time pricing.** Assuming attacker costs stay fixed while exploit kits commoditize last year's hard attacks.
- **Cost-blind controls.** Deploying controls without ever asking what attacker path got more expensive.

## Worked example

A team has two findings: a critical RCE in an internal admin tool (needs VPN access plus a valid session, no public exploit) and a medium finding (password reset tokens that never expire, sent over email). Scanner order says fix the RCE first. Cost-of-attack says otherwise. RCE price: high skill, needs prior access, no public exploit, high detection risk once used. Reset token price: nearly zero, anyone with inbox access (phishing, old breaches) can reuse a token months later, low detection risk. Attacker ROI on the token flaw is far higher, and it is the path a real attacker takes. The team fixes token expiry and single-use first (one day of work, kills a whole attack class), then schedules the RCE. Economics beat the scanner, and the actual cheapest path is closed first.
