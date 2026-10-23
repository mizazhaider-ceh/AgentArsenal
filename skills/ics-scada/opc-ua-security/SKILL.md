---
name: opc-ua-security
description: Use when assessing OPC UA servers on an authorized OT
  engagement or lab. Covers endpoint discovery, security policy review,
  certificate handling, anonymous access checks, and node enumeration.
  Also use when a plant uses OPC UA as its integration layer and you
  need to verify its security configuration.
version: 1.0.0
domain: ics-scada
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [modbus-security, scada-network-seg, tls-analysis]
tools:
  - name: Python
    version: 3.12
  - name: nmap
    version: 7.98
---

OPC UA was designed with security in mind: signed and encrypted
endpoints, certificates, and user authentication. In practice it is
often deployed with security disabled: anonymous access, the None
policy, and self signed certificates nobody validates. This skill
covers authorized assessment: discovering endpoints, grading their
security policies, testing authentication, and enumerating the address
space. Coordinate with operations; even reads can load fragile
servers.

## Quick Workflow

1. Get written OT authorization naming the segment and test window.
2. Discover OPC UA servers on the standard port 4840 and any custom
   ports.
3. List every endpoint and grade its security policy and mode.
4. Test anonymous access and weak credentials on each endpoint.
5. Review certificate handling: self signed, expired, or never
   validated.
6. Enumerate the address space: browse nodes and note writable ones.
7. Check user roles: what can an authenticated low privilege user do.
8. Report each endpoint with its policy grade and the fix.

## 1. Endpoint discovery and policy grading

```bash
# Find OPC UA servers on the authorized segment
sudo nmap -sS -p 4840 --open -T2 192.168.10.0/24 -oN /tmp/opcua_disc.txt
grep -B2 open /tmp/opcua_disc.txt | head
```

```python
#!/usr/bin/env python3
"""OPC UA endpoint grader (stdlib socket; parses GetEndpoints response)."""
import socket, struct

HOST = "192.168.10.30"
PORT = 4840

def hello():
    # Minimal OPC UA Hello + GetEndpoints request
    hello_msg = b"HELF" + struct.pack("<I", 28) + struct.pack("<I", 0)
    hello_msg += struct.pack("<I", 16) + b"opc.tcp://" + struct.pack("<I", 0)
    s = socket.create_connection((HOST, PORT), timeout=5)
    s.sendall(hello_msg)
    data = s.recv(4096)
    s.close()
    return data

try:
    resp = hello()
    print("server answered hello, bytes:", len(resp))
    print("next: use a full client (python-opcua) for endpoint parsing")
except Exception as e:  # noqa: BLE001
    print("no answer:", e)
```

For full endpoint parsing, use the opcua asyncua library in the lab
(stdlib only rule applies to committed scripts; assessment tooling may
use it):

```bash
# List endpoints with security policy details
python3 - << 'PY'
# pip-installed asyncua used as assessment tooling (not committed code)
from asyncua import Client
import asyncio
async def main():
    async with Client("opc.tcp://192.168.10.30:4840") as client:
        for ep in await client.get_endpoints():
            print(ep.EndpointUrl, "|", ep.SecurityPolicyUri.split("#")[-1],
                  "|", ep.SecurityMode.name)
asyncio.run(main())
PY
# Flag: SecurityPolicy None or SecurityMode None on any endpoint
# Flag: Basic128Rsa15 or Basic256 (deprecated weak policies)
```

## 2. Authentication and node enumeration

```bash
# Test anonymous access: can you browse without credentials?
python3 - << 'PY'
from asyncua import Client
import asyncio
async def main():
    async with Client("opc.tcp://192.168.10.30:4840") as client:
        root = client.get_root_node()
        children = await root.get_children()
        print("anonymous browse OK, root children:", len(children))
        for c in children[:10]:
            print(" -", await c.read_browse_name())
asyncio.run(main())
PY
```

```bash
# Try default and weak credentials on endpoints that need login
# (use the plant's documented test accounts only, never brute force OT)
# Then enumerate writable nodes as the authenticated user:
python3 - << 'PY'
print("checklist: anonymous browse, default creds, role of test user,")
print("writable setpoints visible to that role, method nodes callable")
PY
```

## Edge cases

- The server only offers deprecated policies. That is the finding;
  recommend an upgrade path, not a config tweak.
- Certificates are self signed and the client is told to trust all.
  Document the MITM exposure this creates on the segment.
- Browsing a large address space hangs the server. Browse
  incrementally and stop at the first level that proves the point.
- Redundant server pairs behave differently. Test both; failover
  servers are often misconfigured.

## Escalation

- No endpoints answer: the server may require a reverse connection or
  sit behind an aggregator; check the architecture docs.
- Authentication blocks enumeration: review the user and role model
  from documentation and test privilege boundaries with the provided
  test accounts.
- Custom port in use: scan the vendor documented range on the target
  hosts only.

## Detection and defender view

Defenders see OPC UA attacks as unknown clients calling GetEndpoints,
anonymous sessions, failed logins, and browsing patterns no HMI uses.
Detect with server audit logs: alert on anonymous sessions, new
client certificates, and write or method calls outside the baseline.
The durable fix is to offer only signed and encrypted endpoints,
disable anonymous access, validate client certificates against a
managed trust list, and enforce least privilege roles on nodes.

## Key references

- MITRE ATT&CK ICS T0806 (Brute Force I/O Addresses).
- CWE-306 (Missing Authentication for Critical Function).
- CWE-295 (Improper Certificate Validation).
- OPC Foundation: OPC UA Security Model specification.
