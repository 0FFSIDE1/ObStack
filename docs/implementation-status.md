# ObStack implementation status

**Branch:** codex/phase-1-discovery-architecture  
**Status:** Initial stack plus first-pass central provisioning, WireGuard and Alloy automation committed; validation and deployment remain pending.

## Implemented in repository

- ARM64-pinned central Compose services: Nginx reverse proxy, Prometheus, Loki, Grafana, Alertmanager and Blackbox Exporter.
- Backend services remain loopback-only. Nginx runs in Docker with TLS and proxies Grafana; bootstrap bind is loopback-only pending WireGuard hub readiness.
- Prometheus 30-day time retention with a 3 GB TSDB size cap; Loki 20-day retention.
- Grafana datasource provisioning, conservative alert rules and Blackbox probe modules.
- Secret-free example environment and Ansible inventory.
- Read-only Ubuntu/architecture preflight.
- Read-only Docker/Alloy discovery that avoids container environment variables and secret values.
- First-pass native WireGuard hub/spoke Ansible role and explicitly gated mutating playbook.
- First-pass central-host Ansible workflow: Ubuntu 24.04 ARM64 checks, Africa/Lagos timezone, baseline security configuration, UFW/fail2ban/unattended upgrades, official Docker Engine/Compose installation, private CA and WireGuard-IP server certificate generation, Docker Compose deployment/startup and readiness checks for Nginx and all observability services. Requires Vault credentials and explicit `obstack_apply=true`.
- GitHub Actions workflow for Ansible syntax checks, Ansible Lint and Compose configuration validation.
- Alloy onboarding role with preserve-by-default policy, HTTPS/TLS verification and password-file support. It stages config/secrets only and does not restart or replace existing containers.

## Not yet implemented or validated

- Final VPC/overlay CIDR, real host inventory, public keys and Ansible Vault secrets.
- Central provisioning playbook has not yet passed the newly added GitHub Actions checks or been run; controller collections, SSH source CIDR, repository path, certificate trust distribution and host-specific values must be supplied.
- Generated central TLS certificate is staged for the planned private telemetry ingress; no reverse-proxy ingress is deployed or enabled yet.
- WireGuard role syntax/runtime validation, firewall/security-group changes and pilot handshakes.
- Nginx currently proxies Grafana only; authenticated Prometheus remote-write and Loki push routes, rate limits and endpoint-specific authorization remain to be implemented.
- Host-specific Compose adoption for existing Alloy containers; config/secret/CA/host metric mounts.
- Actual log sources (Docker socket, journald or files) per server.
- Remote telemetry acceptance and authentication tests.
- DNS/certificate lifecycle, dashboards, exporters, alert notification endpoints.
- Backup/restore, off-host storage, RPO/RTO and DR tests.
- ISO/IEC 27002:2022 evidence mapping, security review, CI and native ARM64 runtime validation.
- Capacity validation against measured ingestion volume.

## Safety and capacity

Repository work has not created AWS resources, associated the Elastic IP, installed packages, generated production keys/certificates on a host, changed security groups/firewalls, contacted or modified production servers, or restarted any containers. The new Ansible workflow is code only and has not been executed.

The central 2 vCPU / 2 GB RAM / 14 GB disk host remains a constrained pilot target. Compose limits are provisional. Prometheus's 3 GB cap and Loki's 20-day retention do not guarantee requested retention; measure ingestion and disk growth. Loki filesystem storage is single-node.

Prometheus, Loki, Grafana, Alertmanager and Blackbox ports remain bound to loopback. Do not expose them publicly. Remote Alloy must not be enabled until the WireGuard path and authenticated TLS ingress are implemented and tested.
