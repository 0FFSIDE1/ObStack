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

This is the first automated validation component, not yet an end-to-end Ansible discovery pipeline. AWS routes, host routes, Docker networks and home/office VPN CIDRs must still be gathered and normalized into the input file. The next automation stage can use AWS read-only API calls and Ansible read-only host tasks to create this input automatically. A clean candidate remains a recommendation: the operator/network owner must review and approve it before setting the inventory's `obstack_wg_address` and `obstack_wg_vpn_ip` values or running the mutating `wireguard.yml` playbook.

Never use this preflight to justify opening broad security-group ingress or enabling full-tunnel routing.
