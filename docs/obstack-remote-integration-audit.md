# ObStack remote integration audit — ENSAMS

Audit date: 2026-11-16. This audit is based on the ObStack repository and the supplied ENSAMS integration contract and audit. Repository configuration is not evidence that central or remote production services are deployed.

## Current architecture and implementation inventory

| Capability | Repository evidence | Classification | ENSAMS impact |
| --- | --- | --- | --- |
| Central stack | `compose.yaml` runs Prometheus, Loki, Grafana, Alertmanager, Blackbox Exporter and Nginx; internal stores bind to loopback. | IMPLEMENTED AND VERIFIED (configuration) | Existing central receivers are the reuse point. Runtime state is not verified. |
| Secure telemetry ingress | `nginx/conf.d/obstack.conf`, `docs/telemetry-ingestion.md`, and `ansible/roles/alloy/` configure TLS, per-host Basic Auth, private-CA trust, remote-write and Loki push. | IMPLEMENTED BUT INCOMPLETE | Supports agent push, but no per-application enrollment declaration or live ingestion evidence. |
| Remote application scrape | `prometheus/prometheus.yml` previously had no application jobs. It now reads generated file-SD targets from `prometheus/file_sd/`. | IMPLEMENTED BUT INCOMPLETE | Reusable path exists; ENSAMS target remains unset because the WireGuard address, host port, and Laravel-observed source are unknown. |
| Remote Alloy onboarding | `ansible/playbooks/alloy-onboarding.yml` and `ansible/roles/alloy/` stage a config only when explicitly set to adopt. | IMPLEMENTED BUT INCOMPLETE | It preserves existing containers and does not install, restart, or prove an agent. The current template defines host metrics and a Loki writer but no log source. |
| Remote host metrics | `ansible/roles/alloy/templates/config.alloy.j2` configures Alloy's Unix exporter and remote-write labels. | IMPLEMENTED BUT INCOMPLETE | Requires verified mounts/runtime integration; Docker/container, agent-health, and application exporter coverage are not established by this config. |
| Central alerts | `prometheus/rules/platform.yml`, `alertmanager/alertmanager.yml.j2` | IMPLEMENTED BUT INCOMPLETE | Platform storage/target alerts exist; central delivery defaults to a sink without a configured webhook. Application probes and target alerts are now provisioned, but application-specific metric names and alert routes need evidence. |
| Blackbox | `blackbox/config.yml`, `prometheus/prometheus.yml` | IMPLEMENTED BUT INCOMPLETE | Generic HTTP/TCP modules exist; no ENSAMS target was configured. Generated target file is now supported. |
| Dashboards | `grafana/provisioning/dashboards/obstack/central-overview.json` and provider config | IMPLEMENTED BUT INCOMPLETE | Central platform dashboard exists. Supplied ENSAMS dashboard source files are not in this repository, so import/query compatibility is unverified. |
| Retention/capacity | `compose.yaml`, `loki/config.yml`, `docs/operations/ports-capacity-failure-modes.md` | IMPLEMENTED BUT INCOMPLETE | Configured 30-day metrics and 20-day logs do not establish safe retention on the constrained host; measured ingestion is still needed. |
| Network enrollment | `ansible/roles/wireguard/`, `ansible/playbooks/cidr-overlap-discovery.yml`, `docs/network-architecture.md` | IMPLEMENTED BUT INCOMPLETE | Overlay and peer values remain provisional or absent for ENSAMS. No address or CIDR is assumed by this integration. |
| CI validation | `.github/workflows/validate.yml`, `.github/workflows/ansible-validation.yml` | IMPLEMENTED BUT INCOMPLETE | Config checks include application registration validation, generated-target drift, and pinned Alloy CLI validation of a rendered starter config. This does not establish a running or connected agent. |
| Tracing | No tracing backend or instrumentation configuration found in the relevant files. | MISSING / REQUIRES HUMAN DECISION | No tracing added because no backend is approved. |

## ENSAMS gap matrix

| Area | ENSAMS contract evidence | ObStack state | Required evidence/action |
| --- | --- | --- | --- |
| Application metrics | Laravel `GET /metrics`; internal Nginx port 8082; not published; public vhost denies it; broad Docker source default `172.16.0.0/12`. | Registration exists but disabled and without target. | Confirm tunnel address, host mapping/port, Docker/NAT source seen by Laravel, least-scope allowlist and firewall path. Preserve public denial. |
| WireGuard | No verified ENSAMS peer address/source range in supplied audit. Proposed `10.77.0.0/24` is explicitly unconfirmed. | Reusable WireGuard roles exist; values absent. | Verify route overlap, addresses, peer keys, endpoint and source filtering through the network owner. |
| Logs | JSON stderr captured by bounded Docker `json-file`; local Alloy reads the local socket; central Alloy cannot read a remote socket. | Authenticated Loki push exists, but no remote source is implemented in the staged Alloy config. | Approve agent privilege and source method; validate JSON parsing, retries/backpressure and bounded storage. Never expose Docker socket over the network. |
| Host/container metrics | ENSAMS local node-exporter, cAdvisor, PHP-FPM and Nginx exporters are operational per audit. | ObStack Alloy host metric starter; no verified remote Docker/Nginx/PHP-FPM exporter coverage. | Decide per-host exporters and verify ARM64/AMD64 support, scraping and agent health. Avoid duplicate exporters. |
| Health | `/up` is framework liveness, not dependency readiness. | Generic HTTP Blackbox path exists; generated app probes now supported. | Supply approved HTTPS URL and TLS/auth policy; validate from the intended probe source. |
| Dashboards | ENSAMS JSON paths named in the contract. | Those source JSON files are absent from this checkout. | Obtain source dashboard files, then adapt datasource UIDs, variables, labels, metric names and LogQL using real central samples. |
| Alerts | ENSAMS rule source contains queue/scheduler and service semantics per audit. | Generic target/Blackbox alerts exist. No ENSAMS rule file/data source/central route was verified. | Inspect actual rule expressions and metric names, render/validate, then test delivery end to end. |
| Migration | Local observability is operational; central collection is not proven. | Local ObStack does not manage ENSAMS local stack. | Keep all local services until each readiness gate has production evidence and human review. |

## Security and operational findings

- The direct `/metrics` scrape design is viable only after the operator validates the full path through WireGuard, host port publishing, Docker/Nginx, NAT and Laravel middleware. The source IP seen by Laravel may differ from the ObStack peer address. `X-Forwarded-For` is not an authorization mechanism.
- ENSAMS host port must bind to its verified WireGuard interface address. No public listener, broad source range, or proposed overlay value is committed as a target.
- ObStack's existing remote Alloy model initiates authenticated TLS connections to central ingestion. Log access on Docker hosts can require access to the Docker API/socket; membership in the Docker group or socket access effectively grants root-equivalent host control. Approval and a least-privilege design are required before enabling that collection mode.
- Central Loki/Prometheus are single-node services. Capacity and retention goals need measurement, and an unavailable central host interrupts ingestion. Agent queue limits and drop behavior need staging verification.
- The default Alertmanager sink delivers no notifications. An active receiver and tested firing/resolved delivery are required before migration.
- ENSAMS source dashboards/rules are referenced by the supplied audit but not included in the ObStack checkout. Blind imports would be unsafe and likely produce empty or incorrect panels.

## Implemented in this change

- Declarative, versioned registration structure and a JSON Schema in `applications/`.
- ENSAMS registration with verified facts only and unresolved network/environment fields left null. It is disabled until mandatory values are supplied.
- Deterministic Prometheus file-SD generation for app metrics and health probes; generated targets are committed and CI checks drift.
- Central scrape/probe jobs and actionable target/probe alerts with low-cardinality labels.
- Migration readiness record with evidence states and gates.

## Missing production values and approvals

The following are unresolved and prevent live ENSAMS onboarding: verified WireGuard overlay and peer address; central scrape/probe source identity; remote metrics host port and bind interface; effective Laravel source IP after Docker/NAT; actual `APP_ENV`; verified DNS/TLS/auth policy for `/up`; Docker log collection privilege decision; agent/exporter versions and architecture evidence; central notification receiver; ENSAMS dashboard/rule JSON; actual retention and backup/recovery evidence.

No production infrastructure, ENSAMS application, remote host, AWS resource, key, firewall, or secret was changed. Configuration validation alone is not proof of connectivity or end-to-end telemetry.
