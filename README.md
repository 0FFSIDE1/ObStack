# ObStack

Centralized observability for multiple projects and remote Linux servers.

## Current implementation

The initial repository implementation is on branch codex/phase-1-discovery-architecture.

- Central Docker Compose stack: Prometheus, Loki, Grafana, Alertmanager, Blackbox Exporter and Dockerized Nginx.
- Central images are pinned to ARM64 platform.
- Prometheus and Loki backend ports remain bound to loopback only.
- Prometheus remote-write receiver is enabled and exposed only through the Nginx authenticated HTTPS route /api/v1/write.
- Loki push is exposed only through the Nginx authenticated HTTPS route /loki/api/v1/push; Nginx assigns the single-node obstack tenant.
- Each enrolled host has separate metrics and logs Basic Auth credentials stored in Ansible Vault and bcrypt htpasswd files.
- TLS is terminated by Nginx using a central certificate signed by the private ObStack CA. A gated Ansible playbook distributes only the public CA certificate to spokes.
- Prometheus target retention is configured for 30 days with a 3 GB TSDB size cap; Loki retention is configured for 20 days.
- Grafana datasources are provisioned from files.
- Ansible includes read-only discovery, gated central provisioning, WireGuard hub/spoke provisioning, CA distribution and read-only central validation.

See docs/implementation-status.md, docs/architecture.md, docs/network-architecture.md, docs/telemetry-ingestion.md and docs/implementation-plan.md.

## Local configuration checks

On a compatible Docker host:

    cp .env.example .env
    # Edit .env and replace the placeholder with a unique long random password.
    docker compose config --quiet

The Compose stack is not a production deployment recipe yet. The current 2 vCPU / 2 GB RAM / 14 GB disk target is a constrained pilot; validate actual memory, CPU, disk growth and requested retention before production use.

## Safety boundaries

- Do not commit .env, private keys, preshared keys, tokens or passwords.
- Do not change published backend port bindings from 127.0.0.1 to 0.0.0.0.
- Nginx binds to loopback during bootstrap. After the WireGuard hub is configured and verified, bind Nginx to the hub's WireGuard IPv4 address; keep public TCP 443 closed.
- Do not enable remote Alloy forwarding until WireGuard, certificate distribution, authenticated routes and central validation have passed in the approved pilot.
- Repository changes and CI validation do not authorize AWS provisioning or production host changes.
