# Network CIDR overlap preflight (read-only)

ObStack includes `ansible/scripts/check_cidr_overlaps.py`, a standard-library Python checker. It can test the proposed WireGuard overlay against a collected network list and report overlapping ranges or clean candidates. It does not create AWS resources, change routes, approve a CIDR, or configure WireGuard.

## Sources that must be collected

The preflight's result is only as complete as the inputs. Gather all these before accepting a candidate:

- AWS VPC primary and associated IPv4 CIDR blocks in the target region/account, plus subnet CIDRs. Use AWS CLI with read-only permissions (such as `ec2:DescribeVpcs` and `ec2:DescribeSubnets`). Include any connected VPCs, peered networks or Transit Gateway routes relevant to the central host.
- Home/office VPN networks and other networks the operator laptop or users need to reach. These must be supplied by the network owner; AWS cannot discover them.
- On each enrolled Ubuntu remote host, the host's local and policy routes (`ip -4 route show table all`) and interface addresses (`ip -4 addr show`).
- Every Docker network CIDR on those hosts (`docker network ls` and `docker network inspect`). Docker's default bridge, user-defined bridges and any custom pools are all relevant.
- Any other connected network ranges or site VPNs. Routes may be hidden from a remote server if they are not configured on that server; network owners must disclose those ranges.

## Commands to collect inputs manually

AWS CLI commands from an authenticated controller (read-only):

```bash
aws sts get-caller-identity
aws ec2 describe-vpcs --region YOUR_AWS_REGION --output json > /secure/path/aws-vpcs.json
aws ec2 describe-subnets --region YOUR_AWS_REGION --output json > /secure/path/aws-subnets.json
```

On each remote Ubuntu host, run via SSH or Ansible (read-only):

```bash
ip -4 route show table all
ip -4 addr show
docker network ls
docker network inspect $(docker network ls -q)
```

The Docker inspect command may return an empty/error response if Docker is absent or no networks exist; note that result explicitly rather than treating the host as scanned.

## Checker input and run

1. Copy `ansible/inventory/network-cidr-discovery.example.json` to a private working file.
2. Replace each placeholder with real CIDR values. Add one network record per VPC association, subnet, office/home VPN route, host route and Docker network. Remove placeholder entries; they are intentionally not valid CIDRs.
3. Keep candidate CIDRs in the `candidates` list. The list contains example possibilities only; they are not approved or guaranteed free.
4. From the repository root run:

```bash
python3 ansible/scripts/check_cidr_overlaps.py /secure/path/network-cidr-discovery.json
```

Exit codes: `0` means no overlap among supplied records and at least one candidate was clean (or no candidate was tested); `2` means an existing-record overlap or no clean candidate. Invalid CIDRs fail with an error. Existing overlaps may be intentional, but require network-owner review.

## Scope and safe gate

An Ansible-driven read-only discovery playbook is now available at `ansible/playbooks/cidr-overlap-discovery.yml`. It queries AWS VPCs and subnets using the AWS CLI, collects IPv4 route tables and Docker network inspect output from inventory hosts in the `wireguard` group, and normalizes records before invoking the checker. Home/office VPN CIDRs remain operator-supplied because those networks are not discoverable from AWS or the remote hosts automatically. A clean candidate remains a recommendation: the operator/network owner must review and approve it before setting the inventory's `obstack_wg_address` and `obstack_wg_vpn_ip` values or running the mutating `wireguard.yml` playbook.

Never use this preflight to justify opening broad security-group ingress or enabling full-tunnel routing.


## Automated Ansible discovery (read-only)

Prerequisites: a verified inventory (hosts in group `wireguard`), Ansible collections installed, AWS CLI installed and authenticated on the controller with read-only `ec2:DescribeVpcs` and `ec2:DescribeSubnets` permissions. Use a dedicated AWS profile or short-lived credentials; do not store credentials in inventory or repository files.

From the repository root, pass the approved target VPC CIDR and the network-owner-confirmed home/office VPN ranges as variables. Candidate overlay ranges are proposals only:

```bash
ansible-playbook -i ansible/inventory/hosts.yml \
  ansible/playbooks/cidr-overlap-discovery.yml \
  -e '{
    "obstack_aws_region": "YOUR_AWS_REGION",
    "obstack_approved_vpc_cidr": "YOUR_APPROVED_VPC_CIDR",
    "obstack_home_office_vpn_cidrs": ["YOUR_HOME_VPN_CIDR", "YOUR_OFFICE_VPN_CIDR"],
    "obstack_candidate_overlay_cidrs": ["10.77.0.0/24", "10.240.0.0/24", "172.30.240.0/24", "192.168.240.0/24"]
  }'
```

The controller writes temporary normalized inputs and per-host discovery records beneath `ansible/tmp/network-discovery` with restrictive permissions. Treat these as internal network information and remove them after review. AWS calls and remote host collection are read-only; the playbook does not change routes, Docker, security groups, or WireGuard. A successful checker result does not grant approval: the network owner must confirm a candidate and only then may it be set in inventory for a separate, explicitly approved WireGuard deployment.

The discovery covers route tables and Docker IPAM subnets on the selected inventory hosts. It does not magically discover unadvertised home/office ranges, disconnected VPCs, or VPN routing outside the supplied AWS region/account; provide those explicitly.


## Host interface CIDR and route validation gate

The automated playbook now collects both `ip -o -4 addr show` (interface-assigned host CIDRs) and `ip -4 route show table all` (connected and routed destination CIDRs) from every host in `wireguard`. It also inspects Docker IPAM networks when Docker is installed. If Docker is installed but inspection fails, discovery fails closed. A host where Docker is absent is recorded explicitly.

The playbook requires exactly 10 hosts in the `monitored` inventory group and at least 11 hosts in `wireguard` (central host plus ten remote hosts). The normalizer independently requires 11 host records. Candidate CIDRs are checked against host interface CIDRs, host route destinations, Docker subnets, AWS VPC/subnet ranges, and operator-supplied VPN ranges. A nonzero result fails the Ansible play.

A clean result opens the **WireGuard approval stage**: review the generated report and obtain explicit network-owner approval. It does not change inventory, configure WireGuard, create keys, or deploy networking.
