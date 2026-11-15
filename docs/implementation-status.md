# ObStack implementation status

**Branch:** codex/phase-1-discovery-architecture  
**Status:** Initial stack plus first-pass WireGuard and Alloy automation committed; validation and deployment pending.

## Implemented in repository

- ARM64-targeted central Compose services: Prometheus, Loki, Grafana, Alertmanager and Blackbox Exporter.
- Loopback-only host port bindings.
- Prometheus 30-day time retention with a 3 GB TSDB size cap; Loki 20-day retention.
- Grafana datasource provisioning, baseline alert rules and Blackbox modules.
- Secret-free environment and scalable Ansible inventory example.
- Read-only Ubuntu/architecture preflight.
- Read-only Docker/Alloy discovery across every host currently in the monitored inventory group, independent of fleet size.
- First-pass native WireGuard hub/spoke Ansible role and explicitly gated mutating playbook.
- Alloy onboarding role with preserve-by-default policy, HTTPS/TLS verification and password-file support. It stages config/secrets only and does not restart or replace existing containers.

## Dynamic fleet model

The project is not tied to ten servers. The rollout can begin with two, expand by batches of three or four, and continue beyond ten. Ansible peer generation iterates over inventory membership. The proposed 10.77.0.0/24 is only a provisional address example; final CIDR selection must account for future fleet growth and route overlap.

The central host is also scalable. The current 2 vCPU / 2 GB RAM / 14 GB disk host is a pilot constraint, not a permanent limit. Review CPU, memory, storage, ingestion rate, retention achieved and query latency before each onboarding batch; resize EC2/EBS or redesign storage as measurements require.

## Not yet implemented or validated

- Final VPC/overlay CIDR and authoritative inventory for the initial pilot hosts.
- WireGuard role syntax/runtime validation, firewall/security-group changes and pilot handshakes.
- Central authenticated TLS ingress and Prometheus remote-write receiver enablement.
- Host-specific Compose adoption for existing Alloy containers; config/secret/CA/host metric mounts.
- Actual log sources (Docker socket, journald or files) per server.
- Remote telemetry acceptance and authentication tests.
- DNS/certificate lifecycle, dashboards, exporters and alert notification endpoints.
- Backup/restore, off-host storage, RPO/RTO and DR tests.
- ISO/IEC 27002:2022 evidence mapping, security review, CI and native ARM64 runtime validation.
- Capacity validation against measured ingestion volume.

## Safety and capacity

Repository work has not created AWS resources, associated the Elastic IP, installed packages, generated production keys, changed security groups/firewalls, contacted or modified production servers, or restarted any containers.

The central 2 vCPU / 2 GB RAM / 14 GB disk host remains a constrained pilot target. Compose limits are provisional. Prometheus's 3 GB cap and Loki's 20-day retention do not guarantee requested retention. Measure ingestion and disk growth before expanding the fleet. Loki filesystem storage is single-node.

Prometheus, Loki, Grafana, Alertmanager and Blackbox ports remain bound to loopback. Do not expose them publicly. Remote Alloy must not be enabled until the WireGuard path and authenticated TLS ingress are implemented and tested.
