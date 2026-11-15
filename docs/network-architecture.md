# ObStack — WireGuard Network Architecture

**Status:** Selected design documented; first-pass automation committed; no deployment performed.  
**Topology:** Native self-managed WireGuard hub-and-spoke.  
**Hub:** Future AWS EC2 ARM64 host; an Elastic IP is available but not yet associated. VPC/EC2 do not yet exist.  
**Fleet size:** Dynamic. The initial rollout may start with two remote hosts, expand in batches of three or four, and grow beyond ten. The architecture and Ansible inventory are not capped at ten.

## Topology and addressing

Each remote host initiates an outbound WireGuard UDP tunnel to the AWS hub on UDP 51820. Every host receives a unique keypair and unique tunnel /32. The hub's peer AllowedIPs contain only that peer's /32. Spokes route only to the hub's approved overlay/service addresses. No default route, NAT, forwarding, site-to-site routing or remote-to-remote access is planned.

The previously proposed 10.77.0.0/24 is a provisional example, not a fixed fleet limit or final allocation. A /24 has 254 usable host addresses in principle, but actual sizing must account for reserved addresses and future expansion. Select the final overlay after checking the planned VPC CIDR, office/home/existing VPN routes, and each remote host's local and Docker bridge ranges. If projected growth requires it, choose a larger non-overlapping CIDR before deployment rather than renumbering later.

Ansible iterates over the monitored inventory group; add or remove hosts as the fleet changes. Do not encode a fixed count in playbooks, peer templates, address assignment or rollout logic. Address allocation must be unique, documented and reviewed.

## Security policy

- AWS security-group UDP 51820 ingress should be restricted to verified static public egress IPv4 /32 sources for the currently enrolled spokes. Update the allowlist as hosts are added/removed; verify observed egress addresses before applying.
- Spokes require no inbound WireGuard port. Preserve existing SSH management access.
- Keep telemetry endpoints private. WireGuard encryption is not a substitute for service authentication.
- Alloy must use authenticated HTTPS endpoints with CA verification. Do not disable certificate verification.
- Central TLS/auth ingress must proxy to Prometheus remote-write and Loki push. Prometheus remote-write receiver and Loki tenant/auth settings must be explicitly configured and tested before onboarding.
- No private keys or telemetry credentials in Git. Store secrets in Ansible Vault or an approved secret manager.
- Do not enable forwarding/NAT unless a separately reviewed future requirement needs transit routing.

## Alloy discovery and onboarding

Run ansible/playbooks/discover-alloy.yml against the current monitored inventory before onboarding. It is read-only and discovers Docker/Alloy containers on every host currently listed, regardless of how many hosts are enrolled. It reports container image, state, restart policy, mounts and Compose ownership without printing environment variables or secret values.

Existing Alloy containers default to preserve. Adoption is host-by-host after reviewing the existing Compose owner, config/data mounts, collection sources and backups. No automatic duplicate container creation or restart is included. Hosts without Alloy can be onboarded later through a separately reviewed install path.

## Dynamic rollout model

1. Start with two pilot hosts: one AMD64 and one ARM64 where possible.
2. Validate peer isolation, reconnect/reboot, TLS/auth, metric/log delivery, queue behavior and resource use.
3. Add the next three or four hosts as a batch; discover and adopt existing Alloy per host.
4. Repeat batches as needed. The inventory and peer template have no ten-host cap.
5. Update AWS source allowlists and monitoring expectations whenever the enrolled fleet changes.
6. Review central capacity before every expansion batch.

## Central capacity and scaling

The current 2 vCPU / 2 GB RAM / 14 GB disk host is a constrained pilot baseline, not a fixed architecture requirement. Central compute, RAM and storage can be increased as remote hosts, scrape targets, log volume, query concurrency and retention needs grow.

Track daily metrics samples/series, log GB/day, Prometheus TSDB growth, Loki index/chunk growth, disk free space, memory pressure, CPU saturation, ingestion latency and query latency. Size disk from measured daily ingestion × retention plus indexes, compaction, OS/container footprint, backups and free-space headroom. Increase storage first when disk/retention is the constraint; increase RAM/CPU when memory pressure, OOMs, ingestion lag or query latency justify it. Reassess service limits after each expansion. Do not promise 30-day metrics or 20-day logs until measured.

A single central host remains a single point of failure. Scaling vertically does not provide HA. Add object storage, distributed backends or redundant infrastructure only when justified by growth and a separately approved design.

## Automation and safety status

- ansible/playbooks/discover-alloy.yml: read-only discovery across the current monitored inventory.
- ansible/playbooks/wireguard.yml: mutating role; requires explicit obstack_apply=true.
- ansible/playbooks/alloy-onboarding.yml: preserve-by-default; adoption stages configuration/password files only and does not restart or rewire a container.
- Private keys and credentials remain external secrets.

No packages, keys, firewall rules, AWS resources, production services or existing Alloy containers have been changed. The first-pass roles have not yet been validated on live hosts or a native AMD64/ARM64 staging pair.
