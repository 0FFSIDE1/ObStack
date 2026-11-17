# Remote application onboarding

Each service has one registration file: `applications/<application>.yml`. Its schema is `applications/schema.json`. The registration is the onboarding inventory; central Prometheus file-SD outputs are generated and committed under `prometheus/file_sd/`.

## Add a service

1. Copy `applications/ensams.yml` and update the application name and verified service facts.
2. Keep `enabled: false` until the private network, target, TLS and access policies have been verified. Null fields are explicit blockers, not defaults. The central application scrape interval and timeout are fixed at 30 seconds and 10 seconds.
3. After route-overlap review, set `approved_wireguard_cidr` in `applications/policy.yml` to approved RFC1918 IPv4 or IPv6 unique-local space. This central policy is not configurable per application. Use a verified literal target inside that network in `WireGuard-IP:port` form; IPv6 uses `[address]:port`. Hostnames and public or special-use IPs are rejected without DNS lookup. Any enabled application requires the network policy, including a health-only registration.
4. Set the protected environment name, exact Ansible inventory host, and approved HTTPS liveness URL where supported. Never add credentials or private keys. The current registration contract does not support enabling remote logs or host monitoring; those flags and methods are schema-rejected until their agents and source paths are implemented.
5. Run `python3 scripts/validate_applications.py` to validate schema and policy and deterministically rewrite the generated targets and missing-target alert rules. Review the diff.
6. Run `python3 scripts/validate_applications.py --check-generated` and the repository CI validators. CI rejects duplicate application names/targets, malformed fields, unapproved IPs, sensitive/high-cardinality labels, missing identity, external source claims as local files, and stale generated files.
7. Validate configured targets and probes from the intended path. Check scrape labels, `up`, `probe_success`, and application metric samples in staging. Logs and host/container monitoring cannot be enabled by this contract yet.
8. Update the integration readiness record with exact evidence and obtain a human review before production rollout.

## Registration behavior

- Enabled application metric targets are scraped at 30 seconds with a 10 second timeout from the registered metrics path and must be IP literals within the centrally approved private WireGuard CIDR.
- Enabled health targets are passed to Blackbox's `http_2xx` module; the registration URL must be HTTPS, use a literal private IP inside the approved WireGuard CIDR, and contain no credentials, query, or fragment. Hostname resolution is intentionally unsupported so CI validation stays deterministic.
- Generated metrics and probe series receive `application`, `environment`, and `host` labels. Registration labels are fixed identity values, not runtime dimensions. Application owners must separately inspect exported metric labels for IDs, emails, request data, or other high-cardinality values.
- ENSAMS `/up` is liveness only. Do not call it readiness or expose dependency diagnostics through it.
- Host/container telemetry uses the separate Alloy remote-write/log push path described in [remote telemetry architecture](remote-telemetry-architecture.md). Application scrape registration does not install an agent or make network/firewall changes.
- Dashboard and alert paths are source references only until files and actual metric names are checked. No automatic dashboard/rule copy is performed.

## CI and deployment boundary

CI validates the v2 JSON schema, every registration, policy CIDR, generated file drift, and the supported collection-method restrictions plus existing Prometheus, rule, Compose, Ansible and other repository configuration. CI does not grant production access or execute Ansible deployment. Mutating Ansible playbooks remain explicitly gated by `obstack_apply=true`; use the reviewed inventory and approved maintenance window. Configuration is eligible for deployment only after the network owner supplies verified values and the deployment reviewer approves.

## Application owner inputs

Before enabling an application, its owner and the network owner must provide the approved environment, exact inventory host, a verified WireGuard CIDR after overlap checks, a reserved host bind port, a literal WireGuard target address, the source IP actually observed by the application after Docker/NAT, an approved health URL and TLS policy, and reviewed metric names/labels. Central target validation does not authorize host firewall or application changes. Log collection and remote host monitoring remain unavailable in this registration contract; do not enable them by inventing a method name. Dashboard and alert paths in an application repository are reported as external references and are not treated as files imported into ObStack.

## Retirement lifecycle

Migration stages are `discovery`, `configured`, `validated_ci`, `verified_staging`, `verified_production`, `ready_for_human_review`, and `retired_local`. Advancing a value requires evidence. No script deletes local observability. The readiness checklist requires metrics, logs, dashboards, alerts, host/container data, healthy collectors, retention/recovery decisions, and no lost local-only capability. Retiring local services requires a separate reviewed change with rollback instructions.
