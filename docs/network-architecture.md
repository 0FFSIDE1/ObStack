# ObStack — WireGuard Network Architecture

**Status:** Selected design documented; implementation pending.  
**Decision owner:** User  
**Workload classification:** Non-commercial (user-confirmed)  
**Scope:** One central AWS EC2 observability host and ten Ubuntu 24.04 LTS remote servers (5 AMD64, 5 ARM64).  
**Central endpoint:** AWS Elastic IP is user-confirmed; the literal address has not been supplied or recorded.

## 1. Decision

Use **native, self-managed WireGuard**, in a hub-and-spoke topology. WireGuard is selected for its small footprint, mature Linux support, low operational overhead and lack of per-device software licence fees. This is a software-cost statement, not a guarantee of zero total cost: AWS public IPv4, data transfer, storage, and any additional cloud resources may incur charges.

The initial design does not use Tailscale, Headscale, a commercial VPN service, or a separate VPN appliance. No WireGuard software has been installed and no production host, AWS security group, firewall, route table or application has been changed as part of this documentation work.

## 2. Topology

- **Hub:** central AWS EC2, Ubuntu 24.04 LTS, user-reported ARM64/Graviton, with a user-confirmed Elastic IP (actual address to verify during deployment), proposed VPN address 10.77.0.1.
- **Spokes:** ten remote Ubuntu 24.04 LTS hosts. Five AMD64 and five ARM64. Proposed addresses 10.77.0.11 through 10.77.0.20.
- **Transport:** each remote host initiates an outbound WireGuard UDP tunnel to the hub's stable public endpoint on UDP 51820.
- **Telemetry:** Alloy forwards metrics and logs to central endpoints over the VPN. Prometheus, Loki, Grafana and exporters are not directly exposed to the public internet.
- **Management:** Ansible/SSH remains a separately restricted management path; VPN membership does not automatically grant SSH access.

```text
Remote-01..10 (Ubuntu 24.04; 5 amd64 + 5 arm64)
  Alloy / exporters
       | outbound UDP 51820 (encrypted WireGuard)
       v
Internet / NAT
       |
       v
AWS Security Group: UDP 51820 only
       |
Central EC2 — WireGuard hub (10.77.0.1)
       |
       +-- authenticated TLS telemetry ingress over wg0
       |      +-- Prometheus remote-write
       |      +-- Loki log push
       |
       +-- private observability services
              +-- Grafana / Alertmanager / Blackbox
```

## 3. Address and peer policy

The following is a **provisional plan**, not an instruction to configure addresses before checking for overlap.

| Node | Proposed tunnel address | Architecture |
|---|---:|---|
| Central hub | 10.77.0.1/24 | ARM64 |
| Remote 01–05 | 10.77.0.11/32–10.77.0.15/32 | Five AMD64 hosts |
| Remote 06–10 | 10.77.0.16/32–10.77.0.20/32 | Five ARM64 hosts |

Before adoption, check 10.77.0.0/24 against the AWS VPC CIDR, all ten remote networks, office/home LANs, other VPNs, peering and any future connected networks. Change the proposed range if it overlaps. The host-to-address allocation must be recorded in the authoritative inventory and must not be assumed from the architecture counts.

Peer restrictions:
- Generate a unique key pair per host. Never clone a private key between servers.
- On the hub, each peer gets only its assigned remote /32 in AllowedIPs.
- On each remote host, initially route only the hub VPN address (10.77.0.1/32) and required central service destinations through the tunnel.
- Do not configure 0.0.0.0/0, IPv6 default routes, broad remote subnets, site-to-site transit, or remote-to-remote access in the initial rollout.
- Configure PersistentKeepalive = 25 on remote peers when required to maintain NAT mappings. The hub accepts authenticated peers whose public endpoint changes.
- No IP forwarding or NAT is needed when spokes only access services hosted on the hub.

## 4. AWS and host firewall policy

1. Retrieve and verify the existing Elastic IP allocation and association with the central EC2 instance; record it in deployment inventory/configuration (not as a guessed value). No additional Elastic IP allocation is currently required.
2. Permit inbound UDP 51820 in the hub's AWS Security Group. Since remote source IPs may be dynamic, initial ingress may require a broad source range; narrow it to known static egress addresses whenever feasible and review this exposure.
3. Do not add public inbound rules for Prometheus 9090, Loki 3100, Grafana 3000, Node Exporter 9100, cAdvisor or other exporter ports.
4. On the hub, permit only required telemetry and management flows on the WireGuard interface. Remote peers should not gain general host or container-network access.
5. On remote hosts, allow outbound UDP to the hub endpoint; no public inbound WireGuard port is required for the spoke-initiated topology.
6. Validate effective nftables/iptables rules. Docker-published ports can interact with or bypass simplistic UFW assumptions; use a tested policy (including Docker's forwarding chains where relevant) and verify from an external network.
7. Preserve SSH access through its existing approved path; do not unintentionally lock out management during firewall changes.

## 5. Telemetry ingress and encryption

WireGuard encrypts the network path but does not replace service authentication, authorization or TLS policy.

- Prefer a deliberately VPN-bound listener or reverse proxy reachable over wg0, with TLS verification and authentication enabled.
- Prometheus remote-write receiver and Loki push endpoints must not be unauthenticated on a public interface.
- Bind/publish container ports carefully. Confirm the listener is reachable from the VPN while not reachable from the public internet.
- Use a private DNS name with a trusted internal CA, or a certificate strategy whose SANs match the endpoint used by Alloy. Do not disable TLS verification to work around certificate errors.
- Allow only the necessary remote-to-hub flows. The exact endpoint ports and proxy configuration are implementation decisions to be validated against the selected component versions.

## 6. Keys and configuration management

- Private keys and preshared keys are secrets. Generate them securely and distribute them through a protected mechanism.
- Do not commit private keys, preshared keys, access tokens or rendered secret files to Git.
- Store only public keys and non-secret peer metadata in ordinary inventory. Use Ansible Vault or an approved secrets manager for protected values.
- Restrict key/config file permissions (private key readable only by root); avoid secrets in command-line arguments, CI logs or debug output.
- Document peer rotation and revocation: remove/revoke the peer on the hub, deploy a replacement key/config, verify the new handshake, and confirm the old key can no longer establish access.
- Back up encrypted configuration and key material off-host with controlled key custody. A backup is not validated until restoration is tested.

## 7. Resilience, observability and failure modes

- Alert separately on WireGuard interface failure, stale/missing peer handshakes, missing Prometheus series, missing log ingestion and central service health.
- A recent WireGuard handshake does not prove Alloy is healthy or telemetry is arriving.
- Configure Alloy buffering/retry limits appropriate to disk capacity. The remote host must not exhaust its disk during a prolonged hub outage.
- The hub is a single point of failure. During hub downtime, remote agents should retry and buffer only within verified limits; telemetry gaps remain possible.
- Test reboot persistence, transient internet loss, NAT rebinding, hub restart, key revocation, and restoration from encrypted backup.

## 8. Implementation sequence (not yet executed)

1. Discovery: confirm VPC CIDR, remote network ranges, central public/static endpoint, UDP egress, firewall ownership, hostnames and server-to-project mapping.
2. Inventory: assign stable IDs, VPN /32 addresses, architecture, owners and environment labels to all ten hosts.
3. Staging: validate WireGuard package/version and kernel support on central ARM64 and representative remote ARM64/AMD64 hosts.
4. Hub: prepare configuration and security-group/firewall change plan; review management lockout and rollback steps.
5. Pilot: onboard one AMD64 and one ARM64 host, validate routes, peer isolation, telemetry TLS/authentication and public-port exposure.
6. Fleet: onboard remaining hosts in controlled batches after pilot acceptance.
7. Operations: add peer/telemetry alerts, key rotation/revocation procedures, encrypted backup and restore tests.
8. Review: record actual test evidence and residual risks; seek explicit production deployment approval before any live changes.

## 9. Preconditions / open decisions

- Actual central EC2 instance type, kernel architecture, and exact Elastic IP value/association (Elastic IP existence is user-confirmed).
- AWS VPC CIDR and remote network CIDRs; confirmation the proposed VPN range is non-overlapping.
- Per-host names, architecture, project/environment mapping, static/dynamic public egress and ownership.
- UDP egress policy and AWS Security Group/firewall change authority.
- Private DNS and TLS certificate/CA approach; telemetry endpoint authentication.
- Secret storage, key custody, backup destination, RPO/RTO and recovery owner.
- Staging hosts and an approved production change window.

## 10. Explicit safety boundary

This document and the associated implementation plan are design artifacts only. No packages have been installed; no keys generated for production; no inventory secrets created; no AWS rules, routes, host firewalls or services changed; no production host contacted or modified. Any deployment requires a separate explicit authorization after the preconditions and rollback plan are reviewed.
