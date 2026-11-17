# ENSAMS migration readiness

Assessment date: 2026-11-16. ENSAMS remains disabled. Local Prometheus, Grafana, Loki, Alloy, Alertmanager, node-exporter, cAdvisor, PHP-FPM exporter and Nginx exporter must remain in place until central telemetry is proven and local retirement is separately approved.

PR #25 was inspected at head `5da01da6aa785682bcbaed1aa675f9d3e732313e`. Its required `Validate configuration` run 297 and `Ansible validation` run 159 both passed. Those are CI configuration results, not live infrastructure evidence. This separate hardening branch must pass its own checks before merge.

| Migration gate | Status | Evidence / remaining work |
| --- | --- | --- |
| Registration schema validated | CONFIGURED | Schema v2 and validator enforce conditional feature requirements. Current hardening branch tests are pending CI. |
| Registration values supplied | NOT STARTED | ENSAMS environment, inventory hostname, WireGuard target and health URL remain null. |
| Approved WireGuard CIDR | REQUIRES HUMAN APPROVAL | `applications/policy.yml` is intentionally null. Network owner must complete overlap review and approve the CIDR. |
| Configuration generated | CONFIGURED | Empty file-SD targets and generated alert rules are deterministic. No target is generated while ENSAMS is disabled. |
| Central scrape configured | NOT STARTED | No verified address/port or application host bind; public metrics route must remain denied. |
| Central scrape verified | NOT STARTED | Requires authorized WireGuard scrape and observed Laravel source after Docker/NAT. |
| Health probe configured | NOT STARTED | Blackbox generation exists; ENSAMS health URL/TLS policy are not supplied. `/up` is liveness only. |
| Health probe verified | NOT STARTED | No central live probe evidence. |
| Remote logs configured | NOT STARTED | `logs.enabled` is schema-forced false and the only accepted method is `none`. No safe source path has been approved. |
| Remote logs verified | NOT STARTED | No central ENSAMS records or outage/backpressure evidence. |
| Remote host/container monitoring configured | NOT STARTED | Registration blocks enablement until an agent deployment/lifecycle, source scoping and health reporting exist. |
| Remote host/container monitoring verified | NOT STARTED | No central host, container, Docker daemon or Alloy health samples. |
| Dashboards imported | NOT STARTED | The two dashboard paths are explicitly external ENSAMS source references and absent in this ObStack checkout. |
| Dashboards verified | NOT STARTED | Datasource UIDs, PromQL/LogQL, metric names and labels have not been checked against central samples. |
| Application alerts configured | NOT STARTED | Generic scrape/probe and generated target-disappearance rules exist. ENSAMS queue/scheduler rules are not imported because source and actual metric names are unavailable here. |
| Application alerts verified | NOT STARTED | No central firing data or application metric samples. |
| Notification delivery verified | REQUIRES HUMAN APPROVAL | Alertmanager defaults to a sink without an approved protected receiver. Firing and resolved delivery must be tested. |
| Application owner approval received | REQUIRES HUMAN APPROVAL | Confirm metrics exposure, privacy/labels, health semantics and operational ownership. |
| Local monitoring retirement approved | REQUIRES HUMAN APPROVAL | Separate change only after all central paths, retention/recovery and no-loss checks are evidenced. |

## Values the application and network owners must supply

- Approved WireGuard CIDR after VPC, Docker bridge, host and operator route overlap checks.
- ENSAMS WireGuard peer address, approved inventory hostname, reserved host port, and host bind interface.
- Effective source IP that Laravel sees through the Docker/Nginx/NAT path and the narrow application/Nginx allowlists.
- Protected `APP_ENV`, approved HTTPS `/up` URL and TLS policy.
- A reviewed remote log source and privilege boundary. Docker socket access is root-equivalent even when mounted read-only.
- Source dashboard and alert-rule files or an approved repository reference, plus confirmed metric names/labels.
- Central alert receiver, retention/capacity decision, backup destination, RPO/RTO and restore evidence.

## Retirement safety

No registration status advances itself based on syntax checks. Production readiness requires evidence for scrape, probe, logs, host/container data, dashboards, alert rules and routed notifications, plus healthy agents and understood retention/recovery. Preserve local observability throughout. Disable only the central integration to roll back a failed pilot; restore any separately changed agent config from its recorded backup. Removing local services requires a distinct reviewed PR and explicit owner approval. Preserve ENSAMS application instrumentation and `/metrics` source code.
