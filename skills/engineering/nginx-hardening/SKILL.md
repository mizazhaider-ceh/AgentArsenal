---
name: nginx-hardening
description: Use when hardening an nginx 1.27 web server or reverse proxy:
  writing secure server blocks, disabling version banners, configuring modern
  TLS, adding security headers (HSTS, CSP, X-Frame-Options), rate limiting
  with limit_req, restricting request sizes and methods, running workers as a
  non-root user with tight file permissions, setting up access and error
  logging for forensics, or reviewing an existing nginx config for common
  misconfigurations. Use when the task mentions nginx config, reverse proxy
  security, TLS hardening, or web server lockdown.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [secure-coding, linux-hardening]
tools:
  - name: nginx
    version: 1.27
  - name: OpenSSL
    version: 3.4
---

nginx usually sits at the edge of the stack, terminating TLS and proxying to
application servers, which makes its configuration a high-value hardening
target. This skill covers locking down nginx 1.27: hiding version banners,
modern TLS, security headers, rate limiting, request limits, privilege
separation, safe proxying, and logging that supports incident response.
Scope is the web server layer itself, not the application behind it.

## Quick Workflow

1. Inventory the config: `nginx -T` dumps the effective configuration;
   review every server block.
2. Hide the version banner (`server_tokens off`) and remove the Server
   header where possible.
3. Terminate TLS with modern protocols and ciphers only; redirect all HTTP
   to HTTPS.
4. Add security headers: HSTS, X-Content-Type-Options, X-Frame-Options or
   frame-ancestors, Referrer-Policy, and a tight Content-Security-Policy.
5. Set request limits: client_max_body_size, client_body_timeout, and
   method restrictions.
6. Add rate limiting (limit_req) on login, API, and expensive endpoints.
7. Run worker processes as a non-root user; lock down file and directory
   permissions.
8. Harden the reverse proxy: sanitize forwarded headers, set timeouts, and
   never proxy hop-by-hop headers blindly.
9. Configure structured access and error logging, and ship logs off the
   box.
10. Test every change with `nginx -t`, reload gracefully, and verify from
    the outside with curl.

## 1. Baseline: inspect and test the config

```bash
# Show nginx version and the full effective config
nginx -v
sudo nginx -T 2>&1 | less

# Validate syntax before every reload (catches typos)
sudo nginx -t

# Graceful reload: zero-downtime config apply
sudo systemctl reload nginx
```

Put site configs in `/etc/nginx/sites-available/` symlinked to
`sites-enabled/`, and shared hardening snippets in
`/etc/nginx/conf.d/` so every server block inherits them.

## 2. Hide version banners and server identity

```bash
# /etc/nginx/conf.d/hardening.conf
server_tokens off;
```

Verify from the outside; the Server header should say only `nginx`:

```bash
curl -sI https://example.com | grep -i '^server:'
# Expected: server: nginx
```

To strip even that, use the third-party headers-more module
(`more_clear_headers Server;`) if your build includes it; otherwise the
bare `nginx` token is acceptable and honest.

## 3. Modern TLS termination

Redirect all HTTP to HTTPS, then serve TLS 1.2 and 1.3 only with a modern
cipher list:

```nginx
# /etc/nginx/sites-available/example.com
server {
    listen 80;
    server_name example.com www.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    http2 on;
    server_name example.com;

    ssl_certificate     /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS: only after you are sure HTTPS works everywhere, start with a
    # short max-age and raise it
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
}
```

Verify the handshake from the outside:

```bash
# Confirm TLS 1.0/1.1 are rejected and 1.2/1.3 accepted
openssl s_client -connect example.com:443 -tls1_1 </dev/null 2>&1 | grep -E 'Protocol|Cipher'
openssl s_client -connect example.com:443 -tls1_3 </dev/null 2>&1 | grep -E 'Protocol|Cipher'

# Check certificate chain and expiry
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
  | openssl x509 -noout -dates -issuer
```

## 4. Security headers

```nginx
# /etc/nginx/conf.d/security-headers.conf
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
# Start CSP in report-only, tighten after watching violation reports
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'" always;
```

Check the headers on a real response:

```bash
curl -sI https://example.com | grep -iE 'strict-transport|x-content-type|x-frame|content-security|referrer|permissions'
```

CSP note: a wrong CSP breaks the site. Deploy `Content-Security-Policy-Report-Only`
first, collect reports, then enforce.

## 5. Request limits and method restrictions

```nginx
# /etc/nginx/conf.d/limits.conf
client_max_body_size 10m;        # reject huge uploads early
client_body_timeout 10s;
client_header_timeout 10s;
keepalive_timeout 15s;
send_timeout 10s;

# Block methods you do not use at the server level
if ($request_method !~ ^(GET|HEAD|POST|PUT|DELETE|OPTIONS)$) {
    return 405;
}
```

Prefer `limit_except` inside location blocks for finer control:

```nginx
location /api/ {
    limit_except GET POST PUT DELETE { deny all; }
    proxy_pass http://app_backend;
}
```

## 6. Rate limiting

Define zones in the http context, then apply them where abuse hurts:
logins, password resets, API endpoints.

```nginx
# /etc/nginx/conf.d/rate-limit.conf
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;
limit_req_status 429;
```

```nginx
location /login {
    limit_req zone=login burst=5 nodelay;
    proxy_pass http://app_backend;
}

location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://app_backend;
}
```

Test that limiting triggers:

```bash
for i in $(seq 1 12); do
  curl -s -o /dev/null -w "%{http_code}\n" https://example.com/login
done
# Expect 200s then 429s
```

Rejected requests land in the error log; watch them during rollout.

## 7. Privilege separation and file permissions

```bash
# /etc/nginx/nginx.conf (top level)
user www-data;
worker_processes auto;
```

```bash
# Config readable by root only; web root readable, never writable by www-data
sudo chown -R root:root /etc/nginx
sudo chmod -R 640 /etc/nginx/nginx.conf
sudo find /etc/nginx -type d -exec chmod 750 {} \;

sudo chown -R root:www-data /var/www/example.com
sudo find /var/www/example.com -type d -exec chmod 755 {} \;
sudo find /var/www/example.com -type f -exec chmod 644 {} \;

# TLS private key: root only
sudo chmod 600 /etc/letsencrypt/live/example.com/privkey.pem

# Confirm workers run unprivileged
ps -o user,comm -C nginx
```

Never run application upload directories with execute permission, and
never let the web root be writable by the worker user.

## 8. Safe reverse proxying

```nginx
upstream app_backend {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 443 ssl;
    server_name example.com;

    location / {
        proxy_pass http://app_backend;
        proxy_http_version 1.1;

        # Forward client identity safely
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Drop hop-by-hop headers, do not blindly forward Connection
        proxy_set_header Connection "";

        # Timeouts so a hung backend cannot pile up workers
        proxy_connect_timeout 5s;
        proxy_send_timeout 15s;
        proxy_read_timeout 30s;

        # Do not let the backend override your security headers silently;
        # use proxy_hide_header for backend headers you distrust
        proxy_hide_header X-Powered-By;
    }
}
```

If nginx sits behind a CDN or load balancer, set `real_ip_header` and
`set_real_ip_from` for the proxy ranges so logs and rate limits see the
real client IP, and never trust `X-Forwarded-For` from the open internet.

## 9. Logging for forensics

```nginx
# /etc/nginx/conf.d/logging.conf
log_format forensic '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    'rt=$request_time uct=$upstream_connect_time '
                    'urt=$upstream_response_time';

access_log /var/log/nginx/access.log forensic;
error_log /var/log/nginx/error.log warn;
```

Ship logs off the box (rsyslog, filebeat, or similar) and rotate them:

```bash
# Confirm logrotate handles nginx
cat /etc/logrotate.d/nginx
# Force a rotation test
sudo logrotate -d /etc/logrotate.d/nginx 2>&1 | tail -5
```

## Edge cases

- `nginx -t` passes but reload fails silently on a bad include path.
  `nginx -T` shows exactly which files were loaded; diff against what you
  expect.
- `add_header` directives are not inherited into a location block that
  defines its own `add_header`. Repeat the headers or use a shared
  include inside every location.
- HSTS with `preload` before you are ready can brick HTTP access for
  months. Start with a short max-age, no preload, then raise it.
- Rate limiting legitimate users behind NAT: one office shares one IP.
  Combine `limit_req` with allowlists for known office ranges, or key the
  zone on an authenticated user id instead of IP for logged-in endpoints.
- `client_max_body_size` too small breaks file uploads with a confusing
  413. Set it per location for the upload endpoint instead of globally.
- HTTP/2 and `http2 on` syntax: nginx 1.25.1 and later use the `http2 on`
  directive; the old `listen 443 ssl http2` parameter still works but is
  deprecated style.

## Escalation

- Config test fails: `nginx -t` prints the file and line; fix, retest,
  and never reload on a failed test.
- 502 Bad Gateway after proxy changes: check the backend is listening
  (`ss -tlnp | grep 8000`), then read `error.log` for the upstream error
  (`connect() failed`, `no live upstreams`).
- TLS handshake failures: run `openssl s_client` with `-tls1_2` and
  `-tls1_3` to isolate protocol vs cipher issues; confirm the full chain
  is in `fullchain.pem` (missing intermediates are the usual cause).
- Permission denied on reload: the master process needs root to bind
  ports 80/443; reload via `systemctl reload nginx`, not as www-data.
- Still broken: bisect by moving site configs out of `sites-enabled`
  one at a time and reloading until the failure disappears.

## Detection and defender view

nginx misconfigurations defenders hunt for: version banners leaking
(`Server: nginx/1.27.0`), missing HSTS or CSP, TLS 1.0/1.1 still enabled,
no rate limiting on auth endpoints, directory listing on, overly broad
`location ~ \.php$` style blocks, and proxy configs that forward to
internal hosts (SSRF via misconfigured `proxy_pass` with user-controlled
variables). Detect misuse and misconfig with:

```bash
# Banner and header audit from outside
curl -sI https://example.com | grep -iE '^server:|strict-transport|content-security'

# TLS posture scan (needs testssl.sh or nmap ssl scripts)
nmap --script ssl-enum-ciphers -p 443 example.com | head -30

# 4xx/5xx spike or 429 flood in the access log (attack or mis-tuned limits)
sudo awk '$9 ~ /^(429|403)$/ {print $1}' /var/log/nginx/access.log \
  | sort | uniq -c | sort -rn | head

# Requests probing for admin paths or traversal
sudo grep -E '\.\./|/\.git/|/admin|/wp-login' /var/log/nginx/access.log | tail -20
```

Alert on: sudden 429 storms (credential stuffing), `client_max_body_size`
413 bursts (upload abuse probing), and any `proxy_pass` to non-allowlisted
upstreams after a config change. Keep a known-good `nginx -T` dump in
version control and diff it after every change.

## Key references

- nginx 1.27 documentation: https://nginx.org/en/docs/
- nginx ssl module: https://nginx.org/en/docs/http/ngx_http_ssl_module.html
- nginx limit_req module: https://nginx.org/en/docs/http/ngx_http_limit_req_module.html
- Mozilla SSL Configuration Generator (modern profile):
  https://ssl-config.mozilla.org/
- OWASP Secure Headers Project: https://owasp.org/www-project-secure-headers/
- CWE-200 (Exposure of Sensitive Information): version banners.
- CWE-319 (Cleartext Transmission): missing HTTPS redirect or HSTS.
- CWE-770 (Allocation of Resources Without Limits): missing rate limits
  and request size caps.
