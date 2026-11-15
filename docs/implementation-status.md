# ObStack implementation status

**Branch:** codex/phase-1-discovery-architecture  
**Status:** Central stack, authenticated ingestion configuration, first-pass WireGuard/CA automation and validation playbooks are committed. CI and runtime validation are pending; nothing has been deployed.

## Implemented in repository

- ARM64-targeted central Compose services: Nginx reverse proxy, Prometheus, Loki, Grafana, Alertmanager and Blackbox Exporter.
- Backend services remain loopback-only. Nginx runs in Docker with TLS and proxies Grafana; bootstrap bind is loopback-only until WireGuard is verified.
- Prometheus 30-day time retention with a 3 GB TSDB size cap; Loki 20-day retention.
- Prometheus remote-write receiver enabled explicitly; Nginx exposes only the authenticated /api/v1/write route.
- Nginx exposes authenticated Loki /loki/api/v1/push and sets the configured single-node tenant header.
- Separate per-host metrics and logs Basic Auth credentials, stored in Ansible Vault and provisioned as bcrypt htpasswd entries; Nginx runs unprivileged and reads its TLS key and auth hashes through a dedicated host group; secrets are not committed.
- Grafana datasource provisioning plus a file-provisioned central platform overview dashboard (Prometheus scrape status, TSDB storage/series/ingestion, scrape duration, reload health and targets); conservative alert rules and Blackbox probe modules.
- Prometheus alert rules for missing scrape targets, failed config reloads, and warning/critical thresholds near the configured 3 GB TSDB storage cap.
- Optional HTTPS Alertmanager webhook delivery via OBSTACK_ALERTMANAGER_WEBHOOK_URL from the Ansible controller environment. The rendered configuration is group-readable only by the dedicated container group; CI validates sink and webhook configurations with amtool.
- Secret-free example environment and Ansible inventory.
- Read-only Ubuntu/architecture preflight and Docker/Alloy discovery that avoids container environment variables and secret values.
- First-pass native WireGuard hub/spoke Ansible role and explicitly gated mutating playbook; peer address/key uniqueness, keypair validation, actual hub-derived AllowedIPs and static peer egress validation added.
- Central UFW UDP 51820 ingress is scoped to the verified static public egress IPv4 for each enrolled spoke; AWS Security Group allowlisting remains a separate manual prerequisite.
- First-pass central-host Ansible workflow: Ubuntu 24.04 ARM64 checks, Africa/Lagos timezone, baseline security configuration, UFW/fail2ban/unattended upgrades, official Docker Engine/Compose installation, private CA and WireGuard-IP server certificate generation, Docker Compose deployment/startup and readiness checks.
- Gated public-CA distribution playbook; transfers only ca.crt, never private keys.
- Read-only central validation playbook for Compose services, readiness endpoints, Prometheus receiver flag, TLS trust and authenticated/unauthenticated ingress behavior.
- Alloy onboarding role with preserve-by-default policy, HTTPS/TLS verification and password-file support. It stages config/secrets only and does not restart or replace existing containers.
- GitHub Actions validation for Ansible syntax/lint, Compose rendering, Nginx syntax, Prometheus config/rules, Alertmanager config, Loki config, Blackbox Exporter config, Grafana provisioning YAML and dashboard JSON.
- Initial design-level threat model and preliminary scoped ISO/IEC 27002:2022 control/evidence mapping (explicitly Partial/Pending, not a compliance assertion).
- Operations guide documenting network diagram, ingress/host-local port inventory, Compose resource-ceiling sum and failure-mode responses.

## Not yet implemented or validated

- Final VPC/overlay CIDR, real host inventory, public keys, private keys and Ansible Vault secrets.
- Central provisioning playbook has not yet been run; controller collections, SSH source CIDR, repository path, certificate trust distribution and host-specific values must be supplied.
- WireGuard role syntax/runtime validation, firewall/security-group changes and pilot handshakes.
- CI workflow has not yet run against the latest changes; review any lint/config findings.
- CA trust distribution and central end-to-end validation have not been run against a deployed host.
- Nginx remains loopback-bound until WireGuard hub provisioning and verification; no public HTTPS exposure is intended.
- Host-specific Compose adoption for existing Alloy containers; config/secret/CA/host metric mounts.
- Actual log sources (Docker socket, journald or files) per server.
- Remote telemetry acceptance, payload delivery and authentication tests from AMD64 and ARM64 pilot hosts.
- DNS/certificate lifecycle automation, additional project/application dashboards, exporter deployment, and destination-specific alert routes. Generic webhook delivery is implemented but no actual endpoint has been provided; if unset, Alertmanager intentionally uses a sink.
- Backup/restore, off-host storage, RPO/RTO and DR tests.
- ISO/IEC 27002:2022 evidence mapping, security review and native ARM64 runtime validation.
- Host filesystem/free-space and service-level capacity alerts; current Prometheus TSDB block-cap alerts are implemented but do not indicate OS/disk free-space headroom.
- Capacity validation against measured ingestion volume.

## Safety and capacity

Repository work has not created AWS resources, associated the Elastic IP, installed packages, generated production keys/certificates on a host, changed security groups/firewalls, contacted or modified production servers, or restarted any containers. CI uses temporary test-only credentials and certificates.

The central 2 vCPU / 2 GB RAM / 14 GB disk host remains a constrained pilot target. Compose limits are provisional. Prometheus's 3 GB cap and Loki's 20-day retention do not guarantee requested retention; measure ingestion and disk growth. Loki filesystem storage is single-node.

Prometheus, Loki, Grafana, Alertmanager and Blackbox ports remain bound to loopback. Do not expose them publicly. Remote Alloy must not be enabled until the WireGuard path, public CA distribution, authenticated TLS ingress and pilot delivery tests are implemented and passed.
