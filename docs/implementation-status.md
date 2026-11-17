# Current implementation and project status

**Status snapshot:** 2026-11-17. This describes committed repository configuration and GitHub history. It is not evidence of a deployed or runtime-verified observability service.

## Repository and release state

- The default `main` branch is at `c251af6` (`Promote main to release v0.0.1`, PR #28).
- The `release` branch is at `5cd4661` (`docs(release): prepare v0.0.2 notes`, PR #30). It includes the promotion from `main` in PR #29 and the trailing-whitespace correction in PR #31.
- PRs #25 and #26 integrated remote application onboarding and its hardening into `main`. PR #27 was closed without merging after its conflict was resolved through PR #29.
- `release-notes/v0.0.2.md` is pending release metadata. The repository currently has no version tags or published GitHub Releases. No tagged deployment has run.
- No AWS VPC/EC2 hub or remote host has been provisioned by this repository work. The available Elastic IP is not associated with a hub; the proposed `10.77.0.0/24` overlay remains unapproved.

### Recent CI evidence

These workflow runs passed on their respective pull-request commits:

| Change | Commit | Validate configuration | Ansible validation |
| --- | --- | --- | --- |
| Main-to-release promotion, PR #29 | `f5f532d` | #304 passed | #165 passed |
| Pending v0.0.2 notes, PR #30 | `724e74c` | #309 passed | #169 passed |
| Release whitespace correction, PR #31 | `1e6f34a` | #307 passed | #168 passed |

These results establish repository checks only. They do not show that AWS, central services, WireGuard peers, remote collectors, dashboards, or notifications are running.

## Implemented in the repository

- A Docker Compose observability stack with Prometheus, Loki, Grafana, Alertmanager, Blackbox Exporter, and Dockerized Nginx. Images and service limits are configured for the intended small ARM64 pilot.
- Authenticated HTTPS ingestion routes for Prometheus remote-write and Loki push, per-host credential provisioning, a private CA, public-CA distribution, and automated central leaf-certificate renewal configuration.
- Ansible roles and gated playbooks for central host setup, host security, WireGuard, CIDR discovery, CA distribution, Alloy discovery/onboarding, and read-only central validation. Mutating plays require `obstack_apply=true`.
- A declarative application registration schema and validator. Metrics and health targets must be literal private addresses inside the centrally configured WireGuard CIDR. Registrations generate deterministic Prometheus file-SD and target-disappearance alerts. ENSAMS remains disabled; the central CIDR and approved inventory hosts remain unset.
- Generic application scrape/probe alerts, platform alerts, one provisioned Grafana overview dashboard, and optional HTTPS Alertmanager webhook configuration. The default Alertmanager receiver is a sink, so it sends no notifications until a destination is configured and tested.
- CI for Python validation, registrations and generated-file drift, secret scanning, Compose, Prometheus, Alertmanager, Blackbox, Loki, Grafana assets, Alloy syntax and architecture manifests, Ansible syntax/lint, and Nginx configuration.
- Release-note generation, pending metadata validation, exact `release`-HEAD tag checks, and a production deployment workflow gated by GitHub environments.

## Not deployed or not yet verified

- No VPC, EC2 hub, security group, production host, WireGuard peer, key, or application has been provisioned or changed through this work. The CIDR preflight workflow is read-only and requires real network inputs and credentials before it can run against infrastructure.
- No remote application registration is enabled. ENSAMS has no approved CIDR, target address, inventory hostname, environment, or health URL.
- The Alloy onboarding role stages configuration; it does not install or restart an agent. Remote logs and host monitoring remain disabled because there is no approved source/privilege model, bounded-buffer design, deployment lifecycle, or agent-health path.
- No live scrape, health probe, telemetry delivery, backup restore, failure recovery, alert notification, or AMD64/ARM64 remote pilot has been verified.
- ENSAMS dashboards and alert rules remain external references, not imported files. Application-specific queue/scheduler rules need actual metric names and samples.
- Requested retention (30 days of metrics and 20 days of logs) is configured, not capacity-proven. The intended 2 vCPU / 2 GB RAM / 14 GB disk hub is a constrained pilot target. Loki has no hard volume-size cap, and filesystem free-space alerting is not implemented.
- No published release tag or GitHub Release exists. The v0.0.2 notes are pending; production deployment, root changelog promotion, backup/restore, RPO/RTO, and DR evidence remain outstanding.

## Governance and CI follow-up

`.github/rulesets/branches-main-release.json` still names the required checks `config` and `Syntax, lint, Compose and Nginx validation`. Current workflow runs report `Validate configuration` and `Ansible validation`. The repository's effective GitHub ruleset state has not been independently confirmed here; align and verify required check contexts through the approval-gated governance workflow before relying on them for branch protection.

## Safety and capacity

Repository configuration and passing CI do not authorize production changes. Keep local application monitoring in place until central ingestion, dashboards, alerts, notification delivery, retention, and recovery have been verified with evidence and approved by the owners. See the [ENSAMS migration readiness record](integrations/ensams-migration-readiness.md), [network architecture](network-architecture.md), and [operations guide](operations/ports-capacity-failure-modes.md).
