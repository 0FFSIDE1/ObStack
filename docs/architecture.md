## 1. Discovery findings

The repository default branch (`main`) currently contains only `README.md`, `.gitignore`, and `LICENSE`. The README describes ObStack as a centralized observability platform for multiple projects on remote Linux servers. No existing Docker Compose, Prometheus, Grafana, Loki, Alloy, Alertmanager, Ansible, Terraform, infrastructure inventory, network configuration, TLS/DNS configuration, or test assets were found at the repository root.

### Central host facts supplied by the user

- Candidate OS: Ubuntu 22, 24, or 26 (exact release not yet selected).
- Resources: 2 vCPU, 2 GB RAM, 8–14 GB disk.
- Docker Engine: not installed.
- These are user-provided intended specifications, not independently verified host facts.

**Sizing assessment:** this is severely constrained for a full centralized stack with persistent metrics and logs. In particular, 8–14 GB disk cannot reasonably accommodate OS/Docker image layers, Prometheus TSDB, Loki data/index/compaction, Grafana/Alertmanager state, and useful retention/backups with safe headroom. 2 GB RAM also leaves little room for the complete set of services and ingestion/query peaks. Treat this host as a lab/minimal proof-of-concept, not production-grade capacity, unless scope and telemetry retention are drastically reduced and carefully measured.

**Recommended planning baseline (engineering estimate, not vendor minimum):** Ubuntu 24.04 LTS, at least 4 vCPU, 8 GB RAM, and 100 GB SSD for a modest initial fleet; adjust disk sizing using expected series count, scrape interval, log GB/day, retention, and backup policy. A larger fleet or meaningful log volume may require considerably more storage and RAM. Ubuntu 24.04 LTS is preferred over interim release selection for the initial stable deployment; verify support lifecycle and package availability during implementation.

The deployment environment is otherwise **not yet discovered**. Docker/Compose versions, hostnames/DNS, network/VPN topology, firewall policy, TLS issuer, secrets backend, backup target, and target project/server inventory remain unknown. These must not be assumed.
## 2. Proposed logical architecture

- Docker Engine + Docker Compose orchestrate Prometheus, Grafana, Loki, Alertmanager, Blackbox Exporter, and Nginx TLS reverse proxy.
- Persistent storage is mounted for Prometheus TSDB, Loki data/index/compactor state, Grafana state, and Alertmanager state.
- Prometheus scrapes central service metrics and centrally reachable exporters. Remote servers behind NAT/private networks use Alloy remote-write for metrics rather than requiring inbound scrape reachability.
- Alloy on remote Linux hosts collects host/container/application telemetry and forwards metrics and logs over authenticated private connectivity (prefer WireGuard) to dedicated secured endpoints.
- Alertmanager is the primary notification router for Prometheus-originated alerts. Grafana/Loki alerting is only enabled if a clear integration path avoids competing notification pipelines.
- Grafana provisions data sources and dashboards from version-controlled files. Dashboard variables cover project, environment, server, service, and region.
- Ansible provisions hosts and installs/configures agents and only service-relevant exporters.

Remote nodes run Alloy, Node Exporter, cAdvisor and only relevant optional exporters. Applications expose Prometheus-compatible metrics. Logs from journald/syslog, Docker, Nginx and application files are filtered/redacted before forwarding.

## 3. Telemetry flows

### Metrics

Alloy collects local exporters and application endpoints and sends Prometheus remote-write over private authenticated connectivity to central Prometheus. Central Prometheus also scrapes targets only where private VPN reachability and firewall policy are verified. Prometheus evaluates rules and sends alerts to Alertmanager.

### Logs

Alloy collects approved sources, filters/redacts secrets and unnecessary sensitive/PII fields, then pushes to authenticated TLS-protected Loki. Loki applies retention and compaction; Grafana explores logs using stable labels.

### Alerting

Prometheus rules -> Alertmanager -> configured Telegram, SMTP, Slack or webhook receivers. Credentials are runtime secrets/protected files. Firing/resolved routes and delivery must be tested.

## 4. Multi-tenancy and label contract

Required low-cardinality identity labels: `project`, `environment`, `server`, `instance`, `service`, `region`, `role`. Metric labels must not contain request/user/session identifiers, emails, face/biometric identifiers, tokens or other sensitive/high-cardinality values. Loki index labels are limited to stable fields; variable values stay in log content or structured metadata.

## 5. Trust boundaries and security principles

- Public edge: Nginx HTTPS for approved Grafana access and, only if required, secured telemetry endpoints.
- Private telemetry plane: preferably WireGuard with peer allowlists and host firewall rules.
- Docker service plane: dedicated Compose networks; internal services and exporters remain private.
- Management plane: SSH/Ansible restricted to approved sources.
- Secrets: Docker secrets or protected files; encrypted off-host backup; placeholders only in `.env.example`.
- TLS verification remains enabled; plan renewal and certificate expiry monitoring.
- Pinned images, non-root where supported, read-only FS/drop capabilities/resource controls where compatible; document host mounts and exceptions.
- Log collection is privacy-reviewed; sensitive biometric payloads are excluded.

## 6. Retention and resilience direction

Proposed starting defaults subject to policy and capacity: Prometheus 90 days; Loki 30 days. Explicit storage limits and capacity alerts are required. Retention does not guarantee deletion from backups.

Initial single central node with local persistent storage and encrypted off-host backups is **not high availability**. Future path: object storage, scalable Loki, Prometheus-compatible long-term storage such as Mimir, redundant infrastructure and independent uptime monitoring.

## 7. Deployment constraints

Use Ansible for repeatable idempotent provisioning. Do not modify production hosts or application configs without explicit authorization and verified inventory. Do not assume Terraform exists. Pin images and maintain upgrade/rollback procedures. Validate with upstream tools and record actual test results only.

## 8. Decisions required

1. Confirm OS release and whether to resize the central host to the recommended planning baseline.
2. Remote Linux distributions and first project/server/service inventory.
3. VPN/network topology, allowed peers, firewall owner and telemetry endpoint reachability.
4. DNS and TLS issuer/renewal.
5. Authentication, secrets backend, RBAC and MFA expectations.
6. Notification destinations and routing owners.
7. Backup destination, encryption/key custody, retention, RPO/RTO.
8. Telemetry volume, data classification/privacy, and retention approval.
9. Existing Ansible/Terraform conventions and change authorization boundaries.
10. Approval for implementation; no production changes implied.

## 9. Architecture acceptance gates

- Network/firewall plan reviewed.
- Secrets and TLS validated.
- Storage/resource sizing matches expected telemetry.
- Retention/privacy approved.
- Secure remote ingestion tested in staging.
- Backup restoration demonstrated.
- Security/configuration checks pass and residual risks documented.
