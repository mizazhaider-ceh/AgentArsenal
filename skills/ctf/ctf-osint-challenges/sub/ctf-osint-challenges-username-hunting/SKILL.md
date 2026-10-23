---
name: ctf-osint-challenges-username-hunting
description: Use when a CTF OSINT challenge provides a username, handle,
  or email fragment, or when tracing an online persona you are authorized
  to research. Covers enumerating username presence across platforms with
  Sherlock-style tooling, searching code and commits on GitHub, pivoting
  from one profile to linked accounts, handling username variants and
  leetspeak, verifying that profiles belong to the same person, and
  respecting challenge rules about contacting real people. Use when given
  a handle, when a metadata author field yields a name, or when you need
  to map every public account tied to one identity.
version: 1.0.0
domain: ctf
lifecycle: stable
last_verified: 2026-10-23
parent: ctf-osint-challenges
requires: [ctf-osint-challenges]
extends: []
relates: [osint-methodology, ctf-osint-challenges]
tools:
  - name: Python
    version: 3.12
  - name: curl
    version: 8.5
---

Usernames are the primary key of OSINT: people reuse handles across
platforms, and each platform leaks different facts (GitHub leaks code
and commit emails, social platforms leak photos and locations, forums
leak interests). This sub-skill covers the authorized competition
workflow for username enumeration and pivoting. Scope is CTF
competitions, lab personas, and research you are authorized to conduct;
never contact the person, attempt logins, or touch private data.

## Quick Workflow

1. Normalize the username: exact string, plus common variants
   (dots, underscores, numbers appended, leetspeak).
2. Run a multi-platform username check (Sherlock-style) to map
   presence across hundreds of sites.
3. Manually verify the top hits: same avatar, same bio phrases, same
   linked URLs mean the same person.
4. Search GitHub code and commits for the username; commit metadata
   is the richest pivot source.
5. Pivot: bios link to other handles, emails, domains; each becomes
   a new search seed.
6. Check archives for deleted or renamed profiles (Wayback Machine).
7. Corroborate identity with two independent signals before using a
   profile as a flag source.
8. Stop at public data; log every source for the writeup.

## 1. Multi-platform username enumeration

```bash
# Sherlock-style check (install per your environment)
sherlock target_handle --print-found --timeout 10
# or the faster maintained forks; output shape:
# [*] Checking username target_handle on:
# [+] GitHub: https://github.com/target_handle
# [+] Twitter: https://twitter.com/target_handle
# [-] Instagram: Not Found!

# Generate variants and check them too
for v in target_handle target.handle target_handle1 t4rget_handle; do
  echo "== $v"; sherlock "$v" --print-found 2>/dev/null | grep "+";
done
```

False positives happen (different people, same handle). Verification
(section 3) matters more than enumeration breadth.

## 2. GitHub as a pivot goldmine

```bash
# GitHub code search via web UI or API (authenticated token raises limits)
# search: "target_handle" in code, commits, issues

# Commit history leaks names and emails
curl -s -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/users/target_handle/events/public?per_page=100" | \
  python3 -c "import json,sys; [print(e['type'], e.get('repo',{}).get('name')) for e in json.load(sys.stdin)]" | sort | uniq -c | head

# Old commits often contain secrets removed later; check history, not just HEAD
# (use the web UI commit history or git log on a clone)
```

Look for: personal email in commits, linked personal domains in
READMEs, SSH keys (usernames), and gists (people paste freely in
gists). Each is a new pivot seed.

## 3. Verifying same-person identity

Confirm at least two of these before treating profiles as one person:

- Same avatar image (reverse image search the avatar).
- Same bio sentence or distinctive phrase across platforms.
- Cross-links: GitHub profile links the Twitter, Twitter links the
  blog, blog links the GitHub.
- Same PGP key, same email, same personal domain.
- Posting timestamps consistent with one timezone and one human.

Red flags: different avatars, contradictory locations, one profile
clearly older or corporate while others are personal. In CTFs the
planted persona usually has 3-5 obviously linked profiles; if linkage
is ambiguous, you may be looking at a real namesake, so stop.

## 4. Username variants and transformations

```python
#!/usr/bin/env python3
"""Generate plausible username variants for enumeration."""
base = "target_handle"
variants = {base}
variants.add(base.replace("_", "")); variants.add(base.replace("_", "."))
variants.add(base.replace("_", "-"))
for suffix in ("1", "123", "_", ".", "x", "official", "real"):
    variants.add(base + suffix)
leet = str.maketrans("aeios", "43105")
variants.add(base.translate(leet))
for v in sorted(variants):
    print(v)
```

Also try: first+last name combos when a real name surfaces
(`johnsmith`, `john.smith`, `jsmith`), and platform-specific forms
(Discord discriminators are gone, but old leaks still carry them).

## 5. Archives and deleted profiles

```bash
# Wayback availability for a profile URL
curl -s "http://archive.org/wayback/available?url=twitter.com/target_handle" | python3 -m json.tool

# CDX search for historical captures of a personal domain
curl -s "https://web.archive.org/cdx/search/cdx?url=targetblog.com/*&output=text&fl=timestamp,original&limit=50" | head -30
```

Deleted posts and old bios are where CTF authors plant flags: the
current profile looks clean, the 2021 archive has the clue. Check
profile renames too (GitHub redirects old usernames; the redirect
target confirms the rename chain).

## Edge cases

- The handle is extremely common: add discriminators from the
  challenge (location, event name, a distinctive phrase) to every
  search; enumerate, then filter hard.
- Platform blocks unauthenticated checks: use the platform's own
  search logged in as yourself, or accept the gap and pivot from
  verified profiles.
- The persona uses different handles per platform: pivot via
  cross-links and avatar matching rather than string matching.
- Sherlock-style tools miss niche CTF-planted sites: manually check
  any domain mentioned in the challenge, plus pastebin-likes and
  CTF-specific platforms.
- The username appears with a discriminator or ID number (old Discord
  tags, forum UIDs): search the handle with and without the number;
  archives often keep the numbered form.

## Escalation

- No profiles found anywhere: the handle may be encoded or partial
  (check the challenge text for the transform), or the challenge
  expects image or metadata OSINT instead.
- Profiles exist but are empty shells: they are verification
  anchors, not sources; the flag is in what they link to (a repo, a
  gist, an archived page).
- You found a real person with the same handle: stop, do not
  interact, and re-read the challenge; the intended persona is
  usually distinguished by one planted detail.
- A profile matches but its content is private: do not attempt follows
  or access tricks; treat it as unverifiable and find another source.

## Detection and defender view

Defenders use username hunting on themselves: enumerate employee and
brand handles, find exposed code and credentials in commits, and
reclaim lookalike accounts. Detection of hostile enumeration is
limited (it looks like normal browsing), so defense is hygiene: unique
handles per context, no personal emails in commits (use noreply
addresses), and regular audits of what each public profile reveals.
GitHub secret scanning and push protection catch the credential leaks
this workflow finds.

## Key references

- MITRE ATT&CK T1589 (Gather Victim Identity Information) and T1593
  (Search Open Websites/Domains).
- OSINT Framework (username sections): https://osintframework.com/
- Sherlock: https://github.com/sherlock-project/sherlock
- GitHub code search docs: https://docs.github.com/en/search-github
- Bellingcat username investigation guides:
  https://www.bellingcat.com/resources/
