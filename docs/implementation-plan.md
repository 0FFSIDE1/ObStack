# ObStack — Phased Implementation Plan

**Status:** Draft pending environment discovery and architecture approval. This plan is not evidence of completed implementation or tests.

## Phase 1 — Discovery and architecture

- [x] Inspect linked GitHub repository `0FFSIDE1/ObStack` on default branch `main`.
- [x] Record current repository baseline and gaps.
- [x] Draft logical architecture, telemetry flows, trust boundaries, label contract, assumptions and decision list in `docs/architecture.md`.
- [x] Record user-provided initial central resources (AWS EC2 2 vCPU / 2 GB RAM / 14 GB disk, fixed for now but potentially expandable) and retention goals (30 days metrics / 20 days logs); actual host state and capacity validation remain pending.
- [x] Record user-confirmed central OS as Ubuntu 24.04 LTS; host state remains unverified.
- [x] Record central EC2 architecture as ARM64 / AWS Graviton (user-confirmed; verify actual instance type and host architecture before installation).
- [x] Record initial monitoring scope as approximately 5–10 projects and 6 remote servers; project names, project-to-server mapping, environments, and workload inventory remain pending.
- [x] Record all six remote servers as Ubuntu 24.04 LTS on a mixed ARM64 (`arm64`) and AMD64 (`amd64`) fleet; per-host architecture mapping remains pending.
- [ ] Confirm remote OS, networking, TLS/DNS, secrets, backups, projects and data-volume expectations.
- [ ] Review and approve architecture.

## Phase 2 — Implementation plan and safe boundaries

- [x] Define phases, dependencies and validation gates in this document.
- [x] Define architecture requirements: central stack images must support `linux/arm64`; remote agent/exporter artifacts must support both `linux/arm64` and `linux/amd64`, select architecture-specific binaries safely, and validate all required architectures before fleet rollout.
- [ ] Confirm staging environment and production-change authorization boundary.
- [ ] Choose exact supported upstream image versions and record upgrade strategy after compatibility/security review; verify multi-platform manifests and pin immutable digests where possible.

## Phase 3 — Central platform

- [ ] Compose stack: Prometheus, Grafana, Loki, Alertmanager, Blackbox Exporter, Nginx; constrain scope/resources for the initial small ARM64 host.
- [ ] Persistent volumes, dedicated networks, health checks, resource controls and hardening.
- [ ] Prometheus scrape/remote-write receiver config and rule groups; configure 30-day metrics retention and validate TSDB growth.
- [ ] Loki auth, retention/compaction and storage limits; configure 20-day log retention and measure actual daily ingest/index footprint.
- [ ] Establish host/disk/service capacity alerting, safe free-space headroom, and explicit scale-up/degradation runbook. Requested retention is a target, not guaranteed until telemetry volume is measured.
- [ ] Grafana datasources, global/project dashboard provisioning and RBAC.
- [ ] Nginx TLS/auth/access restrictions and certificate lifecycle.
- [ ] Configuration validation using official tooling; confirm every central image has a linux/arm64 manifest.

## Phase 4 — Remote agent and exporter patterns

- [ ] Alloy metrics/log pipelines with authenticated TLS forwarding and retries/buffering appropriate to supported components; verify agent release support on ARM64 and AMD64.
- [ ] Node Exporter and cAdvisor with documented host mounts and least privilege; validate binaries/images for both architectures.
- [ ] Optional PostgreSQL/MySQL/Redis/Nginx/process exporters only for applicable workloads; confirm each selected exporter supports each deployed architecture.
- [ ] Application instrumentation examples for FastAPI, Laravel, Nginx, PostgreSQL and Redis.
- [ ] Label normalization, sensitive-log filtering/redaction, and cardinality policy tests.
- [ ] Run representative ARM64 and AMD64 staging onboarding and integration tests before fleet-wide rollout.

## Phase 5 — Ansible automation

- [ ] Inventory, group/host vars, common/security/Docker/observability/Nginx/firewall/backup/validation roles.
- [ ] Inventory architecture facts and normalized architecture variables; fail safely on unsupported architectures rather than downloading the wrong binary. Enforce ARM64-compatible artifacts for central deployment.
- [ ] Central deployment, remote onboarding/update, exporter enablement, validation and agent removal playbooks.
- [ ] Idempotency/syntax/lint checks; avoid unnecessary application config changes.

## Phase 6 — Alerting

- [ ] Reusable infrastructure, Docker, application, database, telemetry, security/operations and backup alert rules.
- [ ] Alertmanager grouping, severity/project/environment/service routing, inhibition, templates, and configurable Telegram/SMTP/Slack/webhook receivers.
- [ ] Firing/resolved delivery tests; thresholds documented and configurable.

## Phase 7 — Security and compliance

- [ ] Threat model, secrets policy, network assessment, hardening review, CIS assessment and vulnerability scanning.
- [ ] ISO/IEC 27002:2022 control mapping with objective, evidence, verification, status, gaps and organizational responsibilities.
- [ ] Privacy/logging review and retention/deletion policy.

## Phase 8 — Testing and evidence

- [ ] Compose, Prometheus, rules, Alertmanager, Loki, Alloy, Nginx, Grafana provisioning and Ansible validation.
- [ ] Integration checks: metrics/logs/query paths, labels, alert routes, persistent data, backup restore.
- [ ] Architecture matrix checks: verify central ARM64 and remote ARM64/AMD64 image manifests, checksums, package availability and successful agent startup on all required architectures.
- [ ] Security checks: exposed ports, credentials, TLS verification, privileges/mounts, access controls, image vulnerabilities and log leakage.
- [ ] Controlled staging failure simulation and recovery tests.
- [ ] Produce evidence-based test report with actual command output and pass/fail statuses; no fabricated results.

## Phase 9 — Documentation and operations

- [ ] Install/deploy/upgrade/rollback, onboarding/removal, alerting, dashboards, operations, troubleshooting, backup recovery and DR documentation.
- [ ] Resource sizing and required ports, network diagram and failure-mode guidance.
- [ ] RPO/RTO and backup retention approved and restoration rehearsed.

## Phase 10 — Final review and readiness

- [ ] Senior SRE review of reliability, security, alert coverage, capacity, recovery, maintainability and compliance evidence.
- [ ] Resolve safely actionable findings and report residual risks.
- [ ] Production readiness decision only after all critical validation gates pass and required external dependencies are verified.

## Rollback approach

- Keep changes isolated on a feature branch and review via pull request.
- For config changes, retain previous versioned configs and revert the branch/commit if validation or staging tests fail.
- For central deployment, use a maintenance window, backup configuration and state before upgrades, validate the previous image/config versions are recoverable, and avoid destructive volume removal.
- Remote onboarding/removal must be inventory-scoped and reviewed; no broad host targeting. Removal should disable telemetry and remove only observability-managed resources.
- No production deployment or destructive operation is authorized by this plan.
