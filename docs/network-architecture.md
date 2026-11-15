# ObStack — WireGuard Network Architecture

**Status:** Selected design documented; automation scaffold committed; no deployment performed.  
**Scope:** One future AWS EC2 ARM64 hub and ten Ubuntu 24.04 remote servers (five AMD64, five ARM64).  
**Transport:** Native self-managed WireGuard, hub-and-spoke.  
**Hub endpoint:** Existing Elastic IP reported by user, but not associated with an EC2 instance. VPC/EC2 do not yet exist.

## Topology and policy

Each remote host initiates an outbound WireGuard UDP tunnel to the future AWS hub on UDP 51820. Each host gets a unique keypair and /32. Hub peer AllowedIPs are restricted to that spoke's assigned /32. Spokes route only the hub overlay address and explicitly approved central service destinations. No default route, forwarding, NAT, site-to-site routing or remote-to-remote access is planned.

The proposed overlay 10.77.0.0/24 and host mapping are provisional only. Check against the planned VPC CIDR, office/home/existing VPN routes and each server's local routes/Docker bridge networks before configuring. The remote hosts are standalone public-facing servers; no remote private subnet routing is required.

AWS security-group UDP 51820 ingress should be restricted to the ten verified static public IPv4 /32 source addresses. Spokes require no inbound WireGuard port. Preserve existing SSH management access and validate host firewall/Docker forwarding behavior before changes.

## Telemetry security

WireGuard encrypts the transport but is not service authentication. Alloy must send metrics and logs to authenticated HTTPS endpoints with CA verification enabled. No insecure_skip_verify workaround is allowed. Central listeners must be reachable only over the WireGuard interface or a tightly restricted private ingress, never exposed as unauthenticated public services.

The Compose stack includes a hardened Nginx container as the HTTPS reverse-proxy edge. During bootstrap it binds only to host loopback port 443; after the WireGuard hub is provisioned and verified, bind it to the hub's WireGuard IPv4 address and keep public TCP 443 closed. Nginx currently proxies the Grafana UI only. Prometheus remote-write and Loki push routes must be added with endpoint-specific authentication before Alloy can send telemetry. Prometheus must explicitly enable its remote-write receiver. Loki tenant authentication must be configured and validated. The TLS certificate SANs must match the names configured in Alloy.

## Host time

The central Ubuntu host timezone is set to `Africa/Lagos`. Chrony maintains system clock synchronization; telemetry timestamps should remain UTC-normalized across services and hosts to avoid ambiguity during cross-region correlation. Docker containers retain their image defaults (normally UTC) unless deliberately configured otherwise.

## Repository automation

- ansible/playbooks/wireguard.yml installs WireGuard and configures wg-quick on inventory group wireguard. It requires obstack_apply=true and unique per-host private/public key material.
- ansible/playbooks/discover-alloy.yml is read-only. It inventories existing Docker containers and Alloy mounts/Compose ownership without printing environment variables.
- ansible/playbooks/alloy-onboarding.yml stages a secure config only for hosts explicitly marked adopt. The default policy is preserve. It does not stop, restart, replace or automatically rewire a running container.
- Private keys and telemetry passwords must be supplied through Ansible Vault or an approved secret manager, never Git.

The first-pass roles have not yet been validated against live hosts or a native ARM64/AMD64 staging pair. They are not production-ready.

## Preconditions and sequence

1. Confirm VPC CIDR, office/home/existing VPN ranges and route overlap.
2. Verify the Elastic IP allocation/region and plan its association with the future hub.
3. Collect all ten hostnames, static public egress IPs, architectures, project/environment mappings and SSH access method.
4. Run read-only discovery to identify which hosts already run Alloy, image/tag, Compose ownership, config/state mounts, network mode and collection sources.
5. Generate unique keys securely and store private keys in Vault; review the AWS UDP 51820 source allowlist and firewall rollback.
6. Implement and test central authenticated TLS ingress, remote-write receiver and Loki tenant/auth behavior.
7. Pilot one AMD64 and one ARM64 host; test peer isolation, TLS/auth, metrics/log delivery, reboot and recovery.
8. Adopt existing Alloy containers individually after backup and Compose-owner review; do not create duplicate agents.
9. Roll out remaining hosts in batches only after pilot acceptance and explicit production authorization.

No packages, keys, firewall rules, AWS resources or production services have been changed by these repository commits.
