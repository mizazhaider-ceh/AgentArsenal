---
name: people-osint
description: Use when researching a person from public sources for
  authorized security work (social engineering assessments with consent,
  executive protection, or investigations). Covers username and email
  enumeration, social media mapping, and breach data correlation. Use
  when the engagement includes OSINT on named individuals, when building
  a target profile with permission, or when assessing personal exposure.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
parent: osint-methodology
requires: [osint-methodology]
extends: []
relates: [breach-data-osint, social-media-osint]
tools:
  - name: theHarvester
    version: 4.6
  - name: Python
    version: 3.12
---

People OSINT builds a picture of a person from public sources: accounts,
usernames, emails, and exposures. This skill covers the techniques for
authorized work only: consented assessments, executive protection, and
legitimate investigations. It stays on public data, respects platform
rules, and never touches non-public sources. If the authorization does
not name the person, stop.

## Quick Workflow

1. Confirm the authorization names the individual and the purpose.
2. Start from the known identifiers: name, email, username, company.
3. Enumerate usernames and accounts across platforms.
4. Map social media presence and public posts.
5. Correlate breach data for exposure (see breach-data-osint).
6. Build the profile: accounts, exposure, and attack surface.
7. Report factually; do not speculate about private matters.

## 1. Username and email enumeration

```bash
# Username variants from the name: jdoe, john.doe, johndoe92, etc.
python3 - <<'EOF'
first, last = "john", "doe"
variants = {first+last, first+"."+last, first[0]+last, first+last[0],
            first+"_"+last, first+last+"92", last+first}
print("\n".join(sorted(variants)))
EOF

# Check username presence across platforms (use your enumeration tooling)
# Record: platform, profile URL, activity level, public info

# Email enumeration via theHarvester (public sources only)
theHarvester -d example.com -b all -l 200 2>/dev/null | head -30
```

Usernames repeat across platforms: one known username unlocks the
pattern for the rest. Record every account with its URL and what is
publicly visible; the profile is built from public facts, not guesses.

## 2. Social media mapping

```bash
# Per account found, record systematically:
# - Profile URL and handle
# - Bio, location, links (often leak other accounts)
# - Employment history and education
# - Public posts revealing: travel plans, tech stack, internal tools,
#   org charts, badge photos, screen photos with data

# Search the person's posts for security-relevant disclosures:
# - "new laptop" photos (stickers reveal employer, sometimes screens)
# - Conference badges (name, company, sometimes QR data)
# - "Working from X" (travel patterns for pretexting)
```

Photos are the richest source: backgrounds show offices, whiteboards,
screens, and badges. But the analysis stays factual: report what is
visible, not what you infer about their life.

## 3. Exposure assessment

```bash
# Correlate the enumerated emails/usernames with breach data
# (see breach-data-osint for the handling discipline)
# Exposure questions:
# - Are their credentials in public breaches? (password reuse risk)
# - Is their personal data aggregated on people-search sites?
# - Do their public posts enable targeted phishing? (role, tools, contacts)

# Executive protection output: the exposure list with removal options
# (opt-outs for people-search sites, privacy setting fixes)
```

The deliverable depends on the purpose: for a consented assessment, it
is the attack surface (what a phisher would use); for executive
protection, it is the exposure list with remediation. Both stay factual
and sourced.

## Edge cases

- The person has a common name. Disambiguate with the company, location,
  or known username before attributing anything; misattribution is the
  cardinal sin of people OSINT.
- Accounts are private. Public metadata (bio, follower counts) is still
  usable; do not attempt to bypass privacy controls.
- The authorization is verbal. Get it in writing with the named
  individual before starting; people OSINT without clear authorization
  is indistinguishable from stalking.
- You find sensitive personal data. Minimize it: the security report
  needs the attack surface, not the person's private life.

## Escalation

- The scope expands to associates: each new person needs their own
  authorization; networks of people do not inherit consent.
- You need non-public data: that is outside OSINT by definition;
  raise it as a scope question, do not improvise access.
- The findings indicate real danger to the person: report through the
  agreed channel immediately, with the facts only.

## Detection and defender view

For defenders, people OSINT is the red team's reconnaissance made
visible: the same public data the phisher uses. The defensive program
is executive digital hygiene: regular exposure reviews, people-search
opt-outs, social media guidance for high-risk roles, and breach
monitoring for key staff. You cannot stop public data collection, but
you can shrink what is public.

## Key references

- OSINT framework references (technique catalogs).
- Platform terms of service (collection boundaries).
- NIST SP 800-63 (identity proofing context, for assessments).
