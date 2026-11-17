# Remote application onboarding

Each service has one registration file: `applications/<application>.yml`. Its schema is `applications/schema.json`. The registration is the onboarding inventory; central Prometheus file-SD outputs are generated and committed under `prometheus/file_sd/`.

## Add a service

1. Copy `applications/ensams.yml` and update the application name and verified service facts.
2. Keep `enabled: false` until the private network, target, TLS and access policies have been verified. Null fields are explicit blockers, not defaults. The centrally managed application scrape interval and timeout are fixed at 30 seconds and 10 seconds.
3. Set the protected environment name, exact Ansible inventory host, metrics target `WireGuard-address:port`, approved HTTPS liveness URL, and stable `service`, `environment`, and `host` log labels. Never add credentials or private keys.
4. Run `python3 scripts/validate_applications.py` to validate schema and policy and deterministically rewrite the generated file-SD targets. Review the diff.
5. Run `python3 scripts/validate_applications.py --check-generated` and the repository CI validators. CI rejects duplicate application names/targets, malformed fields, sensitive/high-cardinality labels, missing required identity, and stale generated files.
6. Validate the target and probe from the intended central WireGuard path. Check scrape labels, `up`, `probe_success`, application metric samples, Loki JSON records, dashboard queries, agent health, and firing/resolved notification delivery in staging.
7. Update the integration readiness record with the exact evidence and obtain a human review before production rollout.

## Registration behavior

- Enabled application metric targets are scraped at 30 seconds with a 10 second timeout from `/metrics`.
- Enabled health targets are passed to Blackbox's `http_2xx` module; the registration URL must be HTTPS and cannot contain credentials.
- Generated metrics and probe series receive `service`, `environment`, and `host` labels. Do not put user, asset, request, URL/path, or other unbounded values into labels.
- ENSAMS `/up` is liveness only. Do not call it readiness or expose dependency diagnostics through it.
- Host/container telemetry uses the separate Alloy remote-write/log push path described in [remote telemetry architecture](remote-telemetry-architecture.md). Application scrape registration does not install an agent or make network/firewall changes.
- Dashboard and alert paths are source references only until files and actual metric names are checked. No automatic dashboard/rule copy is performed.

## CI and deployment boundary

CI validates registration structure and generated files plus the existing Prometheus, rule, Compose, Ansible and other repository configuration. CI does not grant production access or execute Ansible deployment. Mutating Ansible playbooks remain explicitly gated by `obstack_apply=true`; use the reviewed inventory and approved maintenance window. Configuration is eligible for deployment only after the network owner supplies verified values and the deployment reviewer approves.

## Retirement lifecycle

Migration stages are `discovery`, `configured`, `validated_ci`, `verified_staging`, `verified_production`, `ready_for_human_review`, and `retired_local`. Advancing a value requires evidence. No script deletes local observability. The readiness checklist requires metrics, logs, dashboards, alerts, host/container data, healthy collectors, retention/recovery decisions, and no lost local-only capability. Retiring local services requires a separate reviewed change with rollback instructions.
