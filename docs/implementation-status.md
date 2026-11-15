# ObStack implementation status

**Branch:** `codex/phase-1-discovery-architecture`  
**Status:** Initial configuration scaffold committed; validation and deployment remain pending.

## Implemented in repository

- ARM64-pinned central Compose services: Prometheus, Loki, Grafana, Alertmanager and Blackbox Exporter.
- Loopback-only host port bindings; no observability service is intentionally exposed to the public interface.
- Prometheus 30-day time retention with a 3 GB TSDB size cap.
- Loki 20-day retention configuration using local filesystem storage and TSDB schema v13.
- Grafana datasource provisioning and anonymous access/signup disabled.
- Conservative baseline alert rules and Blackbox probe modules.
- Secret-free `.env.example`.
- Ansible project defaults, example inventory, and a read-only Ubuntu 24.04 / architecture preflight playbook.

## Not yet implemented or validated

- WireGuard hub/peer roles and final overlay/VPC CIDR selection.
- Authenticated remote telemetry ingress over WireGuard; current central services bind only to loopback.
- Remote Alloy installation/configuration and host-specific collection policies.
- Nginx TLS, DNS, identity/RBAC design and certificate lifecycle.
- Notification receiver credentials and delivery tests.
- Dashboard set, application/database exporters and project inventory.
- Backup/restore, off-host storage, RPO/RTO and DR tests.
- ISO/IEC 27002:2022 evidence/control mapping and security review.
- CI validation against pinned image manifests and native ARM64 runtime.
- Capacity validation against actual ingestion volume.

## Safety and capacity

This repository work does not create AWS resources, associate the Elastic IP, install packages, create WireGuard keys, alter security groups, change firewall rules, or contact/configure the ten remote production servers.

The initial 2 vCPU / 2 GB RAM / 14 GB disk host is a constrained pilot target. Compose memory/CPU limits are provisional guardrails, not proof the full stack will fit. The Prometheus 3 GB TSDB cap and Loki retention period do not guarantee that the full requested retention is achievable; measure ingestion and disk growth before production use. Loki filesystem storage is single-node and not highly available.

The Compose file deliberately binds published ports to 127.0.0.1. Do not change these bindings to 0.0.0.0. A separately reviewed WireGuard-bound authenticated TLS ingress design is required before remote telemetry is enabled.
