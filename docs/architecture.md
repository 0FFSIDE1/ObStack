# ObStack — Architecture (Phase 1 Discovery Draft)

**Status:** Discovery draft; not approved for production deployment.  
**Repository:** `0FFSIDE1/ObStack`  
**Last reviewed:** 2026-11-15

## 1. Discovery findings

The repository default branch (`main`) currently contains only `README.md`, `.gitignore`, and `LICENSE`. The README describes ObStack as a centralized observability platform for multiple projects on remote Linux servers. No existing Docker Compose, Prometheus, Grafana, Loki, Alloy, Alertmanager, Ansible, Terraform, infrastructure inventory, network configuration, TLS/DNS configuration, or test assets were found at the repository root.

The deployment environment is therefore **not yet discovered**. OS/version, CPU/RAM/disk, Docker/Compose versions, hostnames/DNS, network/VPN topology, firewall policy, TLS issuer, secrets backend, backup target, and target project/server inventory remain unknown. These must not be assumed.

## 2. Proposed logical architecture

### Central observability node (initial deployment)

- Docker Engine + Docker Compose orchestrate Prometheus, Grafana, Loki, Alertmanager, Blackbox Exporter, and Nginx TLS reverse proxy.
- Persistent storage is mounted for Prometheus TSDB, Loki data/index/compactor state, Grafana state, and Alertmanager state.
- Prometheus scrapes central service metrics and centrally reachable exporters. Remote servers behind NAT/private networks use Alloy remote-write for metrics rather than requiring inbound scrape reachability.
- Alloy on remote Linux hosts collects host/container/application telemetry and forwards metrics and logs over authenticated private connectivity (prefer WireGuard) to dedicated secured endpoints.
- Alertmanager is the primary notification router for Prometheus-originated alerts. Grafana/Loki alerting is only enabled if a clear integration path avoids competing notification pipelines.
- Grafana provisions data sources and dashboards from version-controlled files. Dashboard variables cover project, environment, server, service, and region.
- Ansible provisions hosts and installs/configures agents and only service-relevant exporters.

### Remote project nodes

- Alloy agent, Node Exporter, and cAdvisor, plus optional database/service exporters only when those services exist and the exporter is justified.
- Application metrics exposed through Prometheus-compatible instrumentation/endpoints.
- Logs collected from journald/syslog, Docker stdout/stderr, Nginx and application log files, subject to source-specific filtering/redaction and access approval.
- No exporter or Alloy debug/admin endpoint is exposed publicly. Restrict host firewall ingress to private VPN/allowlisted management sources.

## 3. Telemetry flows

### Metrics

1. Alloy discovers/collects metrics from local exporters and supported application endpoints.
2. Alloy forwards metrics through Prometheus-compatible remote-write to a private, authenticated central endpoint.
3. Prometheus stores the time series and evaluates reusable rules.
4. Prometheus alerts are sent to Alertmanager for grouping, deduplication, inhibition, routing and notifications.

A secondary pattern is central Prometheus scraping of exporter endpoints over private VPN. Use this only when central-to-host reachability and firewall rules are verified. Avoid opening exporter ports to the public Internet.

### Logs

1. Alloy collects configured local log sources.
2. Source filters and redaction remove secrets and unnecessary sensitive/PII fields before forwarding.
3. Alloy pushes logs to a private authenticated Loki endpoint over TLS.
4. Loki applies configured retention/compaction; Grafana provides project/environment/server/service exploration.

### Alerting

Prometheus rules -> Alertmanager -> configured Telegram, SMTP, Slack, or webhook receiver(s). Credentials are provided at runtime via Docker secrets or protected secret files; no credentials are committed. Firing and resolved notifications, inhibition, routing and destination delivery must be tested.

## 4. Multi-tenancy and label contract

Required low-cardinality identity labels: `project`, `environment`, `server`, `instance`, `service`, `region`, `role`. Metric labels must not contain request/user/session identifiers, emails, face/biometric identifiers, tokens or other sensitive/high-cardinality values. Loki index labels are limited to stable low-cardinality fields (project, environment, server, service, region, level/severity where appropriate); variable values stay in log content or structured metadata.

Projects are onboarded through Ansible inventory/vars and telemetry configuration. Grafana dashboards use variables and provisioning; onboarding must not require Grafana dashboard edits for every project.

## 5. Trust boundaries and security principles

- Public edge: Nginx HTTPS entry point for approved Grafana access and, only if required, authenticated telemetry endpoints.
- Private telemetry plane: preferably WireGuard between remote hosts and central node; enforce peer allowlists and host firewall rules.
- Docker service plane: dedicated Compose networks; only Nginx publishes public-facing ports. Prometheus, Loki, Alertmanager, exporters, cAdvisor, and Alloy management interfaces remain private.
- Management plane: SSH/Ansible restricted to approved operator/admin sources.
- Secrets: Docker secrets where Compose/runtime support fits, or protected secret files with strict permissions and encrypted off-host backup. `.env.example` only has placeholders.
- TLS: verify certificates end-to-end; no skip-verify settings. Plan certificate renewal and expiration monitoring.
- Container hardening: pinned images, non-root where supported, read-only FS/drop capabilities/resource constraints where compatible; document host mounts and exceptions for Node Exporter/cAdvisor.
- Log access/retention must be privacy reviewed; biometric/sensitive payloads are explicitly out of scope for collection.

## 6. Initial retention and resilience direction

Proposed starting defaults (confirm against data volume, disk sizing and policy): Prometheus 90 days; Loki 30 days. Set explicit storage limits and alert on capacity and ingestion. Retention does not imply secure deletion from backups.

The first topology is a single central node with local persistent storage and encrypted off-host backups. This is **not high availability**. Document failure modes, backup/restore verification, and recovery objectives. Future scaling path: durable object storage and scalable Loki deployment; Prometheus-compatible long-term storage (e.g. Mimir); redundant central components; independent external uptime monitoring.

## 7. Deployment and implementation constraints

- Implement configuration and automation in version control; use Ansible for repeatable central/remote provisioning and idempotent agent updates/removal.
- Do not modify production hosts or application deployment files without explicit authorization and verified inventory.
- Do not assume the existence of Terraform. If an infrastructure repository is supplied, inspect it and integrate narrowly.
- Use version-pinned upstream images and maintain an upgrade/rollback procedure; final versions require compatibility and vulnerability review at implementation time.
- Validate configs using upstream tools, test integration/failure paths in a non-production environment, and record actual results only.

## 8. Decisions required before production implementation

1. Central server OS/version, CPU, RAM, disk layout/capacity, and whether it is newly provisioned.
2. Remote Linux distributions/versions and list of projects/environments/hosts/services to onboard first.
3. VPN/network design: WireGuard already available or to be provisioned; allowed peer ranges; firewall owner; whether central inbound remote-write and Loki endpoints are reachable over VPN.
4. DNS names and TLS/certificate issuer/renewal approach.
5. Authentication and secrets mechanism, operator identity/RBAC requirements, and MFA expectations.
6. Notification destination(s) and ownership for global/project routes.
7. Backup destination, encryption/key custody, retention, and desired RPO/RTO.
8. Expected telemetry volume (hosts, scrape interval, log GB/day), data classification/privacy requirements, and retention approval.
9. Existing Ansible/Terraform/config management conventions and authorization boundaries.
10. Approval to proceed with implementation in this repository branch; no production changes are implied.

## 9. Architecture acceptance gates

- Network reachability and firewall plan reviewed.
- Secrets and TLS path selected and validated.
- Resource/storage sizing supported by expected telemetry volume.
- Retention and privacy policy confirmed.
- Remote-write/Loki ingestion secured and tested in staging.
- Backup restoration demonstrated, not merely backup creation.
- Security and configuration checks pass; remaining risks documented.
