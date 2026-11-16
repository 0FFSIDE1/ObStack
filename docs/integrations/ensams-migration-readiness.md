# ENSAMS migration readiness

Assessment date: 2026-11-16. The central stack has no production ENSAMS telemetry evidence in this repository. Local ENSAMS observability must remain enabled.

| Capability | Status | Evidence / remaining gate |
| --- | --- | --- |
| ENSAMS application registration | CONFIGURED | `applications/ensams.yml` contains audit-confirmed paths/methods; disabled and unresolved network/environment values are null. |
| Registration schema and deterministic outputs | CONFIGURED | `applications/schema.json`, `scripts/validate_applications.py`; local tests and generated-target checks pass. The PR CI run has not yet occurred; active target files are empty until values are approved. |
| Central metrics scrape | NOT STARTED | No verified WireGuard target/port, Laravel-observed source, or successful scrape. |
| Public `/metrics` denial | REQUIRES HUMAN APPROVAL | ENSAMS audit states denial exists; verify deployed production Nginx after any app-side exposure change. |
| `/up` Blackbox probe | CONFIGURED | Probe job and target generation exist; URL and approved path/source/TLS policy are unresolved. No probe has run. |
| Remote application logs | NOT STARTED | Loki push endpoint exists. No approved remote Docker log source/privilege model and no observed ENSAMS records. |
| Remote host/container metrics | NOT STARTED | Alloy onboarding stages config only; no verified ENSAMS agent health, Docker/cAdvisor coverage or central samples. |
| ENSAMS dashboards | NOT STARTED | Source dashboards are referenced by audit but absent in this checkout; no central import/query validation. |
| ENSAMS queue/scheduler alerts | NOT STARTED | Need actual metric names and rule source; no central firing/routing evidence. |
| Alert delivery | REQUIRES HUMAN APPROVAL | Alertmanager defaults to sink without protected receiver. Must test firing and resolved delivery. |
| Retention and recovery | REQUIRES HUMAN APPROVAL | Measure rates/capacity and decide backup destination/RPO/RTO; run restore exercise. |
| Migration / local retirement | REQUIRES HUMAN APPROVAL | Must not proceed until all above are verified in production, local-only capabilities are accounted for, and rollback is approved. |

## Evidence required to advance

For each central scrape, probe, log, and agent path, retain timestamped query/result and target labels. For dashboards, attach screenshots or query results demonstrating non-empty ENSAMS data. For alerting, retain an approved test alert and firing/resolved delivery evidence. Record measured retention, disk headroom, backup/restore results, agent retry bounds, and architecture validation on both AMD64 and ARM64. These checks cannot be inferred from a passing syntax check.

## Rollback outline for a future migration

Keep ENSAMS local Prometheus, Grafana, Loki, Alloy, exporters and Alertmanager untouched during onboarding. If central collection fails, disable only the central registration/agent forwarding under an approved change; restore the pre-change remote agent configuration if needed. Once central collection is proven, any retirement must be a separate PR with a service-by-service revert plan and retention/history impact reviewed. Preserve application instrumentation and `/metrics` source code.
