## 1. Discovery findings

The repository default branch (`main`) currently contains only `README.md`, `.gitignore`, and `LICENSE`. The README describes ObStack as a centralized observability platform for multiple projects on remote Linux servers. No existing Docker Compose, Prometheus, Grafana, Loki, Alloy, Alertmanager, Ansible, Terraform, infrastructure inventory, network configuration, TLS/DNS configuration, or test assets were found at the repository root.

### Central host facts supplied by the user

- OS: Ubuntu 24.04 LTS (user-confirmed intended release; host state not independently verified).
- CPU architecture: **ARM64 / AWS Graviton** (user-confirmed; instance type and actual host state still need verification).
- Initial resources are fixed for now: 2 vCPU, 2 GB RAM, 14 GB disk on AWS EC2. User says the host could be increased later. The EBS volume type and whether the 14 GB refers to root volume capacity still need confirmation.
- Docker Engine: not installed.
- Initial monitoring scope: approximately **5–10 projects** and **10 remote servers** (user-confirmed); exact project names, project-to-server mapping, environments, and workload inventory remain to be discovered.
- Remote OS/architecture: all ten remote servers are **Ubuntu 24.04 LTS**: **5 AMD64 (`amd64`) and 5 ARM64 (`arm64`)** (user-confirmed). The per-host architecture mapping is still needed.
- Requested retention: metrics 30 days; logs 20 days.
- These are user-provided intended specifications, not independently verified host facts.

**Architecture compatibility requirement:** the central EC2 host is ARM64, while the remote fleet includes both ARM64 and AMD64. Every central container image and supporting binary must therefore provide a verified `linux/arm64` build. Remote-agent deployment artifacts, packages, container images and exporter binaries must support both `linux/arm64` and `linux/amd64`. Prefer verified multi-platform upstream container images or architecture-specific package downloads selected from Ansible facts (`ansible_architecture` / normalized Debian architecture). Do not assume a single binary or image manifest works on both. Validate image manifests and checksums for the central ARM64 host and both remote architectures, and run configuration/integration checks on at least one ARM64 and one AMD64 remote representative before fleet rollout. Keep architecture-specific exceptions explicit in inventory/group vars. The central instance type and actual kernel architecture must be verified before installation.

**Capacity assessment:** the initial host is severely constrained for a centralized observability platform. The 14 GB EC2 disk must also accommodate OS, Docker image layers, persistent service state, indexes/compaction, and operational headroom; it is unlikely to support meaningful telemetry volume with the requested retention safely. 2 GB RAM limits the number of services and ingest/query headroom. Therefore, treat the initial deployment as a tightly scoped pilot / low-volume MVP, not production-capacity assurance. Retention goals must be validated against measured ingest rates and disk usage; configure hard storage limits, capacity alerts, and a documented degradation/scale-up procedure. Do not silently shorten retention: if the capacity budget is exceeded, alert and require an explicit policy decision or host expansion.

**Scale-up path (engineering guidance, not vendor minimum):** first consider increasing disk to a dedicated SSD sized from measured daily metrics/log ingestion and retention plus OS, indexes, compaction, backup, and safety headroom; then increase RAM/CPU based on service utilization and query/ingest load. A planning baseline of 4 vCPU, 8 GB RAM, and 100 GB SSD may suit a modest initial fleet, but is not a guarantee and should be recalculated from observed telemetry. Ubuntu 24.04 LTS supports both amd64 and arm64; verify upstream agent/exporter image manifests and package availability during implementation.

The deployment environment is otherwise **not yet discovered**. Docker/Compose versions, hostnames/DNS, network/VPN topology, firewall policy, TLS issuer, secrets backend, backup target, and target project/server inventory remain unknown. These must not be assumed.
## 2. Proposed logical architecture

- Docker Engine + Docker Compose orchestrate Prometheus, Grafana, Loki, Alertmanager, Blackbox Exporter, and Nginx TLS reverse proxy. All selected central images must explicitly support `linux/arm64`; pin verified immutable digests where possible.
- Persistent storage is mounted for Prometheus TSDB, Loki data/index/compactor state, Grafana state, and Alertmanager state.
- Prometheus scrapes central service metrics and centrally reachable exporters. Remote servers behind NAT/private networks use Alloy remote-write for metrics rather than requiring inbound scrape reachability.
- Alloy on remote Linux hosts collects host/container/application telemetry and forwards metrics and logs over authenticated private connectivity (prefer WireGuard) to dedicated secured endpoints.
- Alertmanager is the primary notification router for Prometheus-originated alerts. Grafana/Loki alerting is only enabled if a clear integration path avoids competing notification pipelines.
- Grafana provisions data sources and dashboards from version-controlled files. Dashboard variables cover project, environment, server, service, and region.
- Ansible provisions hosts and installs/configures agents and only service-relevant exporters. Remote-agent roles must be architecture-aware and support both ARM64 and AMD64.

Remote nodes run Alloy, Node Exporter, cAdvisor and only relevant optional exporters. Applications expose Prometheus-compatible metrics. Logs from journald/syslog, Docker, Nginx and application files are filtered/redacted before forwarding. Confirm ARM64 and AMD64 support for every selected exporter and pin compatible multi-platform image digests where available.

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

User-requested retention targets: **Prometheus metrics 30 days; Loki logs 20 days**. These targets are not yet capacity-validated against the fixed initial AWS EC2 2 vCPU / 2 GB RAM / 14 GB disk host. Implementation must configure retention explicitly, enforce storage caps, and alert on disk usage, ingestion, and service resource pressure. Estimate capacity from observed metrics TSDB growth and log GB/day; include indexes, compaction, image/OS footprint, backup requirements, and safe free-space headroom. Record measured retention behavior in staging/pilot and raise a scale-up recommendation before disk pressure jeopardizes data or service availability. Do not claim the requested retention is guaranteed until measured.

Initial single central node with local persistent storage and encrypted off-host backups is **not high availability**. Backup destination, backup retention, RPO/RTO, and restoration test remain undecided. Future path: object storage, scalable Loki, Prometheus-compatible long-term storage such as Mimir, redundant infrastructure and independent uptime monitoring.

## 7. Deployment constraints

Use Ansible for repeatable idempotent provisioning. Do not modify production hosts or application configs without explicit authorization and verified inventory. Do not assume Terraform exists. Pin images and maintain upgrade/rollback procedures. Validate with upstream tools and record actual test results only. Initial resource constraints require service/resource limits and conservative component scope, followed by measured scale-up when needed. Central provisioning must enforce ARM64-compatible artifacts; remote provisioning must branch safely for `arm64` and `amd64`; test all required architectures before rollout.

## 8. Decisions required

1. Confirm EC2 storage details (EBS volume type; root-volume capacity); host expansion is possible but not currently approved/specified.
2. Verify central EC2 instance type/kernel architecture and map each of the ten remote servers to ARM64 or AMD64; gather project/server/service inventory.
3. VPN/network topology, allowed peers, firewall owner and telemetry endpoint reachability.
4. DNS and TLS issuer/renewal.
5. Authentication, secrets backend, RBAC and MFA expectations.
6. Notification destinations and routing owners.
7. Backup destination, encryption/key custody, retention, RPO/RTO.
8. Telemetry volume, data classification/privacy, and retention approval (30-day metrics / 20-day logs are user requested; capacity validation pending).
9. Existing Ansible/Terraform conventions and change authorization boundaries.
10. Approval for implementation; no production changes implied.

## 9. Architecture acceptance gates

- Network/firewall plan reviewed.
- Secrets and TLS validated.
- Storage/resource sizing reconciled with observed telemetry volume and target retention; explicit capacity alerting enabled.
- Retention/privacy approved.
- Secure remote ingestion tested in staging.
- Central ARM64 and remote ARM64/AMD64 image, package and binary compatibility verified.
- Backup restoration demonstrated.
- Security/configuration checks pass and residual risks documented.
