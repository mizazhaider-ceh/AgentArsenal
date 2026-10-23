---
name: velociraptor-basics
description: Use when you need fast, targeted forensic collection across
  many endpoints during incident response or proactive hunting. Covers
  deploying the Velociraptor server, enrolling clients, running artifact
  collections from the GUI, writing basic VQL queries, launching hunts
  across the fleet, and using the offline collector for dead-box triage.
  Use when one compromised host becomes twenty, when you need the same
  evidence from every workstation, or when manual per-host forensics will
  not scale.
version: 1.0.0
domain: soc
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [incident-response, forensics-fundamentals]
tools:
  - name: Velociraptor
    version: 0.77
  - name: Python
    version: 3.12
---

Velociraptor is an endpoint visibility and collection framework: a server
that talks to lightweight agents on every endpoint, letting you query,
collect, and hunt across the whole fleet from one console instead of
touching hosts one by one. Its power comes from VQL (Velociraptor Query
Language) artifacts, prebuilt queries that collect specific evidence types.
This skill covers deploying a lab server, enrolling clients, running your
first collections, writing basic VQL, launching hunts, and the offline
collector for hosts you cannot enroll. Scope: deploy agents only on systems
you administer or are explicitly authorized to monitor, and tell users
beforehand where policy requires it. Endpoint collection sees everything on
a machine, so access control and a documented investigation basis are
mandatory.

## Quick Workflow

1. Deploy the Velociraptor server in your lab or SOC network and generate
   the server and client configs.
2. Enroll at least one test client and confirm it checks in on the GUI.
3. Run a built-in artifact collection on the test client (e.g., process
   listing, autoruns).
4. Write and test a small custom VQL query in a notebook.
5. Launch a hunt to run the collection across a client label or the fleet.
6. Download and review the collected results; extract IOCs.
7. For hosts you cannot enroll, build and run the offline collector.
8. Clean up: remove hunt data per retention policy and document the
   collection.

## 1. Server deployment

One binary is the whole server. Generate configs with the interactive
wizard, then run.

```bash
# Download the release binary for your platform and make it executable
wget -O velociraptor https://github.com/Velocidex/velociraptor/releases/download/v0.77.2/velociraptor-v0.77.2-linux-amd64
chmod +x velociraptor
./velociraptor version

# Interactive config generation (answers: datastore path, frontend hostname,
# ports, GUI credentials, self-signed certs for a lab)
./velociraptor config generate -i
# Produces server.config.yaml and client.config.yaml

# Run the server in the foreground first to watch for errors
./velociraptor --config server.config.yaml frontend -v

# GUI is on the configured port (default 8889); log in and confirm
# the dashboard loads with zero clients
```

For anything beyond a lab, put the server behind TLS with a real hostname,
back up `server.config.yaml` (it holds the CA), and restrict GUI access to
the SOC network. The client config embeds the server address and cert, so
regenerate clients if either changes.

## 2. Client enrollment

Install the agent with the client config on each endpoint. Enrollment is
automatic on first check-in.

```bash
# Linux client: copy binary + client.config.yaml, install as a service
sudo cp velociraptor /usr/local/bin/
sudo cp client.config.yaml /etc/velociraptor/client.config.yaml
# Create a systemd unit that runs:
# /usr/local/bin/velociraptor --config /etc/velociraptor/client.config.yaml client -v

# Windows client: install as a service (run as Administrator)
velociraptor.exe --config client.config.yaml service install
velociraptor.exe --config client.config.yaml service start

# Confirm enrollment in the GUI: the client appears under the search tab
# with its hostname, OS, and last-seen time
```

Label clients as they enroll (by OS, site, or role) because hunts target
labels. A hunt without labels is a hunt against everything, which is rarely
what you want.

## 3. First collections from the GUI

Collections run artifacts against one client. Start with the built-ins that
answer the most common triage questions.

```bash
# GUI path for each: select client -> Collect -> search artifact -> Launch
# Useful first artifacts:
#   Windows.System.Pslist          process listing
#   Windows.Sysinternals.Autoruns   persistence points
#   Windows.EventLogs.Evtx          event log collection
#   Windows.Registry.Hunter         registry triage
#   Linux.Sys.Pslist               Linux processes
#   Generic.Client.Info            client metadata sanity check
```

Each collection gets a flow ID; results land in the flow's Uploads and
notebook tabs. Download the CSV/JSON for anything you will correlate
elsewhere, and note the flow ID in your case notes so the collection is
reproducible and auditable.

## 4. Basic VQL

VQL looks like SQL but queries the endpoint: plugins return rows, and you
filter and shape them. Test in a notebook before putting a query in a hunt.

```sql
-- Processes with their command lines, newest first
SELECT Pid, Ppid, Name, CommandLine
FROM pslist()
ORDER BY Pid DESC
LIMIT 50
```

```sql
-- Files modified in the last 24 hours under temp directories
SELECT FullPath, Mtime, Size
FROM glob(globs=['C:/Windows/Temp/**', 'C:/Users/*/AppData/Local/Temp/**'])
WHERE Mtime > now() - 86400
ORDER BY Mtime DESC
```

```sql
-- Registry Run keys (persistence triage)
SELECT *
FROM registry_hunter(
  hive='HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run')
```

```bash
# Run VQL from the CLI too, for scripting and offline work
./velociraptor --config server.config.yaml query 'SELECT * FROM pslist() LIMIT 5'
```

VQL gotchas: paths need the right accessor for the OS, time is in epoch
seconds unless converted, and expensive queries (full-disk globs) should be
narrowed before hunting or they will take hours across a fleet.

## 5. Hunts across the fleet

A hunt runs an artifact against many clients at once, with conditions and
label targeting.

```bash
# GUI: Hunts -> New Hunt -> select artifact -> set label/condition -> Start
# Example hunt: collect autoruns from all Windows clients enrolled this week
# Condition (VQL): SELECT * FROM info() WHERE OS = 'windows'
```

Hunt hygiene: always set a label or condition, start with a small canary
group before the full fleet, and watch the server load on the first run.
Hunts write to the same flow/result structure as single collections, so your
review workflow does not change, only the scale does.

```sql
-- Hunt condition example: only clients that have not been collected today
SELECT * FROM info() WHERE OS = 'windows'
```

## 6. Offline collector for dead-box triage

When you cannot install an agent (a powered-off disk image, a host you must
not touch), build a standalone collector binary that gathers a fixed
artifact set to a local zip.

```bash
# Build the offline collector from the GUI (Server -> Build Offline Collector)
# or the CLI with a collector config, then run it on the target:
./velociraptor-collector --config collector.config.yaml collect -v
# Produces a zip with the collected artifacts; import it back into the
# server GUI for analysis with the same notebooks and VQL
```

The offline collector is also the right tool for third-party handoffs: the
recipient gets data, not access to your server.

## 7. Review, IOCs, and cleanup

```bash
# Results download from the GUI per flow/hunt; for automation use the API
# Extract IOCs from collected process and network data
# Example: unique external IPs from a netstat-style collection CSV
cut -d, -f5 connections.csv | sort -u | grep -E '^[0-9.]+$' | head -30

# Retention: delete hunt and flow data when the case closes, per policy
# GUI: select flow -> Delete; document what was deleted and when
```

Every collection is an intrusion into someone's machine from their
perspective. Keep the justification, the scope (which clients, which
artifacts), and the retention decision in the case file.

## Edge cases

- Client never checks in: verify the frontend port is reachable, the client
  config has the right server name/IP, and the client clock is roughly
  correct (TLS fails on wild skew).
- Collection returns empty: the artifact may not apply to that OS version,
  or the VQL had a wrong path/accessor. Test the artifact on a known-good
  lab client first.
- Hunt is too slow: narrow the artifact parameters, add stricter hunt
  conditions, or split by label into smaller hunts.
- GUI shows stale client data: check last-seen; an agent that stopped
  checking in mid-incident is itself a signal (host powered off, agent
  killed).
- Offline collector zip is huge: you collected too broadly; trim the
  artifact list to the triage set and re-run.

## Escalation

- Need custom evidence types: write a custom artifact (YAML with VQL) in
  the GUI artifact editor, test on one client, then promote it to hunts.
  Keep custom artifacts in version control.
- Fleet-wide YARA scanning: use the built-in YARA artifacts to push rules
  from yara-rules across endpoints, then hunt on the hits.
- Need continuous monitoring, not point collections: configure client event
  monitoring artifacts (process creation, DNS queries) which stream to the
  server, but size the server storage first.
- Server compromise suspected: the server holds keys to every endpoint;
  treat it as tier-zero infrastructure with backups, access logging, and
  an incident plan of its own.

## Detection and defender view

Velociraptor is a defender's force multiplier, and this entire skill is the
defender view: rapid evidence collection, fleet-wide hunting for IOCs, and
baselining normal endpoint behavior. Operationalize it: maintain a library
of hunt artifacts mapped to your top MITRE techniques, run them on a
schedule as proactive hunts, and feed hits to the SIEM. The misuse case is
deploying agents on machines without authorization, which is surveillance,
not defense; enrollment requires admin rights or explicit consent for a
reason, and bypassing that is out of scope. Also defend the server itself:
it is the highest-value target in the SOC after the domain controllers.

## Key references

- MITRE ATT&CK T1033 (System Owner/User Discovery), T1057 (Process
  Discovery), T1049 (System Network Connections Discovery): the discovery
  artifacts map here.
- MITRE ATT&CK T1003 (OS Credential Dumping): what LSASS collection
  artifacts target for detection.
- Velociraptor documentation: https://docs.velociraptor.app
- Velociraptor quickstart: https://docs.velociraptor.app/docs/deployment/quickstart/
- Velociraptor GitHub releases: https://github.com/Velocidex/velociraptor/releases
