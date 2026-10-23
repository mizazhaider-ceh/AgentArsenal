---
name: osint-methodology
description: Use when planning and running an open source intelligence
  collection effort against public sources only. Covers the OSINT cycle,
  defining collection requirements, building a collection plan, source
  evaluation, operational security for researchers, sock puppet hygiene,
  documentation and evidence handling, and reporting. Use when the
  engagement needs external reconnaissance, background research, or
  threat actor profiling, always within terms of service and privacy law.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [recon-passive]
tools:
  - name: theHarvester
    version: 4.x
  - name: Python
    version: 3.12
---

OSINT is the collection and analysis of publicly available information
to answer a specific intelligence question. This skill covers the
disciplined methodology: the intelligence cycle applied to open
sources, collection planning, source evaluation, researcher OPSEC, and
evidence handling. Scope is strictly public sources, used lawfully:
respect terms of service, privacy law, and the engagement's written
authorization. Never access non-public data, never bypass access
controls, never pretext as someone else to obtain private information.

## Quick Workflow

1. Write the intelligence requirement as a question, with a deadline
   and a named requester.
2. Break the question into sub-questions and map each to source types
   (domains, people, social, documents, code, infrastructure).
3. Set up a clean research environment and sock puppet accounts before
   touching any target.
4. Collect in passes: broad sweep first, then deep dives on the leads
   that matter.
5. Evaluate every source for reliability and every item for credibility
   before it enters the report.
6. Corroborate key facts with two independent sources.
7. Document everything with timestamps, URLs, and archived copies.
8. Report findings with confidence levels and explicit gaps.

## 1. The OSINT cycle

Direction, Collection, Processing, Analysis, Dissemination. In practice:

- Direction: the requester states the question. "Which domains does
  this company expose?" is answerable; "tell me everything" is not.
  Push back until the question is specific.
- Collection: gather raw data from public sources per the plan.
- Processing: deduplicate, normalize, and structure the data (spread-
  sheets, timelines, link charts).
- Analysis: answer the question, assign confidence, note what you
  could not find.
- Dissemination: deliver the report to the authorized requester only.

Revisit direction when collection shows the question was wrong. The
cycle is a loop, not a straight line.

## 2. Collection plan

Write the plan before you collect. Template:

```text
Requirement: Map the external attack surface of example.com for the
  authorized assessment starting 2026-11-01.
Sub-questions:
  1. Which domains and subdomains resolve publicly? (DNS, CT logs)
  2. Which IPs and ASNs host them? (BGP, reverse DNS)
  3. What technologies are exposed? (headers, certificates)
  4. Are there leaked credentials tied to the domain? (breach data)
Sources: crt.sh, DNS, RDAP, Shodan (authorized use), GitHub code search
Timebox: 3 days. Stop conditions: diminishing returns, or any source
  requiring authentication we do not have.
```

A timebox per sub-question stops OSINT from expanding forever. If a
lead would take a day to chase, check with the requester first.

## 3. Research environment and OPSEC

Keep research separate from your real identity:

```bash
# Dedicated research VM or browser profile, VPN exit in a neutral country
# Never log into personal accounts from the research profile

# Separate theHarvester runs per engagement with output directories
theHarvester -d example.com -b crtsh,certspotter -f /cases/acme/theharvester.html

# Archive every important page at collection time (pages change or vanish)
# Use the Wayback Machine save endpoint or a local archive tool, and note
# the archive URL next to the live URL in your notes
```

OPSEC rules:

- Use sock puppet accounts created for the engagement, with no links
  to your real identity (separate email, no phone reuse, no personal
  photos).
- Do not interact with the target: no friend requests, no follows, no
  messages, no comments. Passive observation only unless the
  authorization explicitly allows contact.
- Do not log into the target's services with the research identity in
  ways that create audit trails tied to the engagement unless approved.
- Keep case material encrypted at rest and delete it at the end of the
  retention period in the contract.

## 4. Source evaluation

Not all public data is good data. Score sources on:

- Authority: who publishes it (registry data beats a random blog).
- Freshness: when was it updated (DNS data goes stale fast).
- Corroboration: does a second independent source agree.
- Bias and motive: is the source selling something or pushing a view.

Credibility scale for the report: confirmed (two independent sources),
probable (one strong source), possible (one weak source), unknown.
Never present a single-source social media claim as confirmed.

## 5. Collection passes

Pass 1, broad sweep (hours): enumerate the obvious. Domains from
certificate transparency, company website, job ads (they leak tech
stacks), public code repos, app store listings.

```bash
# Certificate transparency sweep for subdomains
curl -s "https://crt.sh/?q=%25.example.com&output=json" \
  | python3 -c "
import json,sys
data=json.load(sys.stdin)
names=set()
for e in data:
    for n in e['name_value'].splitlines():
        names.add(n.strip().lower())
print('\n'.join(sorted(names)))" | head -50
```

Pass 2, deep dives (days): chase the leads. Historic DNS, document
metadata, employee tech mentions, infrastructure reuse across domains.

Pass 3, verification: re-check the key facts, archive the evidence,
and close gaps or mark them as gaps.

## 6. Evidence handling

Every finding needs a trail back to the source:

```bash
# Case directory layout
/cases/acme/
  plan.md            # collection plan and requirements
  log.md             # dated collection log: what, when, source URL
  evidence/          # archived pages, screenshots, raw JSON
  analysis.md        # working analysis and confidence notes
  report.md          # final deliverable
```

Log format per entry: timestamp (UTC), collector, source URL, archive
URL, what was collected, and why it matters. Screenshots get filenames
with date and subject. Hash raw downloads so you can prove they have
not changed.

## 7. Analysis techniques

- Timelining: put events in chronological order; gaps and clusters
  reveal campaigns and working hours.
- Link analysis: map people, domains, emails, and IPs as a graph;
  shared infrastructure links seemingly separate entities.
- Contradiction hunting: when two sources disagree, dig into which is
  newer or more authoritative instead of averaging them.
- Hypothesis testing: write the conclusion you expect, then actively
  look for disconfirming evidence before reporting.

## 8. Reporting

Structure: executive summary, requirement restatement, key findings
with confidence levels, detailed findings with evidence links, gaps
and limitations, recommendations, appendix of sources. Mark every
finding confirmed, probable, or possible. State what you did not find
as clearly as what you did. Deliver only to the authorized requester
over an approved channel.

## Edge cases

- The target has almost no public footprint. Report the thin result
  honestly instead of padding with speculation; suggest adjacent
  collection (suppliers, job ads) if authorized.
- Sources contradict each other. Present both with dates and let the
  requester decide, noting which you judge more reliable and why.
- A source requires login or payment. Check the authorization and
  terms of service first; some paid data sources are fine, scraping
  behind a login usually is not.
- You stumble on clearly private data (exposed credentials, personal
  documents). Stop, document minimally for the report, notify the
  requester through proper channels, and do not exploit or spread it.
- Language barriers: machine translate, but flag translated quotes as
  translations and verify key terms with a second tool.
- Sock puppet gets blocked or flagged. Do not create replacements to
  evade the block; note the limitation and move to other sources.

## Escalation

- The requirement cannot be answered from public sources: say so
  early, propose a narrowed question, and do not drift into gray-area
  collection to fill the gap.
- You find evidence of ongoing crime beyond the engagement scope:
  report to the requester and follow their legal guidance; do not
  investigate further on your own.
- A source threatens legal action over your collection: stop that
  collection immediately, preserve your authorization paperwork, and
  escalate to the requester's legal contact.
- The engagement needs active contact (interviews, pretexting):
  that is a different authorization and usually a different skill set.
  Get explicit written approval before any interaction.
- Timebox expires with gaps remaining: report the gaps with a cost
  estimate to close them and let the requester decide.

## Detection and defender view

OSINT methodology is neutral tradecraft; defenders use it and
defend against it:

- Attackers run the same cycle against your organization. Reduce
  their raw material: minimize DNS exposure, scrub document metadata,
  review what job ads and public code reveal.
- Defenders use OSINT for threat intel and incident scoping: find
  attacker infrastructure, track ransomware leak sites for your data,
  and verify breach claims before reacting.
- Watch for collection against you: certificate transparency
  monitoring alerts you when someone (or you) issues certs for your
  domains; canary tokens in public documents reveal who opens them.
- Attackers evade OSINT-based detection by rotating infrastructure
  fast and reusing bulletproof hosting. Track behavior (TTPs) not
  just IOCs.
- Tune your external footprint quarterly with the same passes in
  this skill, and fix what you would not want an attacker to find.

## Key references

- MITRE ATT&CK T1590 (Gather Victim Network Information), T1591
  (Gather Victim Org Information), T1593 (Search Open Websites and
  Domains), T1596 (Search Open Technical Databases).
- NATO OSINT Handbook concepts (intelligence cycle applied to open
  sources).
- theHarvester documentation: https://github.com/laramies/theHarvester
- crt.sh (certificate transparency): https://crt.sh/
- SANS SEC487 / SEC497 OSINT course concepts (course references).
