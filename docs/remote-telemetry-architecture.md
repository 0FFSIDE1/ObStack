# Remote telemetry architecture

## Existing central paths

Remote Alloy agents initiate outbound connections through WireGuard to the ObStack hub. `nginx/conf.d/obstack.conf` terminates TLS using the private ObStack CA and enforces per-host Basic Auth before forwarding Prometheus remote-write to Prometheus or Loki push to Loki. Prometheus and Loki host ports stay on loopback. TLS verification remains enabled. This avoids inbound exporter ports on public remote interfaces.

Application endpoints are a separate path: central Prometheus scrapes an application metrics endpoint over WireGuard, and Blackbox probes its approved health URL. These paths are generated from registrations into Prometheus file-SD. The scrape target must be bound only to the verified WireGuard interface on the application host and its application allowlists must match the source Laravel actually observes after Docker/NAT. Do not authorize forwarded headers. Keep public `/metrics` denial in place.

## Logs and host/container monitoring

The repository's Alloy onboarding role currently stages a starter configuration and preserves existing deployments by default. It does not install or restart Alloy. CI renders and syntax-validates this starter config with a pinned Alloy CLI. Its template has host metric collection and a Loki writer but no log source, so central log receipt is not established by that role alone.

For Docker JSON logs, a centrally managed Alloy agent on each remote host is the candidate design because collection stays local and forwarding reuses the existing authenticated TLS Loki path. However, reading the Docker socket/API is effectively root-equivalent even when mounted read-only: Docker API operations can create privileged containers. Do not enable this path until the maintainer approves the privilege model. A less-privileged alternative is to forward selected application logs to a protected host file/journald stream and grant the agent read-only access only to that path; this requires application/host changes and should be chosen where feasible. Never expose the socket over TCP or mount it into central Alloy.

The log agent must add only stable labels (`service`, `environment`, `host`, `container`), preserve structured JSON, bound Docker rotation and any retry queue, and expose its own health. Staging must measure behavior during central outages and demonstrate that backpressure cannot fill the application disk. Do not label secrets, IDs, user data, request paths, or request bodies.

For host metrics, prefer the existing Alloy Unix exporter where its host mounts and runtime permissions are verified. Add cAdvisor or application-specific Nginx/PHP-FPM exporters only when there is a concrete metric requirement and a verified ARM64/AMD64 artifact. Current ENSAMS exporters are local and not reachable by ObStack. The current repo does not establish remote Docker/container metrics or agent-health ingestion; do not claim those capabilities are complete.

## Labels and probes

Prometheus application scrape/probe labels are `service`, `environment`, and `host`; Alloy host telemetry additionally uses `project`, `role`, and `region` per the existing template. Loki labels should remain low-cardinality. Prometheus scrapes applications every 30 seconds with a 10 second timeout; Blackbox uses the existing TLS-verifying `http_2xx` module. ENSAMS `/up` means framework liveness, not database/Redis readiness. Configure a separate readiness endpoint only after its dependency semantics and exposure are approved.

## Alerts and dashboards

Prometheus alerts now cover an unavailable application scrape and failed application probe in addition to generic `up == 0` targets. Alertmanager currently uses a non-delivery sink unless a protected HTTPS webhook is configured. Verify notification routing before relying on alerts. App-specific queue/scheduler rules must be checked against the exported names and labels before migration. The ENSAMS dashboard JSON is not present in this repository; adapt it only after obtaining source and comparing datasource UIDs, PromQL/LogQL, labels and variables against central data.

## Capacity, failure and recovery

The central host is a constrained single node. Current config sets metric and log retention, but actual retention depends on telemetry volume, indexes, compaction and OS/storage headroom. Record measured ingest and filesystem use before accepting production retention. During central outage, agents may retry/buffer according to their actual configured queue behavior; verify bounds, recovery and loss behavior. No HA, off-host backup destination, RPO/RTO, or restore proof is established by this onboarding work.

## Network gates

The `10.77.0.0/24` network is a proposal and is not used as an ENSAMS target. Verify route overlap with the future VPC, Docker bridges, host and operator VPNs. Obtain the exact peer/central addresses, firewall source and port, and test observed NAT path before filling the registration. AWS/public firewall rules and production WireGuard peers are outside this repository change.
