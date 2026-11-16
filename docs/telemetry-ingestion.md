# ObStack authenticated telemetry ingestion

## Data paths

The central endpoints are configured for future Alloy remote-write and Loki push traffic through the private WireGuard overlay and Docker Nginx reverse proxy. Nginx terminates TLS using the central certificate signed by the ObStack private CA and enforces HTTP Basic Authentication before forwarding requests. This repository does not prove that any remote agent or log source is active. The current Alloy role only stages a starter config; its Loki writer has no log source.

| Purpose | Agent URL path | Backend | Authentication |
|---|---|---|---|
| Prometheus remote-write | /api/v1/write | prometheus:9090/api/v1/write | Per-host metrics username/password |
| Loki push | /loki/api/v1/push | loki:3100/loki/api/v1/push | Per-host logs username/password; tenant obstack |

Prometheus remote-write receiver is enabled explicitly with --web.enable-remote-write-receiver. Loki retains auth_enabled=true; Nginx sets X-Scope-OrgID to the single-node tenant obstack after authenticating the caller. Prometheus and Loki are not published on public host interfaces. Their host ports remain bound to 127.0.0.1. Nginx runs as an unprivileged UID with a dedicated host-created group; only that group can read the central TLS key and bcrypt htpasswd files. The Grafana .env file remains root-only.

Application `/metrics` scrapes are a separate pull path. Registrations are validated and generate targets only when their literal IP/port lies within the centrally approved `applications/policy.yml` WireGuard CIDR. That CIDR remains null and ENSAMS remains disabled until network review and application-owner values are supplied. The scrape target must be bound to the verified WireGuard interface on the remote host, and Laravel's allowlist must match the source it observes after Docker/NAT. Do not authorize forwarded headers. Keep public `/metrics` denial in place.

Nginx publishes HTTPS on loopback during bootstrap. Once WireGuard is provisioned and verified, set the central Nginx bind address to the hub's WireGuard IPv4 address and rerun central provisioning. AWS security-group TCP 443 remains closed to the public internet. Only UDP 51820 is needed for the WireGuard hub. Both AWS Security Group ingress and central UFW ingress are restricted to each enrolled host's separately verified static public egress IPv4 /32, recorded as obstack_wg_peer_public_ip; do not assume the SSH management address is necessarily the observed tunnel source.

## Credential model

The existing Ansible model supports separate per-host metrics and logs credentials for a future agent. These credentials and endpoints do not indicate a live enrolled host or a working log source. Remote log collection methods are currently rejected by the application-registration schema because the source, least-privilege boundary, agent lifecycle and bounded buffering are not implemented. Never store passwords or private keys in GitHub.

The two Nginx password files are:
- /etc/obstack/secrets/metrics.htpasswd
- /etc/obstack/secrets/logs.htpasswd

A future Alloy container would mount staged metrics/logs password files read-only at `/run/secrets/metrics_password` and `/run/secrets/logs_password`. The role does not adopt/restart a container by default. The host files remain root-only; discover the container UID/GID and use a dedicated group before any separately reviewed mount. Never make password files world-readable. Credential rotation is performed by updating the protected secret source, refreshing central auth files, then staging updated files to the agent.

This first iteration uses one Loki tenant, obstack, for the entire ObStack installation. Basic Auth distinguishes enrolled hosts but does not create per-project Loki tenant isolation. Project/environment labels and authorization policy must be reviewed before multi-tenant or customer-isolated workloads are introduced.

## TLS and certificate distribution

The central certificates role creates a private CA key/certificate and a central server certificate with an IP SAN matching the hub WireGuard address. The CA private key and central server private key remain root-only on the central host. The distribute-ca playbook transfers only the public CA certificate to enrolled spokes, in batches of two, and verifies the installed certificate. It never transfers a private key.

The Alloy container must mount the spoke host certificate at /etc/ssl/certs/obstack-ca.crt, matching the Alloy tls_config ca_file. Certificate SAN and the IP in both Alloy URLs must match exactly. Do not disable TLS verification. CA renewal, server certificate renewal and automated rotation remain operational follow-up work; monitor the 397-day leaf certificate expiry and retain the CA private key securely offline.

## WireGuard hub and spokes

The hub listens on UDP 51820. Spokes initiate outbound tunnels and use PersistentKeepalive=25. The hub peer AllowedIPs list contains only each spoke's unique /32; each spoke routes only the hub /32. No full-tunnel default route, IP forwarding, NAT or spoke-to-spoke routing is configured.

The proposed 10.77.0.0/24 overlay is still provisional. The VPC CIDR has not been supplied and must be selected after checking office/home/existing VPN ranges and remote host/Docker bridge routes. The existing Elastic IP is not yet associated with an EC2 hub. Do not run the mutating WireGuard playbook until the network plan, all peer public IPs/keys, UDP 51820 source allowlist, SSH rollback and maintenance window are reviewed.

## Rollout sequence

1. Finalize the VPC CIDR and WireGuard overlay after route-overlap checks; verify the Elastic IP and collect the current pilot hosts' static public IPs and architecture.
2. Add only the approved pilot hosts to Ansible inventory and store unique private keys and metrics/logs credentials in Vault.
3. Run syntax/lint/Compose/Nginx CI validation; inspect all proposed playbook changes.
4. Provision the central host only after separate explicit authorization; it remains loopback-only at this point.
5. Provision WireGuard on the hub and selected spokes under an approved maintenance window; verify handshake and peer isolation.
6. Distribute the public CA certificate to pilot spokes.
7. Bind Nginx to the central WireGuard IP and keep public TCP 443 closed.
8. Run validate-central.yml. It checks service readiness, TLS trust, the Prometheus receiver flag, unauthenticated rejection and acceptance of an enrolled host's credentials.
9. Review existing Alloy ownership and sources. Do not adopt it for remote logs or host monitoring until a source/privilege design, bounded buffering, health checks, architecture support and rollback are implemented and reviewed.
10. For an application scrape pilot, approve the CIDR/target in central policy and registration, verify the host-only WireGuard bind and Laravel-observed source, then test central `up`, exported series and TLS/auth policy. Do not open a public metrics listener. Logs remain unconfigured until their source design is approved.

## Validation and safety

GitHub Actions validates application schema/policy and generated files, Python tests, Ansible syntax/lint, Alloy syntax/image architectures, Compose, Prometheus config/rules, Alertmanager, Blackbox, Loki, Nginx, secret scanning and whitespace. The read-only validate-central playbook is intended for a provisioned staging/central host and is not a substitute for remote integration tests. Passing CI is not proof of a live application scrape, logs, dashboard, alerts or host metrics.

No AWS resources, security groups, public IP associations, production servers, WireGuard keys, CA private keys or running containers are changed by repository-only work. The 2 vCPU / 2 GB RAM / 14 GB disk central host remains a constrained pilot; retention targets of 30 days metrics and 20 days logs must be verified against measured ingestion and disk growth.
