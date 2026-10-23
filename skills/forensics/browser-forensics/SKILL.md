---
name: browser-forensics
description: Use when analyzing browser artifacts in an authorized
  investigation. Covers history, cookies, cache, downloads, and
  session artifacts for Chrome, Firefox, Edge, and Safari. Also use
  when web activity is the key timeline source.
version: 1.0.0
domain: forensics
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [forensics-fundamentals, dfir-timeline, log-forensics]
tools:
  - name: Python
    version: 3.12
  - name: sqlite3
    version: 3.46
---

Browsers record everything: history, searches, downloads, logins,
and cached content. This skill covers analyzing those artifacts from
disk images or profiles you are authorized to examine: where each
browser keeps what, how to parse it, and how to build the web
activity timeline.

## Quick Workflow

1. Identify the browsers and profiles on the image.
2. Copy the profile databases to your workstation (never work on
   the original).
3. Parse history, cookies, downloads, and logins per browser.
4. Reconstruct sessions: what the user did, in order.
5. Check the cache for content of deleted or private pages.
6. Correlate with the system timeline: browser events anchor user
   activity.
7. Note anti forensics: cleared history, private mode, and
   portable browsers.
8. Report with timestamps in UTC and the artifact per claim.

## 1. Chrome and Edge artifacts

```bash
# Profile locations (from the mounted image):
# Chrome: .../AppData/Local/Google/Chrome/User Data/Default/
# Edge:   .../AppData/Local/Microsoft/Edge/User Data/Default/
ls /mnt/img/Users/*/AppData/Local/Google/Chrome/User\ Data/ 2>/dev/null
```

```bash
# History: visits with timestamps (Chrome time = microseconds since 1601)
cp "/mnt/img/.../Default/History" /tmp/bf/history.db
sqlite3 /tmp/bf/history.db \
  "SELECT datetime(last_visit_time/1000000-11644473600,'unixepoch'), url, title
   FROM urls ORDER BY last_visit_time DESC LIMIT 20;"
```

```bash
# Downloads and cookies
sqlite3 /tmp/bf/history.db \
  "SELECT datetime(start_time/1000000-11644473600,'unixepoch'), target_path, tab_url
   FROM downloads ORDER BY start_time DESC LIMIT 10;"
cp "/mnt/img/.../Default/Cookies" /tmp/bf/cookies.db
sqlite3 /tmp/bf/cookies.db \
  "SELECT host_key, name, datetime(creation_utc/1000000-11644473600,'unixepoch')
   FROM cookies ORDER BY creation_utc DESC LIMIT 10;"
```

## 2. Firefox and cache

```bash
# Firefox: places.sqlite (history), cookies.sqlite, formhistory.sqlite
# Profile: .../AppData/Roaming/Mozilla/Firefox/Profiles/*.default*/
sqlite3 /tmp/bf/places.sqlite \
  "SELECT datetime(visit_date/1000000,'unixepoch'), url FROM moz_places
   ORDER BY last_visit_date DESC LIMIT 20;" 2>/dev/null || \
sqlite3 /tmp/bf/places.sqlite \
  "SELECT p.url FROM moz_places p JOIN moz_historyvisits h ON p.id=h.place_id
   ORDER BY h.visit_date DESC LIMIT 20;"
```

```bash
# Cache: may hold content of pages since deleted from history
# Chrome cache: parse with a cache viewer or strings triage
strings /mnt/img/.../Default/Cache/Cache_Data/data_1 2>/dev/null | grep -i -E "http" | head -10
```

## Edge cases

- History was cleared. Check the cache, cookies, and session
  files; clearing is rarely complete.
- Private mode was used. Memory forensics may help; disk
  artifacts will be thin.
- Multiple profiles or portable browsers. Enumerate all of them;
  the interesting one is often not Default.

## Escalation

- Encrypted profile (Firefox master password): note the barrier;
  do not brute force without authority.
- Need the full user timeline: merge browser events into the
  dfir-timeline.

## Detection and defender view

Browser forensics is investigative; its defensive cousin is
awareness that browsers are evidence rich: synced profiles spread
evidence to the cloud, and session restore files capture a lot.
For investigators, the durable practices are working on copies,
converting timestamps carefully, and corroborating browser claims
with network or system evidence.

## Key references

- Browser artifact documentation (forensic wiki references).
- NIST SP 800-86: forensic techniques.
- Related skills: dfir-timeline, forensics-fundamentals.
