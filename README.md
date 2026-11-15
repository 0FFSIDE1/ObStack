# ObStack

Centralized observability for multiple projects and remote Linux servers.

## Current implementation

The initial repository implementation is on branch `codex/phase-1-discovery-architecture`.

- Central Docker Compose stack: Prometheus, Loki, Grafana, Alertmanager and Blackbox Exporter.
- Central images are pinned to ARM64 platform.
- Published service ports bind to loopback only.
- Prometheus target retention is configured for 30 days with a 3 GB TSDB size cap.
- Loki retention is configured for 20 days.
- Grafana datasources are provisioned from files.
- Ansible includes read-only discovery plus an explicitly gated central-host provisioning workflow (security baseline, Docker, private PKI certificate generation, Compose deployment and readiness checks).

See [implementation status](docs/implementation-status.md), [architecture](docs/architecture.md), [network design](docs/network-architecture.md), and [implementation plan](docs/implementation-plan.md).

## Local configuration checks

On a compatible Docker host:

```bash
cp .env.example .env
# Edit .env and replace the placeholder with a unique long random password.
docker compose config --quiet
```

The compose stack is not a production deployment recipe yet. The current 2 vCPU / 2 GB RAM / 14 GB disk target is a constrained pilot; validate actual memory, CPU, disk growth and requested retention before production use.

## Safety boundaries

- Do not commit `.env`, private keys, preshared keys, tokens or passwords.
- Do not change published port bindings from `127.0.0.1` to `0.0.0.0`.
- Remote telemetry ingestion is intentionally not enabled until the WireGuard and authenticated TLS ingress design is implemented and reviewed.
- No AWS resources or remote production servers are changed by repository configuration work.
