---
name: mobile-android-dynamic-network-interception
description: Use when you need to capture and analyze an Android app's
  network traffic during an authorized test. Covers proxy configuration
  with adb, installing a Burp Suite CA into the Android system trust
  store, bypassing certificate pinning with Frida 16.5 and objection
  1.11, capturing with tcpdump and Wireshark 4.2 on the device, handling
  WebSockets and non-HTTP protocols, and mapping the API surface from
  captured traffic. Use when the parent mobile-android-dynamic workflow
  needs decrypted traffic, when static analysis listed endpoints to
  verify, or when you must document exactly what data the app sends.
version: 1.0.0
domain: mobile
lifecycle: stable
last_verified: 2026-10-23
parent: mobile-android-dynamic
requires: [mobile-android-dynamic]
extends: []
relates: [mobile-android-dynamic]
tools:
  - name: Burp Suite
    version: 2024.12
  - name: Frida
    version: 16.5
  - name: objection
    version: 1.11
  - name: adb
    version: 35.0
  - name: Wireshark
    version: 4.2
  - name: Python
    version: 3.12
---

Network interception puts your proxy between the app and its servers
so you can read, modify, and replay the API traffic. It is the highest
value dynamic technique for business apps because the traffic shows
exactly what data leaves the device. This sub-skill covers the full
chain: proxy setup, CA installation, pinning bypass, packet capture
fallbacks, and turning a capture into an API map. Authorized targets
and test devices only.

## Quick Workflow

1. Start Burp Suite on the workstation and note the proxy port.
2. Set the device proxy with adb and confirm it took effect.
3. Install the Burp CA into the Android system trust store.
4. Exercise the app and confirm decrypted HTTPS in Burp.
5. If traffic stays encrypted, bypass pinning with objection or
   Frida.
6. For non-HTTP traffic, capture packets on the device with tcpdump.
7. Map the API: hosts, endpoints, authentication, and sensitive
   fields.
8. Clear the proxy and remove test artifacts when done.

## 1. Proxy configuration

```bash
# Emulator: 10.0.2.2 reaches the host. Physical device: use the workstation LAN IP.
adb shell settings put global http_proxy 10.0.2.2:8080
adb shell settings get global http_proxy
# Expected: 10.0.2.2:8080

# Burp must listen on all interfaces for a physical device
# (Proxy > Options > Bind to address: All interfaces)
```

Some apps ignore the system proxy setting. For those, redirect at the
network layer with iptables on the rooted device:

```bash
# Redirect all port 443 traffic through Burp's invisible proxying
adb shell "su -c 'iptables -t nat -A OUTPUT -p tcp --dport 443 -j DNAT --to-destination 10.0.2.2:8080'"
# Burp: enable invisible proxying on the listener (Support invisible proxying)
```

Remove the rule afterward:

```bash
adb shell "su -c 'iptables -t nat -D OUTPUT -p tcp --dport 443 -j DNAT --to-destination 10.0.2.2:8080'"
adb shell settings put global http_proxy :0
```

## 2. Installing the Burp CA in the system store

Android 7+ ignores user-installed CAs by default, so the Burp CA must
go into the system trust store on a rooted device.

```bash
# Export Burp's CA in DER format (Proxy > Options > Import/export CA certificate)
# Convert and name it by its subject hash
openssl x509 -inform DER -in cacert.der -out /tmp/burp-ca.pem
HASH=$(openssl x509 -inform PEM -subject_hash_old -in /tmp/burp-ca.pem | head -1)
echo "hash: $HASH"
cp /tmp/burp-ca.pem /tmp/${HASH}.0

adb push /tmp/${HASH}.0 /data/local/tmp/
adb shell "su -c 'mount -o rw,remount /system'"
adb shell "su -c 'cp /data/local/tmp/${HASH}.0 /system/etc/security/cacerts/'"
adb shell "su -c 'chmod 644 /system/etc/security/cacerts/${HASH}.0'"
adb shell "su -c 'mount -o ro,remount /system'"

# Verify the system sees it
adb shell "su -c 'ls /system/etc/security/cacerts/' | grep $HASH"
```

Rebooting some emulator images wipes /system changes; if the CA
vanishes, use an emulator image with writable system or re-push at
the start of each session.

## 3. Confirming interception and bypassing pinning

Exercise the app: log in, refresh, search. In Burp's HTTP history you
should see full requests and responses.

```bash
# Quick check that traffic is flowing through the proxy
# In Burp: Proxy > HTTP history should show the app's hosts
# TLS handshake should list Burp's CA as issuer (Proxy > Intercept off, just history)
```

If you see CONNECT entries with no decrypted content, or TLS alerts,
the app pins. First try objection:

```
android sslpinning disable --quiet
```

Then the Frida pattern from the ssl-pinning-bypass sub-skill for the
specific library (OkHttp, TrustKit, network security config pins).
Re-test after each attempt; pinning is per host, so confirm every
important host, not just the first one.

## 4. Packet capture fallback with tcpdump

When the proxy cannot see the traffic (QUIC, raw TLS sockets, custom
protocols), capture packets on the device and analyze offline.

```bash
# Push a static tcpdump build for the device architecture
adb push tcpdump-arm64 /data/local/tmp/tcpdump
adb shell "chmod 755 /data/local/tmp/tcpdump"

# Capture during an app session
adb shell "su -c '/data/local/tmp/tcpdump -i any -w /data/local/tmp/cap.pcap port not 22'"

# Pull and open in Wireshark
adb pull /data/local/tmp/cap.pcap ./
wireshark cap.pcap
```

In Wireshark, start with the conversation statistics
(Statistics > Conversations) to find unexpected hosts, then follow
TCP streams. For TLS streams you cannot decrypt, the handshake still
reveals SNI hostnames and certificate details, which maps the app's
server footprint.

To decrypt TLS offline when you hold the session keys, hook
SSLKEYLOGFILE-style export with Frida at the native layer and load
the key log into Wireshark. This is advanced; the proxy path should
be exhausted first.

## 5. WebSocket and non-HTTP traffic

```bash
# In Burp, WebSockets appear under Proxy > WebSockets history
# Confirm the app's realtime channel: look for 101 Switching Protocols
```

For MQTT, custom binary protocols, or raw sockets, hook the socket
layer with Frida to capture plaintext before encryption:

```javascript
// Dump plaintext at the SSLSocket layer
Java.perform(function () {
    var SSLSocket = Java.use('javax.net.ssl.SSLSocket');
    // Hook the output stream write via the socket's streams is complex;
    // simpler: hook OkHttp's WebSocketListener or the app's socket wrapper
    // identified from static analysis
    var Wrapper = Java.use('com.example.target.SocketWrapper');
    Wrapper.send.overload('java.lang.String').implementation = function (msg) {
        console.log('[*] socket send: ' + msg.slice(0, 200));
        return this.send(msg);
    };
});
```

Document the protocol: message format, authentication, and whether
sensitive data crosses it. Realtime channels often carry chat,
location, or transaction data with weaker protections than the REST
API.

## 6. Building the API map

Turn the capture into the deliverable the rest of the test uses:

```bash
# Export Burp history and summarize hosts
# (Burp: select history entries > Save selected items, then parse)
python3 - <<'EOF'
import xml.etree.ElementTree as ET
tree = ET.parse('burp-history.xml')
hosts = {}
for item in tree.getroot().iter('item'):
    host = item.find('host').text
    path = item.find('path').text.split('?')[0]
    hosts.setdefault(host, set()).add(path)
for host, paths in sorted(hosts.items()):
    print(f"\n## {host} ({len(paths)} endpoints)")
    for p in sorted(paths)[:15]:
        print(f"  {p}")
EOF
```

Example output shape:

```
## api.example.com (23 endpoints)
  /v2/auth/login
  /v2/auth/refresh
  /v2/users/me
  /v2/users/me/payment-methods
```

For each host note: authentication mechanism (bearer token, cookie,
client cert), sensitive fields in requests and responses (tokens,
PII, card data), and transport (TLS version from the handshake).
Endpoints that return other users' data with only a client-supplied
id are the IDOR candidates for the next test phase.

## 7. Modifying and replaying traffic

```bash
# In Burp: right-click a request > Send to Repeater
# Modify parameters and observe; document every mutated request
```

Standard mutations for the authorized test: removing the auth
header, swapping user ids between the client's test accounts,
tampering prices or quantities, replaying a state-changing request
twice. Each mutation gets one line in the notes: request, change,
response, verdict.

## Edge cases

- The app uses its own DNS (DNS-over-HTTPS) and bypasses your
  host-based rules. Block DoH at the lab firewall or override with
  iptables DNAT for port 53 as well as 443.
- Traffic is pinned and the bypass fails on a banking-hardened app.
  Document the effective pinning, and ask the client for a test
  build with pinning disabled; do not burn days on one control.
- The emulator's proxy setting does not affect the app. Some apps
  read proxy settings at startup only; set the proxy before
  launching the app, or use the iptables redirect which cannot be
  ignored.
- Burp's CA expires or the hash filename is wrong. The app fails
  closed with certificate errors, which actually confirms your CA
  is being evaluated. Re-export the CA and recheck the hash.
- Huge media uploads pollute the capture. Filter Burp history by
  MIME type or host to keep the API map readable.
- The app certificate-pins only some hosts. Verify host by host;
  mixed pinning coverage is itself a reportable inconsistency.

## Escalation

- You cannot decrypt traffic for the core API and the test needs
  it. Escalate to the engagement lead for a pinning-disabled test
  build; this is a routine authorized request.
- Captured traffic shows credentials or PII in cleartext or in URLs.
  Capture a clean sample, stop, and report; cleartext credentials
  are a High finding that does not need further exploitation.
- The traffic reveals undocumented hosts outside the agreed scope.
  Note them as observed, do not probe them, and confirm scope
  before any active testing.
- The app uses mutual TLS with a client certificate embedded in the
  app. Extracting it for proxy use is authorized on the test build;
  document the extraction since an embedded client cert is itself a
  finding about key storage.

## Detection and defender view

Interception is detected through pinning, proxy detection (checking
the system proxy setting), and VPN or proxy detection heuristics.
The durable defenses are pinning plus attestation, so that even a
successful proxy position yields rejected requests, and minimizing
sensitive data in transit in the first place. Your report should
state plainly which hosts were interceptable and which resisted,
because "all API traffic was readable after a one-command bypass"
versus "pinning held on all hosts" tells the client exactly where
they stand.

## Key references

- Burp Suite mobile and proxy documentation:
  https://portswigger.net/burp/documentation
- Android network security configuration:
  https://developer.android.com/training/articles/security-config
- Frida CodeShare pinning bypasses:
  https://codeshare.frida.re/
- Wireshark documentation: https://www.wireshark.org/docs/
- OWASP MSTG network communication testing:
  https://mas.owasp.org/MSTG/
- OWASP MASVS network requirements:
  https://mas.owasp.org/MASVS/
- tcpdump man page: https://www.tcpdump.org/manpages/tcpdump.1.html
