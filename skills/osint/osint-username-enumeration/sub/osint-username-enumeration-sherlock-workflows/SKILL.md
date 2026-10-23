---
name: osint-username-enumeration-sherlock-workflows
description: Use when you need to run Sherlock effectively as part of a
  username investigation on authorized cases. Covers installing and
  updating Sherlock with Python 3.12, tuning timeouts and concurrency,
  using proxies and Tor for sensitive cases, building custom site lists,
  parsing JSON output for triage, handling false positives at scale,
  and scheduling repeat scans. Use when the parent
  osint-username-enumeration workflow reaches automated checking, when a
  standard Sherlock run returns too much noise, or when you need
  reproducible, documented scan configurations.
version: 1.0.0
domain: osint
lifecycle: stable
last_verified: 2026-10-23
parent: osint-username-enumeration
requires: [osint-username-enumeration]
extends: []
relates: [osint-username-enumeration]
tools:
  - name: Python
    version: 3.12
  - name: Sherlock
    version: 0.14.0
  - name: curl
    version: 8.5
---

Sherlock checks a username against hundreds of sites and reports
where it exists. It is fast, but raw output is noisy and its site
list decays as platforms change. This sub-skill is the operator's
manual: installation, tuning, proxy use, custom site lists, and output
parsing that turns a scan into triage-ready data. Public profiles
only, within an authorized investigation.

## Quick Workflow

1. Install or update Sherlock and note the version for the case file.
2. Prepare the handle list: primary plus variants from the parent
   skill.
3. Run with JSON output, a sane timeout, and a case-named output
   file.
4. Parse the JSON into a triage table: claimed, unclaimed, errors.
5. Manually verify claimed hits, starting with high-value platforms.
6. Re-run failures and errors separately with longer timeouts.
7. Save the command line, version, date, and raw output with the case.
8. Schedule a re-scan only if the case justifies it.

## 1. Installation and updating

```bash
# From source keeps the site list current
git clone https://github.com/sherlock-project/sherlock.git
cd sherlock
pip install -r requirements.txt
python3 sherlock --version

# Or the packaged install
pip install sherlock-project
sherlock --version
```

The site list lives in a JSON data file in the repo. Before a case,
pull the latest and diff it so you know what changed:

```bash
cd sherlock && git pull
git log --oneline -3 -- sherlock_project/resources/data.json
```

Note the commit hash in the case file. A site added last week can
explain a hit that an older scan missed, and reproducibility matters
if results go to a report.

## 2. Tuned scan commands

```bash
# Standard case scan: JSON output, 20s timeout, named output
sherlock darkcoder \
  --json --output ./cases/2026-10-darkcoder/sherlock.json \
  --timeout 20 \
  --print-found

# Multiple handles in one invocation
sherlock darkcoder darkcoder123 d4rkcoder \
  --json --output ./cases/2026-10-darkcoder/sherlock-variants.json

# Sensitive case: route through Tor to avoid leaking the investigation
# (Tor must be running locally first)
sherlock darkcoder --proxy socks5://127.0.0.1:9050 --timeout 40

# Limit to specific sites for a focused re-check
sherlock darkcoder --site GitHub --site Reddit --site Twitter
```

Example JSON output shape (one entry):

```json
{
  "GitHub": {
    "url_main": "https://github.com/",
    "url_user": "https://github.com/darkcoder",
    "status": {"claimed": "Claimed"},
    "http_status": 200,
    "response_time_s": 0.84
  }
}
```

Parse it into a triage list:

```bash
python3 - <<'EOF'
import json
with open('sherlock.json') as f:
    data = json.load(f)
claimed, failed = [], []
for site, info in data.items():
    s = info.get('status', {}).get('claimed')
    if s == 'Claimed':
        claimed.append((site, info['url_user']))
    elif 'http_status' not in info:
        failed.append(site)
print(f"CLAIMED ({len(claimed)}):")
for site, url in sorted(claimed):
    print(f"  [ ] {site}: {url}")
print(f"\nERRORS/NO-RESPONSE ({len(failed)}): {', '.join(sorted(failed)[:10])}")
EOF
```

The checkbox format turns directly into the verification checklist
for the parent skill's manual review step.

## 3. Custom site lists

When the case involves niche platforms (a gaming forum, a regional
site), add them:

```json
// custom-sites.json: Sherlock site entry format
{
  "ExampleForum": {
    "url": "https://forum.example.com/user/{}",
    "urlMain": "https://forum.example.com/",
    "username_claimed": "darkcoder",
    "username_unclaimed": "noonewouldeverusethis12345"
  }
}
```

Sherlock determines "claimed" by comparing the response against the
known-claimed and known-unclaimed probes, so include both. Test the
custom entry against a known existing and a known missing account
before trusting it in a case.

## 4. Handling errors and retries

Network errors are not negatives. Separate them:

```bash
# Re-run only the sites that errored, with a longer timeout
# (extract the failed site names from the triage script, then:)
sherlock darkcoder --site GitHub --site Reddit --timeout 60
```

Common error causes: the site rate-limited the scan (slow down, add
delays), the site changed its URL scheme (check the data file or the
site manually), or the exit node is blocked (rotate Tor circuits with
a new identity). Never interpret a timeout as "account does not
exist" in the case file; mark it unknown and verify manually.

## 5. Repeat scans and change detection

```bash
# Monthly re-scan for long-running cases, diffed against the baseline
sherlock darkcoder --json --output ./cases/2026-10-darkcoder/sherlock-nov.json
python3 - <<'EOF'
import json
old = json.load(open('sherlock.json'))
new = json.load(open('sherlock-nov.json'))
def claimed(d):
    return {s for s, i in d.items() if i.get('status', {}).get('claimed') == 'Claimed'}
added = claimed(new) - claimed(old)
removed = claimed(old) - claimed(new)
print("New accounts since baseline:", sorted(added) or "none")
print("Removed accounts since baseline:", sorted(removed) or "none")
EOF
```

New accounts mid-investigation can indicate the subject is active;
removed accounts may indicate cleanup. Both are worth a case note.

## Edge cases

- A site returns "claimed" for every username (broken detection).
  Test with the unclaimed probe; if it also claims, exclude the site
  and report the data file issue upstream.
- The handle contains characters Sherlock rejects. Check the
  regex in the data file; some sites allow dots or unicode that the
  generic check mishandles, so verify those manually.
- Corporate network blocks or throttles the scan. Run from the
  approved research network or VM per your organization's policy,
  not by circumventing controls.
- The scan itself notifies the subject (some platforms log profile
  views or the scan triggers alerts). For sensitive cases, prefer
  the Tor path and discuss operational security with the case owner
  before scanning.
- Sherlock's site count differs between installs. The pip package
  lags the git repo; for cases, always use git HEAD and record the
  commit.
- JSON output is malformed after an interrupted run. Re-run rather
  than hand-editing; partial JSON silently drops sites.

## Escalation

- Scan results will support legal or disciplinary action. Freeze the
  exact command, version, commit hash, and raw output; do not
  re-scan casually afterward, since results may change.
- You discover the handle is tied to criminal infrastructure in a
  threat intel case. Preserve the output immediately and escalate to
  the case owner before any further active checking.
- A custom site you added is actually behind authentication or
  returns private data. Remove it from the case workflow; Sherlock
  is for public profile existence checks only.
- The volume of hits suggests an organized identity (dozens of
  consistent accounts). Escalate the correlation phase: this is now
  a full footprint mapping, not a quick check.

## Detection and defender view

Sherlock scans are visible to sites as rapid sequential profile
requests from one IP, which is why operational security (Tor,
rate limits, approved research infrastructure) matters for
sensitive cases. Defensively, the lesson is handle hygiene from the
parent skill: unique handles per context, no bio cross-links, and
periodic self-scans with this exact workflow to see what an
investigator would find. If your organization runs these checks on
personnel or vendors, document the authorization clearly; the tool
is neutral, the context is everything.

## Key references

- Sherlock project and site data file:
  https://github.com/sherlock-project/sherlock
- Maigret (deeper checks, sibling workflow):
  https://github.com/soxoj/maigret
- Parent skill methodology: osint-username-enumeration (this repo)
- Bellingcat verification guidance:
  https://www.bellingcat.com/resources/
- Tor Project (for sensitive-case routing):
  https://www.torproject.org/
