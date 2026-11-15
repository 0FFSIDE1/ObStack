# ObStack — Phased Implementation Plan

**Status:** Draft pending environment discovery and architecture approval. This plan is not evidence of completed implementation or tests.

## Phase 1 — Discovery and architecture

- [x] Inspect linked GitHub repository `0FFSIDE1/ObStack` on default branch `main`.
- [x] Record current repository baseline and gaps.
- [x] Draft logical architecture, telemetry flows, trust boundaries, label contract, assumptions and decision list in `docs/architecture.md`.
- [x] Record user-provided initial central resources (AWS EC2 2 vCPU / 2 GB RAM / 14 GB disk, fixed for now but potentially expandable) and retention goals (30 days metrics / 20 days logs); actual host state and capacity validation remain pending.
- [x] Record user-confirmed central OS as Ubuntu 24.04 LTS; host state remains unverified.
- [x] Record initial monitoring scope as approximately 5–10 projects; project names, environments, host counts, and workload inventory remain pending.
- [ ] Confirm remote OS, networking, TLS/DNS, secrets, backups, projects and data-volume expectations.
- [ ] Review and approve architecture.

## Phase 2 — Implementation plan and safe boundaries

- [x] Define phases, dependencies and validation gates in this document.
- [ ] Confirm staging environment and production-change authorization boundary.
- [ ] Choose exact supported upstream image versions and record upgrade strategy after compatibility/security review.

## Phase 3 — Central platform

- [ ] Compose stack: Prometheus, Grafana, Loki, Alertmanager, Blackbox Exporter, Nginx; constrain scope/resources for the initial small host.
- [ ] Persistent volumes, dedicated networks, health checks, resource controls and hardening.
- [ ] Prometheus scrape/remote-write receiver config and rule groups; configure 30-day metrics retention and validate TSDB growth.
- [ ] Loki auth, retention/compaction and storage limits; configure 20-day log retention and measure actual daily ingest/index footprint.
- [ ] Establish host/disk/service capacity alerting, safe free-space headroom, and explicit scale-up/degradation runbook. Requested retention is a target, not guaranteed until telemetry volume is measured.
- [ ] Grafana datasources, global/project dashboard provisioning and RBAC.
- [ ] Nginx TLS/auth/access restrictions and certificate lifecycle.
- [ ] Configuration validation using official tooling.

## Phase 4 — Remote agent and exporter patterns

- [ ] Alloy metrics/log pipelines with authenticated TLS forwarding and retries/buffering appropriate to supported components.
- [ ] Node Exporter and cAdvisor with documented host mounts and least privilege.
- [ ] Optional PostgreSQL/MySQL/Redis/Nginx/process exporters only for applicable workloads.
- [ ] Application instrumentation examples for FastAPI, Laravel, Nginx, PostgreSQL and Redis.
- [ ] Label normalization, sensitive-log filtering/redaction, and cardinality policy tests.

## Phase 5 — Ansible automation

- [ ] Inventory, group/host vars, common/security/Docker/observability/Nginx/firewall/backup/validation roles.
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
