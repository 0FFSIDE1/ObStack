# Remote telemetry architecture

## Existing central paths

Remote Alloy agents initiate outbound connections through WireGuard to the ObStack hub. `nginx/conf.d/obstack.conf` terminates TLS using the private ObStack CA and enforces per-host Basic Auth before forwarding Prometheus remote-write to Prometheus or Loki push to Loki. Prometheus and Loki host ports stay on loopback. TLS verification remains enabled. This avoids inbound exporter ports on public remote interfaces.

Application endpoints are a separate path: central Prometheus scrapes an application metrics endpoint over WireGuard, and Blackbox probes its approved health URL. These paths are generated from registrations into Prometheus file-SD. The scrape target must be bound only to the verified WireGuard interface on the application host and its application allowlists must match the source Laravel actually observes after Docker/NAT. Do not authorize forwarded headers. Keep public `/metrics` denial in place.

## Logs and host/container monitoring

The repository's Alloy onboarding role stages a starter config and preserves existing deployments by default. It does not install or restart Alloy. CI validates the rendered starter config and checks that its pinned image publishes AMD64 and ARM64 variants. That is syntax and image metadata validation, not proof of a running agent. The current role does not configure a log source, bounded buffer, container scope, or agent-health ingestion. The application schema therefore rejects enabled logs and host-monitoring capabilities; ENSAMS uses `method: none` with both features disabled.

| Option | Security and operations | Decision |
| --- | --- | --- |
| Per-host Alloy with Docker discovery/socket | Local collection and current Loki push path fit, but Docker API/socket access grants root-equivalent control even if the socket mount is read-only. It can see unrelated containers unless additional scoping is reliable. Agent package, service hardening, queue bounds, health, uninstall and socket privilege need explicit design. | Not approved; no Docker socket access and no Alloy log source enabled. |
| Journald collection | A native Alloy service can read journal entries with a constrained journal group, avoiding Docker API access. ENSAMS currently uses Docker `json-file`, so container logs will not be in journald unless its logging driver/application deployment changes. Persistence, retention and per-container scoping also need verification. | Candidate only if the application owner approves journald and confirms its log path. |
| Protected application log files/forwarder | A host agent can receive read-only access to a narrowly scoped file or local forwarding socket. ENSAMS currently emits structured stderr captured by Docker; no scoped file path or local forwarder is configured. Adding one requires application/host changes and bounded rotation/queue design. | Candidate after source and resource behavior are approved. |
| Central Alloy reading remote Docker socket | Exposes a privileged control API across hosts and contradicts the network trust boundary. | Rejected. Never expose Docker socket over TCP or mount it in central Alloy. |

No remote log method is selected yet. The application registration allows only `logs.enabled: false` and `method: none` until the source, least-privilege access, retries/backpressure, bounded local storage, container scoping, JSON preservation, health checks, and rollback procedure are reviewed and implemented. This is an explicit pending decision, not a claim that remote logs are collected.

Likewise, host/container collection is not enabled through application registration. ENSAMS node-exporter, cAdvisor, PHP-FPM and Nginx exporters are local-only per the supplied audit. The existing Ansible Alloy role stages configuration but does not install an agent, prove host mounts, or collect Docker/container metrics. A future role must pin the agent, support AMD64 and ARM64, restrict sources, report health/version, bound queues and provide a safe rollback before a registration method can be allowed.

## Labels and probes

Prometheus application scrape/probe labels are `application`, `environment`, and `host`. Registration labels are fixed identity values; no custom runtime labels are accepted. Loki labels should follow the same low-cardinality contract if log collection is later implemented. Prometheus scrapes applications every 30 seconds with a 10 second timeout; Blackbox uses the existing TLS-verifying `http_2xx` module. ENSAMS `/up` means framework liveness, not database/Redis readiness. Configure a separate readiness endpoint only after its dependency semantics and exposure are approved.

## Alerts and dashboards

Prometheus alerts cover scrape failure and failed health probes. Deterministic generated per-registration `absent()` alerts detect when an enabled scrape or probe target disappears from file-SD; CI also fails if an enabled registration cannot generate a target. Alertmanager groups by application/environment/host as well as existing host identity labels, but its default receiver remains a sink without a protected webhook. Verify notification routing before relying on alerts. App-specific queue/scheduler rules must be checked against actual exported names and labels before migration. ENSAMS dashboard and rule source paths are explicitly marked as belonging to the application repository and are not present/imported here; adapt them only after obtaining source and comparing datasource UIDs, PromQL/LogQL, labels and variables against central data.

## Capacity, failure and recovery

The central host is a constrained single node. Current config sets metric and log retention, but actual retention depends on telemetry volume, indexes, compaction and OS/storage headroom. Record measured ingest and filesystem use before accepting production retention. During central outage, agents may retry/buffer according to their actual configured queue behavior; verify bounds, recovery and loss behavior. No HA, off-host backup destination, RPO/RTO, or restore proof is established by this onboarding work.

## Network gates

The central policy is `applications/policy.yml`; `approved_wireguard_cidr` intentionally remains null. Set it only after checking the selected RFC1918 IPv4 or IPv6 unique-local range against VPC, Docker bridges, host and operator VPN routes and approving it. The `10.77.0.0/24` network remains a proposal. Application registrations cannot override the policy. Metrics targets must be explicit private, non-special IPv4 or bracketed IPv6 literals in that CIDR; the validator performs no DNS lookup. Obtain the exact peer address, host port, firewall source and observed Docker/NAT path before enabling a scrape. AWS/public firewall rules and production WireGuard peers are outside this repository change.
