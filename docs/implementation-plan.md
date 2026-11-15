# ObStack — Phased Implementation Plan

**Status:** Implementation work in progress; architecture decisions and production prerequisites remain subject to explicit approval. This plan is not evidence of a completed deployment or successful runtime tests.

## Phase 1 — Discovery and architecture

- [x] Inspect linked GitHub repository 0FFSIDE1/ObStack on default branch main.
- [x] Record current repository baseline and gaps.
- [x] Draft logical architecture, telemetry flows, trust boundaries, label contract, assumptions and decision list in docs/architecture.md.
- [x] Record central resources (AWS EC2 2 vCPU / 2 GB RAM / 14 GB disk), Ubuntu 24.04 LTS ARM64 and requested retention (30 days metrics / 20 days logs); actual host state and capacity validation remain pending.
- [x] Record remote fleet as Ubuntu 24.04 LTS with AMD64 and ARM64 hosts; per-host mapping remains pending.
- [x] Record selected self-managed WireGuard, non-commercial workload and hub-and-spoke topology; no VPN has been installed and no production hosts have been changed.
- [ ] Confirm VPC CIDR/subnets and verify no overlap with office/home/existing VPN and remote Docker bridge routes.
- [ ] Collect current pilot host inventory, project/environment mapping, static public IPs, SSH access and existing Alloy ownership.
- [ ] Review and approve architecture and production-change boundary.

## Phase 2 — Implementation plan and safe boundaries

- [x] Define phases, dependencies and validation gates.
- [x] Document WireGuard hub-and-spoke topology, provisional address plan, peer isolation, NAT keepalive, firewall/security-group requirements, secrets handling and failure modes.
- [x] Record that the existing Elastic IP is available but not associated with an EC2 instance; verify allocation, region and ownership during AWS provisioning.
- [x] Record remote servers have static public IPv4 addresses; collect and verify literal addresses before narrowing UDP ingress allowlists.
- [ ] Approve final VPC CIDR and WireGuard overlay after route-overlap checks; the proposed 10.77.0.0/24 remains provisional.
- [ ] Confirm AWS Security Group ownership, UDP 51820 ingress policy and remote egress policy.
- [ ] Define peer key generation, secure distribution, storage, rotation and revocation; private keys must never enter Git.
- [ ] Choose exact supported upstream image versions and record upgrade strategy after compatibility/security review.

## Phase 3 — Central platform

- [x] Compose stack: Nginx reverse proxy, Prometheus, Grafana, Loki, Alertmanager and Blackbox Exporter; constrain scope/resources for the initial small ARM64 host.
- [x] Persistent volumes, dedicated network, health checks and conservative resource controls.
- [x] Prometheus remote-write receiver enabled explicitly; 30-day time retention and 3 GB TSDB cap configured, with actual retention subject to measured capacity.
- [x] Loki authentication enabled, 20-day retention/compaction configured, and single-node obstack tenant assigned by the authenticated Nginx route.
- [x] Nginx TLS routes for Prometheus remote-write and Loki push with separate per-host Basic Auth files; Grafana remains behind the same TLS proxy.
- [x] Per-host bcrypt htpasswd provisioning from Ansible Vault; backend service ports remain loopback-only.
- [x] Add Prometheus TSDB storage-cap warning/critical alert thresholds against the configured 3 GB cap.
- [ ] Establish host filesystem/free-space and service capacity alerting, safe free-space headroom and scale-up/degradation runbook; this requires host-level metrics and measured pilot baselines.
- [x] Provision a version-controlled central platform overview dashboard from Grafana files.
- [ ] Grafana RBAC, project dashboards and application-specific observability.

## Phase 4 — Remote agent and exporter patterns

- [x] Alloy metrics/log endpoints use HTTPS, per-host Basic Auth and CA verification; credentials are staged as password files, not embedded in Alloy config.
- [x] Alloy endpoint defaults use the central WireGuard IP and the matching private-CA certificate trust path.
- [ ] Complete host-specific Compose adoption for existing Alloy containers, including read-only CA and password-file mounts.
- [ ] Select actual log sources (Docker socket, journald or files) per server after read-only discovery.
- [ ] Node Exporter/cAdvisor and optional application/database exporters with architecture checks for AMD64 and ARM64.
- [ ] Label normalization, sensitive-log filtering/redaction and cardinality policy tests.
- [ ] Run representative AMD64 and ARM64 staging onboarding and integration tests before fleet rollout.

## Phase 5 — Ansible automation

- [x] Central inventory variable example, controller collection requirements and first-pass common/security/Docker/certificate/central-stack roles.
- [x] Central deployment playbook for Ubuntu 24.04 ARM64, Africa/Lagos timezone, security baseline, Docker, private CA/server certificate, Docker Nginx TLS reverse proxy, Compose startup and service readiness checks; execution remains pending.
- [x] WireGuard hub/spoke role with inventory/key/address validation, unique peer /32 enforcement and explicit obstack_apply=true gate.
- [x] Gated public CA distribution playbook; transfers only the CA certificate, never private keys.
- [x] Read-only central validation playbook for Compose, service health, Prometheus receiver flag, TLS and endpoint authentication.
- [x] GitHub Actions workflow for Ansible syntax, Ansible Lint, Compose rendering and Nginx syntax validation.
- [ ] Obtain successful CI run and review all validation findings.
- [ ] Complete peer rotation/revocation and host-specific Alloy container adoption procedures.

## Phase 6 — Alerting

- [x] Baseline platform alerts for scrape-target down, Prometheus config reload failure and TSDB storage-cap thresholds.
- [ ] Reusable infrastructure, Docker, application, database, telemetry, security/operations and backup alert rules; host/application metric sources and thresholds are not yet established.
- [x] Alertmanager grouping by alert name, project, environment and server; severity inhibition for critical over warning is configured.
- [x] Add an optional HTTPS webhook receiver controlled by OBSTACK_ALERTMANAGER_WEBHOOK_URL from the Ansible controller environment; render its configuration to a protected file and validate both sink and webhook modes in CI.
- [ ] Complete destination-specific routing/templates (for example Telegram, SMTP, Slack) and set an approved actual endpoint. With the variable unset, the default receiver intentionally remains a non-delivery sink.
- [ ] Firing/resolved delivery tests; thresholds documented and configurable.

## Phase 7 — Security and compliance

- [x] Add initial design-level threat model with assets, trust boundaries, threat scenarios, current controls and staging acceptance gates.
- [ ] Approve organizational secrets policy, complete network/hardening review, CIS assessment and vulnerability scanning; deployed controls and runtime evidence are not yet verified.
- [x] Create a preliminary scoped ISO/IEC 27002:2022 mapping with control objective paraphrases, repository evidence, verification methods, partial/pending status and responsibility gaps.
- [ ] Confirm applicability and owners and gather current organizational/runtime evidence; this preliminary map is not a compliance assertion.
- [ ] Privacy/logging review and retention/deletion policy.
- [ ] Review the single Loki tenant model before multi-project/customer isolation requirements are introduced.

## Phase 8 — Testing and evidence

- [x] Add CI checks for Ansible syntax/lint, Compose rendering and Nginx configuration syntax.
- [x] Add Prometheus config/rule, Alertmanager, Loki, Blackbox Exporter, Grafana provisioning YAML and dashboard JSON checks to the configuration workflow.
- [x] Add read-only central runtime validation for service readiness, TLS trust, Prometheus receiver and unauthenticated/authenticated route behavior.
- [ ] Run CI and capture actual results; do not infer success from workflow configuration.
- [ ] Integration checks: metrics/logs/query paths, labels, alert routes, persistent data, backup restore.
- [ ] WireGuard tests: enrolled peers connect; unique routes; no overlap; reboot/NAT reconnect; UDP reachability; unauthorized peer rejection; key revocation; telemetry endpoints inaccessible from public interfaces.
- [ ] Architecture matrix checks: central ARM64 and remote ARM64/AMD64 image manifests, checksums, package availability and successful agent startup.
- [ ] Security checks: exposed ports, credentials, TLS verification, privileges/mounts, access controls, image vulnerabilities and log leakage.
- [ ] Controlled staging failure simulation and recovery tests.
- [ ] Produce evidence-based test report with actual command output and pass/fail statuses.

## Phase 9 — Documentation and operations

- [x] Document authenticated telemetry paths, credential model, CA distribution, WireGuard routing policy and rollout sequence in docs/telemetry-ingestion.md.
- [ ] Document certificate renewal/rotation, peer revocation, backup recovery, RPO/RTO and DR procedures.
- [x] Document the initial Compose resource ceilings, required ports and ingress policy, logical network diagram and failure-mode guide in docs/operations/ports-capacity-failure-modes.md.
- [ ] RPO/RTO and backup retention approved and restoration rehearsed.

## Phase 10 — Final review and readiness

- [ ] Senior SRE review of reliability, security, alert coverage, capacity, recovery, maintainability and compliance evidence.
- [ ] Resolve safely actionable findings and report residual risks.
- [ ] Production readiness decision only after all critical validation gates pass and required external dependencies are verified.

## Current rollout and safety constraints

The initial rollout should begin with two pilot servers (one AMD64 and one ARM64 where practical), then expand in batches of three or four. The inventory and peer generation are fleet-size agnostic. The central 2 vCPU / 2 GB RAM / 14 GB disk host is a constrained pilot starting point, not a permanent ceiling. Retention goals are not guaranteed until measured ingestion and disk growth support them.

No AWS resource creation, Elastic IP association, security-group mutation, production host change, package installation, WireGuard key generation, CA private-key creation or container restart is authorized by repository work. Mutating Ansible playbooks require obstack_apply=true and separate explicit production approval.
