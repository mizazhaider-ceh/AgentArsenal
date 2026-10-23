---
name: prometheus-monitoring
description: Use when setting up or debugging Prometheus monitoring on an
  authorized engineering task. Covers Prometheus 3.1 server config and
  targets, PromQL queries for RED and USE metrics, recording rules,
  Alertmanager 0.28 routing and silences, node_exporter 1.8 host metrics,
  Grafana 11.5 dashboards, and alert runbook practices. Use when adding
  observability to a service, writing alerts that page correctly,
  debugging a silent alert, or reviewing monitoring for gaps.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [linux-hardening, docker-deep]
tools:
  - name: Prometheus
    version: 3.1
  - name: Grafana
    version: 11.5
  - name: node_exporter
    version: 1.8
---

Prometheus scrapes numeric metrics from targets, stores them as time
series, and evaluates alert rules over them. This skill covers the
operator loop: instrument and scrape, query with PromQL, alert with
Alertmanager, visualize with Grafana, and keep alerts actionable.
All examples target Prometheus 3.1, Alertmanager 0.28,
node_exporter 1.8, and Grafana 11.5.

## Quick Workflow

1. Deploy node_exporter on hosts and expose `/metrics` on
   applications.
2. Configure Prometheus scrape jobs with sensible intervals and
   labels.
3. Verify targets are UP before writing any query.
4. Write PromQL for the RED metrics (rate, errors, duration) per
   service and USE metrics (utilization, saturation, errors) per
   resource.
5. Add recording rules for expensive queries used by dashboards.
6. Write alert rules with clear severity, summary, and runbook
   links; route them in Alertmanager.
7. Build Grafana dashboards from the same queries; one dashboard
   per service.
8. Tune: silence noise, fix flapping alerts, and review alert
   quality monthly.

## 1. Scrape configuration and targets

```bash
mkdir -p prometheus && cat > prometheus/prometheus.yaml <<'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: nodes
    static_configs:
      - targets: ["web1:9100", "web2:9100", "db1:9100"]
        labels:
          team: platform

  - job_name: myapp
    metrics_path: /metrics
    static_configs:
      - targets: ["app1:8080", "app2:8080"]
EOF

# Validate the config before reloading
promtool check config prometheus/prometheus.yaml

# Start Prometheus with the config
prometheus --config.file=prometheus/prometheus.yaml \
  --storage.tsdb.path=/var/lib/prometheus

# Reload config without restart after edits
curl -X POST localhost:9090/-/reload
```

Check target health first when metrics go missing: the Targets page
(or API) shows UP, DOWN, and the last scrape error.

```bash
curl -s localhost:9090/api/v1/targets | head -c 600; echo
```

## 2. node_exporter host metrics

```bash
# Run node_exporter on each host (port 9100)
node_exporter --collector.systemd --collector.processes &

# Verify metrics flow
curl -s localhost:9100/metrics | grep -E '^node_cpu_seconds_total' | head -3
curl -s localhost:9100/metrics | grep -E '^node_memory_MemAvailable_bytes'
```

Key host queries (run in the Prometheus expression browser or via
API):

```bash
# CPU usage percent across all CPUs, per instance
# 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage percent
# 100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))

# Disk usage percent per mountpoint
# 100 * (1 - (node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes))

# Load average vs CPU count (saturation signal)
# node_load1 / count by(instance) (node_cpu_seconds_total{mode="idle"})
```

```bash
# Query via API for scripting and verification
curl -s -G localhost:9090/api/v1/query \
  --data-urlencode 'query=up{job="nodes"}' | head -c 400; echo
```

## 3. PromQL patterns for services

Application metrics follow the RED pattern: Rate, Errors, Duration.
Assume the app exposes `http_requests_total` (counter) and
`http_request_duration_seconds` (histogram).

```bash
# Request rate per second, by status code
# sum by(status) (rate(http_requests_total[5m]))

# Error rate percent (5xx)
# 100 * sum(rate(http_requests_total{status=~"5.."}[5m]))
#   / sum(rate(http_requests_total[5m]))

# p95 latency in seconds
# histogram_quantile(0.95,
#   sum by(le) (rate(http_request_duration_seconds_bucket[5m])))

# p99 latency, grouped by endpoint
# histogram_quantile(0.99,
#   sum by(endpoint, le) (rate(http_request_duration_seconds_bucket[5m])))

# Requests in flight (gauge)
# http_requests_in_flight
```

Counter rates need `[5m]` style ranges; instant queries on raw
counters are meaningless. Always aggregate with `sum by(...)` before
dividing, or a single noisy series skews the ratio.

## 4. Recording rules

```bash
cat > prometheus/rules/record.yaml <<'EOF'
groups:
  - name: service-slo
    interval: 30s
    rules:
      - record: job:http_request_rate_5m
        expr: sum by(job) (rate(http_requests_total[5m]))

      - record: job:http_error_ratio_5m
        expr: |
          sum by(job) (rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum by(job) (rate(http_requests_total[5m]))

      - record: job:http_latency_p95_5m
        expr: |
          histogram_quantile(0.95,
            sum by(job, le) (rate(http_request_duration_seconds_bucket[5m])))
EOF

promtool check rules prometheus/rules/record.yaml
```

Recording rules precompute expensive queries so dashboards stay
fast. Name them `level:metric:operation` (instance, job, or group
level first). Reference the recorded series in alerts and
dashboards, not the raw expression.

## 5. Alert rules and Alertmanager routing

```bash
cat > prometheus/rules/alerts.yaml <<'EOF'
groups:
  - name: service-alerts
    rules:
      - alert: HighErrorRate
        expr: job:http_error_ratio_5m > 0.05
        for: 5m
        labels:
          severity: page
          team: platform
        annotations:
          summary: "High 5xx rate on {{ $labels.job }}"
          description: "Error ratio is {{ $value | printf \"%.2f\" }} for 5m"
          runbook: "https://wiki.example/runbooks/high-error-rate"

      - alert: InstanceDown
        expr: up{job="nodes"} == 0
        for: 2m
        labels:
          severity: page
        annotations:
          summary: "Instance {{ $labels.instance }} down"

      - alert: DiskFilling
        expr: |
          100 * (1 - (node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"}
            / node_filesystem_size_bytes)) > 85
        for: 10m
        labels:
          severity: ticket
        annotations:
          summary: "Disk over 85% on {{ $labels.instance }}:{{ $labels.mountpoint }}"
EOF

promtool check rules prometheus/rules/alerts.yaml
promtool test rules test.yaml  # unit-test alert expressions
```

```bash
cat > alertmanager/alertmanager.yaml <<'EOF'
global:
  resolve_timeout: 5m

route:
  receiver: team-platform
  group_by: [alertname, job]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - matchers: [severity = "page"]
      receiver: pagerduty-critical
      continue: true
    - matchers: [severity = "ticket"]
      receiver: team-platform

receivers:
  - name: team-platform
    webhook_configs:
      - url: https://chat.example/hooks/alerts
  - name: pagerduty-critical
    pagerduty_configs:
      - service_key: <pagerduty-integration-key>
EOF

amtool check-config alertmanager/alertmanager.yaml
```

Every alert needs a runbook link and a severity that matches its
urgency. `for: 5m` prevents paging on blips; `repeat_interval`
stops the 3 AM repeat page for an acknowledged issue.

## 6. Grafana dashboards

```bash
# Point Grafana at Prometheus as a data source, then build panels
# from the same PromQL used in alerts. Provision dashboards as code:

mkdir -p grafana/provisioning/dashboards
cat > grafana/provisioning/dashboards/service.yaml <<'EOF'
apiVersion: 1
providers:
  - name: services
    folder: Services
    type: file
    options:
      path: /etc/grafana/dashboards
EOF
```

Dashboard discipline: one dashboard per service with the same four
panels (rate, error ratio, p50/p95/p99 latency, saturation), plus a
host dashboard per fleet. Dashboards in git, provisioned on deploy;
hand-built dashboards in the UI get lost and drift.

## 7. Silences, inhibition, and alert hygiene

```bash
# Silence a noisy alert during maintenance (expires automatically)
amtool silence add alertname="DiskFilling" instance="web1" \
  --comment "disk expansion scheduled" --duration 4h

# List active silences
amtool silence query

# Expire a silence early
amtool silence expire <silence-id>
```

Inhibit cascading alerts: when `InstanceDown` fires, suppress the
`HighErrorRate` alerts from that instance so one outage pages once,
not twenty times. Review monthly: any alert that fired 50 times
with zero action taken is either miscalibrated or missing its
runbook; fix the threshold or delete the alert.

## Edge cases

- Targets show DOWN with "connection refused". The exporter is not
  running, the port is wrong, or a firewall blocks scraping;
  check from the Prometheus host with curl, not from your laptop.
- `rate()` returns no data for new counters. Rate needs at least
  two samples in the range; wait two scrape intervals after
  deploying a new metric.
- Alert flaps between firing and resolved. Widen `for:` or add
  hysteresis via a higher resolve threshold; flapping alerts train
  people to ignore pages.
- Recording rule slows Prometheus. The expression is too
  expensive (high-cardinality `by` labels); reduce label
  cardinality or lengthen the rule interval.
- Disk fills on the Prometheus server. Set
  `--storage.tsdb.retention.time=30d` and size, monitor
  `prometheus_tsdb_storage_blocks_bytes`, and consider remote
  write to long-term storage.
- Histograms show wrong quantiles. The bucket boundaries do not
  match the latency range; define buckets for your actual
  latencies (e.g. 0.005 to 10 seconds), not library defaults.
- Alertmanager config reload fails silently. Always run
  `amtool check-config` before sending SIGHUP; a bad config
  leaves the old one running and your new routes never apply.

## Detection and defender view

For engineering skills this section covers detecting misuse and
misconfiguration. Monitoring misconfiguration shows up as
Prometheus and Alertmanager exposed without authentication on the
internet (they leak infrastructure topology and sometimes
credentials in labels), alerts with no runbooks, and paging rules
that nobody follows. Detect gaps by auditing which services have
no RED metrics, which alerts fired without any human action, and
whether `up == 0` alerts exist for every scrape job. An attacker
who reaches the Prometheus API learns your hostnames, versions
(from `*_build_info` metrics), and traffic patterns; restrict API
access and strip sensitive labels. Alert fatigue is a security
issue: when everything pages, the real intrusion alert gets
acknowledged unread.

## Key references

- Prometheus 3.1 documentation: https://prometheus.io/docs/
- PromQL basics: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Alertmanager 0.28 configuration:
  https://prometheus.io/docs/alerting/latest/configuration/
- node_exporter 1.8: https://github.com/prometheus/node_exporter
- Grafana 11.5 documentation: https://grafana.com/docs/grafana/
- Google SRE Workbook (alerting): https://sre.google/workbook/alerting-on-slos/
- CWE-778 (Insufficient Logging): monitoring gaps that hide
  incidents.
- CWE-400 (Uncontrolled Resource Consumption): unbounded metric
  cardinality.
