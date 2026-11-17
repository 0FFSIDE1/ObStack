# ObStack — WireGuard Network Architecture

**Status:** Selected design, authenticated ingestion configuration, WireGuard provisioning, public-CA distribution, central validation and CIDR discovery automation are committed. No AWS or production-host deployment has been performed.  
**Scope:** One future AWS EC2 ARM64 hub and a dynamic fleet of Ubuntu 24.04 remote servers (currently ten are identified: five AMD64 and five ARM64).  
**Transport:** Native self-managed WireGuard, hub-and-spoke.  
**Hub endpoint:** Existing Elastic IP reported by user, but not associated with an EC2 instance. VPC/EC2 do not yet exist.

## Topology and policy

Each remote host initiates an outbound WireGuard UDP tunnel to the future AWS hub on UDP 51820. Each host gets a unique keypair and /32. Hub peer AllowedIPs are restricted to that spoke's assigned /32. Spokes route only the hub overlay address and explicitly approved central service destinations. No default route, forwarding, NAT, site-to-site routing or remote-to-remote access is planned.

The proposed overlay 10.77.0.0/24 and host mapping are provisional only. Check against the planned VPC CIDR, office/home/existing VPN routes and each server's local routes/Docker bridge networks before configuring. The remote hosts are standalone public-facing servers; no remote private subnet routing is required.

AWS security-group and central UFW UDP 51820 ingress must be restricted to the verified static public egress IPv4 /32 source addresses for currently enrolled spokes. Store the verified source separately as obstack_wg_peer_public_ip; do not assume the SSH management address is necessarily the observed tunnel source. Spokes require no inbound WireGuard port. Preserve existing SSH management access and validate host firewall/Docker forwarding behavior before changes.

## Telemetry security

WireGuard encrypts the transport but is not service authentication. Alloy sends metrics and logs to authenticated HTTPS endpoints with CA verification enabled. No insecure_skip_verify workaround is allowed.

The Dockerized Nginx edge terminates TLS using the central certificate signed by the private ObStack CA. It exposes:
- POST /api/v1/write to Prometheus, protected by a per-host metrics Basic Auth file. Prometheus must run with --web.enable-remote-write-receiver.
- POST /loki/api/v1/push to Loki, protected by a separate per-host logs Basic Auth file. Nginx sets X-Scope-OrgID to obstack; Loki auth_enabled remains true.

Each enrolled host has distinct metrics and logs credentials stored in Ansible Vault and installed as bcrypt htpasswd entries. Passwords are staged to the remote host as root-only files and mounted into Alloy as read-only secrets. Prometheus and Loki do not have public host port bindings; their published ports remain on 127.0.0.1.

During bootstrap Nginx binds only to host loopback port 443. After the WireGuard hub is provisioned and verified, set its bind address to the hub's WireGuard IPv4 address. Keep public TCP 443 closed in the AWS security group. The central certificate SAN and Alloy URL host must match the same WireGuard IP.

This first iteration uses a single Loki tenant, obstack. Per-host Basic Auth authenticates agents but does not provide per-project Loki tenant isolation. Review data classification and access policy before introducing multi-tenant or customer-isolated workloads.

## Certificate distribution

The central Ansible certificates role creates a private CA and a central server certificate. The CA private key and server key remain root-only on the central host. The gated distribute-ca playbook transfers only the public CA certificate to enrolled spokes and verifies it; it never copies a private key. The existing Alloy container must mount the host CA file read-only at the path configured in its TLS settings. A systemd timer is configured to renew the central leaf certificate before it expires and validate/reload Nginx. Runtime timer execution still needs verification; CA rotation and peer trust refresh remain operational work.

## Host time

The central Ubuntu host timezone is set to Africa/Lagos. Chrony maintains system clock synchronization; telemetry timestamps should remain UTC-normalized across services and hosts to avoid ambiguity during cross-region correlation. Docker containers retain their image defaults (normally UTC) unless deliberately configured otherwise.

## Repository automation

- ansible/playbooks/wireguard.yml: mutating role; requires obstack_apply=true and validates hub/spoke inventory, key inputs, unique spoke addresses and /32 peer assignments.
- ansible/playbooks/distribute-ca.yml: gated distribution of the public CA certificate only.
- ansible/playbooks/validate-central.yml: read-only runtime checks for central services, Prometheus remote-write receiver, TLS trust and Nginx authentication.
- ansible/playbooks/discover-alloy.yml: read-only discovery across the current monitored inventory.
- ansible/playbooks/alloy-onboarding.yml: preserve-by-default; adoption stages config and password files only and does not restart or rewire a container.
- Private keys and credentials remain external secrets in Ansible Vault.

## CIDR overlap preflight

See [network CIDR overlap preflight](network-cidr-overlap-preflight.md) and the read-only Python checker at `ansible/scripts/check_cidr_overlaps.py`. The manual workflow now gathers AWS VPC/subnet ranges, host interfaces/routes, and Docker IPAM ranges before running the checker. It requires network credentials and complete host access; office/home VPN ranges still need to be disclosed by their owners. The workflow is read-only and requires human approval before any network change.

## Preconditions and sequence

1. Confirm VPC CIDR, office/home/existing VPN ranges and route overlap.
2. Verify the Elastic IP allocation/region and plan its association with the future hub.
3. Collect the current pilot hosts' names, static public egress IPs, architectures, project/environment mappings and SSH access method.
4. Run read-only discovery to identify which hosts already run Alloy, image/tag, Compose ownership, config/state mounts, network mode and collection sources.
5. Generate unique keys securely and store private keys and per-host telemetry passwords in Vault; review the AWS UDP 51820 source allowlist and firewall rollback.
6. Run CI syntax/lint/Compose/Nginx checks; review the central deployment and WireGuard playbooks.
7. Provision central services and WireGuard only after separate explicit production authorization.
8. Distribute the public CA, bind Nginx to the WireGuard IP, and run validate-central.yml.
9. Pilot one AMD64 and one ARM64 host; test peer isolation, TLS/auth, metrics/log delivery, reboot and recovery.
10. Adopt existing Alloy containers individually after backup and Compose-owner review; do not create duplicate agents.
11. Roll out remaining hosts in batches only after pilot acceptance and capacity gates pass.

No packages, keys, firewall rules, AWS resources or production services have been changed by these repository commits.
