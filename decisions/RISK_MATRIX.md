# Risk Matrix

Score every proposed action before you take it. Likelihood times impact,
each on a 1 to 5 scale. The score decides whether the action needs approval,
extra safeguards, or is refused outright.

## Scales

Likelihood (how probable is the bad outcome if we do this):

1. Rare: never seen in similar work, theoretical only.
2. Unlikely: seen once or twice in the field, needs unusual conditions.
3. Possible: happens regularly in similar work.
4. Likely: expected unless we take specific precautions.
5. Almost certain: will happen if we proceed.

Impact (how bad is the bad outcome):

1. Negligible: cosmetic, no data or availability effect.
2. Minor: brief degradation, recoverable in minutes, no data loss.
3. Moderate: noticeable downtime or partial data loss, recoverable in hours.
4. Major: extended outage or significant data loss, recovery takes days.
5. Catastrophic: unrecoverable data loss, safety consequences, legal
   exposure, or loss of client trust.

## Score bands

| Score (L x I) | Band | Meaning |
| --- | --- | --- |
| 1-4 | Low | Proceed. Standard care. |
| 5-9 | Medium | Proceed with the documented safeguard for this action. |
| 10-16 | High | Engagement lead approves first, safeguard mandatory, rollback plan ready. |
| 17-25 | Extreme | Refuse or redesign. No approval path except a written client exception. |

## Worked example

Proposed action: run `nmap -sS -p- --min-rate 5000` against the client's
production /24 during business hours.

- Likelihood of disruption: the client's IDS is known to be aggressive and
  the network team was not warned. Similar scans have triggered quarantine
  before. Likelihood = 4 (likely).
- Impact of disruption: a quarantined jump host would stall the whole team
  for a day, but no data loss. Impact = 3 (moderate).
- Score: 4 x 3 = 12, band High.

Decision: do not run as proposed. Options: get engagement lead approval with
a maintenance window (still High, needs the window as safeguard), or redesign:
slow the scan (`--max-rate 200`), scan after hours, warn the network team.
Redesigned: likelihood drops to 2 (unfamiliar scan profile, warned team),
impact stays 3. Score 6, Medium. Proceed with the safeguard documented in
the engagement log.

## Rules

- Score before acting, not after. The score and the chosen safeguard go in
  the engagement log next to the command.
- When in doubt between two likelihood values, take the higher one.
- A High score never proceeds on agent authority alone.
- Extreme scores are not negotiated down by optimism; they are redesigned
  or refused.
