# ObStack threat model

**Scope:** repository-defined centralized observability platform for one future AWS EC2 ARM64 hub and up to ten remote Ubuntu 24.04 hosts (five AMD64, five ARM64), with WireGuard, Docker Compose, Nginx, Prometheus, Loki, Grafana, Alertmanager, Blackbox Exporter and Ansible.

**Assessment status:** initial design-level threat model; not a penetration test, CIS benchmark assessment, ISO certification, or review of deployed host state. Runtime controls remain unverified because no AWS or production host is deployed.

## Assets and security objectives

| Asset | Security objective |
|---|---|
| WireGuard private keys, CA key, Grafana credentials, telemetry passwords and webhook URL | Confidentiality; access limited to authorized operators and the service needing each value |
| Telemetry streams and stored metrics/logs | Integrity, confidentiality where sensitive, bounded retention and availability |
| Central host and Docker daemon | Restrict administrative control to approved SSH sources; harden and patch |
| WireGuard peer registry and host identity labels | Authenticate enrolled peers and prevent unintended cross-host access |
| Grafana and service configuration | Versioned change control, authenticated access and reproducible deployment |
| Alerts and recovery procedures | Detect material failures and support safe response |

## Trust boundaries

- **Public AWS interface:** SSH from an approved administrator CIDR and WireGuard UDP 51820 from individually verified static peer egress IPv4 /32s. Public TCP 443 and exporter/backend ports are not intended to be open.
- **WireGuard overlay:** encrypted hub-and-spoke traffic; each spoke has a unique key and /32. No default-route tunneling, forwarding, NAT or spoke-to-spoke communication.
- **Docker service network:** backends communicate on a private Compose bridge. Host-published backend ports bind loopback. Nginx is the authenticated TLS edge.
- **Controller/management boundary:** Ansible executes with explicit obstack_apply=true for mutating playbooks. Secret inputs are sourced from the controller environment; Vault password-file location is environment-selected.
- **Telemetry data boundary:** logs are not collected from any source by the starter template yet. Source selection, redaction and data classification must precede enabling log collection.

## Threat scenarios and current controls

| Threat scenario | Current control / evidence | Residual status |
|---|---|---|
| Internet attacker probes internal exporters or storage APIs | Backend ports bind loopback; UFW/SG ingress design limits public access; Nginx edge is intended to bind only to the WireGuard IP after bootstrap. Compose and network docs. | Must verify effective AWS SG, UFW and Docker firewall behavior on a staged host. |
| Stolen or compromised spoke key reaches other spokes | Unique peer keys and /32 AllowedIPs; central inventory/key checks; no spoke-to-spoke route. ansible/roles/wireguard. | Peer revocation and reconnect tests not run. |
| Stolen telemetry password can impersonate a host | Separate per-host metrics/log credentials, bcrypt htpasswd files, HTTPS CA verification, no secrets embedded in Alloy config. | Rotation procedure and end-to-end unauthorized-peer tests remain pending. |
| Private CA or TLS key disclosure | CA key root-only; central TLS key root-owned and readable only by dedicated Nginx group; public CA distribution only. A weekly systemd timer renews the leaf certificate before 30 days remain and validates/reloads Nginx. | CA key compromise and CA rotation remain manual; renewal timer must be runtime-tested. |
| Untrusted telemetry endpoint impersonates central | Alloy template sets insecure_skip_verify=false and CA file; Nginx certificate SAN is WireGuard IP. | Pilot trust path and certificate expiry monitoring must be tested. |
| Sensitive values leak into CI or Git | CI uses test-only placeholders; Ansible tasks handling secrets use no_log; .env, private keys and credentials are ignored/not committed. | Secret scanning and repository-wide security scan are not yet configured. |
| Existing Alloy agent is disrupted or duplicate agent installed | Discovery is read-only; onboarding defaults preserve; no stop/remove/restart/recreate task. | Host-specific adoption requires Compose owner, mounts and UID/GID discovery and separate approval. |
| Malicious/compromised image or vulnerable dependency | Versioned image tags, constrained service capabilities/resource budgets, read-only Nginx FS and non-root process. | Immutable digest verification, image vulnerability scan and update/rollback review remain pending. |
| Log content contains passwords, tokens, personal or biometric data | No log sources enabled by starter Alloy template; privacy review is required before source adoption. | Redaction tests and source-level data classification remain open. |
| Single hub outage or disk exhaustion causes telemetry loss | Alloy queue/retry behavior is identified as a test requirement; Prometheus 3 GB TSDB block retention cap; Loki 20-day time retention. | Single-node design, filesystem free-space alerting, off-host backup, restore test and capacity measurements are open. |
| Alert receiver is absent or misconfigured | Optional HTTPS webhook destination is environment-backed and CI validates sink/webhook config modes. | No real destination supplied; with the variable unset alerts are not delivered. End-to-end firing/resolved tests pending. |
| Operator applies network/firewall change and loses SSH | Mutating Ansible playbooks require obstack_apply=true; admin source CIDR asserted; SSH is key-only after verifying authorized_keys; sshd config is syntax-checked before reload. | Keep an active session and EC2 console/SSM recovery path; test a second login before closing it. |
| Operator activity is disputed or compromised | auditd records execve/execveat process execution and sudo command invocations are written to a root-only log. | Local audit logs can be altered by root compromise; shell built-ins are not individually captured and off-host immutable forwarding remains future work. |

## Security acceptance gates

Before a staging pilot is considered accepted:

1. Verify AWS Security Group and host firewall effective rules; public TCP 443 and exporter/backend ports remain closed.
2. Verify WireGuard peer isolation, key revocation, reconnect after reboot/network interruption, and source-IP allowlists.
3. Verify TLS chain/SAN and authenticated metrics/log ingestion from one AMD64 and one ARM64 host.
4. Confirm no secrets or sensitive payloads appear in CI logs, repository artifacts, Grafana labels or Loki indexes.
5. Run image/config vulnerability checks and document findings and exceptions.
6. Demonstrate backup restoration and approve RPO/RTO and off-host key custody.
7. Measure CPU, memory, disk and retention at representative ingestion rates.

These gates are not yet passed.