---
name: defender-mindset
kind: brain
description: Use when an agent needs to reason like a defender: designing security controls, reviewing an architecture for defensive gaps, prioritizing fixes under a limited budget, writing detection logic, or deciding what to protect first. Provides defender mental models: the defender must cover everything while the attacker needs one gap, prevention is finite but detection is forever, layers are friction not walls, and every control should be designed assuming the previous one failed. Load this brain when the task is to protect, prioritize, or harden rather than to break.
version: 1.0.0
provides:
  - Defender asymmetry framing (cover all vs find one)
  - Defense in depth as layers of friction
  - Prevention, detection, and response balance
  - Control failure assumption and second lines
  - Fix-the-class prioritization
  - Asset-value driven protection order
used_by: []
---

The defender's job is unfair. The attacker needs one working path; the defender must close all of them, forever, with a budget and a team that also has a day job. The defender-mindset brain teaches an agent to make peace with that asymmetry and still win: you cannot be perfect, so you make attack paths expensive, visible, and survivable. It matters because most defensive advice is written as if perfection were possible. It is not. Good defense is about raising cost and shrinking impact, in that order.

## Core mental models

**The asymmetry is real, plan around it.** You will never find and fix every vulnerability. Accept it. The defender's leverage is not completeness, it is economics: make the cheapest attacker paths expensive first, because attackers take the cheapest path. A defender who patches the ten most attacker-cheap issues beats a defender who perfectly hardens one crown jewel and ignores the loading dock. Prioritize by attacker cost, not by scanner severity alone.

**Prevention is finite, detection is forever.** Every preventive control can fail or be bypassed. Assume it will. Detection is the control that keeps working after prevention fails: logs, alerts, anomaly checks. A mature defense spends as much thought on "how will we know" as on "how will we stop." If a control fails silently, it is barely a control at all. Design every prevention with a paired detection.

**Layers are friction, not walls.** Defense in depth does not mean stacking walls the attacker must break. It means stacking friction that costs the attacker time, noise, and risk at every step. Each layer should do two jobs: slow the attacker down and make them louder. A WAF, then auth, then input validation, then least-privilege DB access, then query logging: none is a wall, together they are five chances to catch the same attacker.

**Design for the control failing.** For every control you add, ask what happens when it fails. If the firewall rule is wrong, is there network segmentation behind it? If the password leaks, is there MFA? If MFA is phished, is there anomaly detection on logins? The second line is not paranoia, it is the actual design. A defense with no plan for control failure is a single point of failure with extra steps.

## Operating checklist

1. List what you must protect, ranked by real business value (data, uptime, trust).
2. List the cheapest attacker paths to each, using attacker-mindset reasoning.
3. For each path, place at least one preventive and one detective control.
4. Ask for each control: what happens when this one fails? Add the second line.
5. Check the boring basics first: patching, MFA, backups, logging. Most breaches skip the fancy stuff.
6. Reduce what needs defending: remove unused services, accounts, and access. Smaller surface, cheaper defense.
7. Verify controls actually work (test the backup restore, trigger the alert on purpose).
8. Write the runbook: who does what in the first 30 minutes of a breach.
9. Review on a rhythm, not after an incident. Defenses rot.
10. Measure two numbers: mean time to detect and mean time to respond. Improve them.

## Heuristics

- Patch the class, not the bug: one SQL injection found means audit every query.
- The basics beat the exotic: MFA stops more breaches than any AI product.
- If nobody tested the backup, you do not have a backup.
- A control without an alert is a suggestion.
- Remove before you harden: a deleted service needs no patching.
- Defend the paths attackers actually use (phishing, stolen creds, unpatched edge), not the ones in movies.
- Spend defense budget where attacker cost rises most per dollar.
- Your runbook is only as good as its last drill.

## Anti-patterns

- **Security theater.** Controls that look strong but change no attacker path cost (a complex password policy with no MFA, a firewall nobody audits).
- **Perfect-wall thinking.** Believing one strong control (the firewall, the EDR) means the inside can be trusted.
- **Alert noise without tuning.** Hundreds of alerts nobody reads. Detection that nobody watches is not detection.
- **Fixing the scanner, not the risk.** Chasing a clean vulnerability report while the helpdesk has no MFA.
- **No failure plan.** Controls designed as if they never fail, so the first bypass is total.

## Worked example

A small company asks how to stop ransomware with a tiny budget. The agent ranks assets: customer database first, then email, then file shares. Cheapest attacker paths: phishing an employee, then unpatched VPN. Controls per path, cheap first: MFA on email and VPN (kills credential replay), offline tested backups of the database (kills the ransom leverage), patch the VPN (closes the easy hole). Paired detections: impossible-travel login alerts, backup integrity checks that page someone. Second lines: if MFA is phished, login anomaly alerts catch it; if the VPN is breached, internal segmentation limits the blast. The agent skips the expensive EDR suite the vendor pitched. Total spend is small, but every cheap attacker path now costs the attacker real effort and makes real noise. That is defender thinking: asymmetry accepted, economics applied.
