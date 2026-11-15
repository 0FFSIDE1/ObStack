# Ansible automation

The inventory example is intentionally incomplete. Copy it to inventory/hosts.yml only after replacing placeholders with verified host data and checking all address ranges.

## Read-only discovery first

Run the preflight and Alloy discovery playbooks before any mutating playbook:

    ansible-playbook playbooks/preflight.yml
    ansible-playbook playbooks/discover-alloy.yml

The Alloy discovery playbook lists Docker containers and inspects only safe metadata (image, state, restart policy, mounts, Compose project/service labels and networks). It does not print environment variables, install packages, stop containers, or change configuration.

## WireGuard

The wireguard.yml playbook targets the wireguard inventory group and refuses to run unless obstack_apply=true is explicitly supplied. It installs WireGuard, writes a root-only interface config and enables wg-quick. This is a mutating playbook; do not run it until the VPC/overlay ranges, host addresses, peer keys, AWS security group, firewall, SSH rollback and maintenance window are reviewed.

Supply each private key only through Ansible Vault or an approved secret manager. The repository contains no production keys. Public keys and peer /32 metadata may be kept in protected inventory after verification.

## Alloy

The Alloy role defaults to preserve. It does not install a duplicate Alloy container or stop/restart an existing container. Run discovery, identify each container's Compose owner and config/data mounts, back up the existing config, then explicitly set that host's obstack_alloy_existing_policy=adopt.

Adoption stages a config and root-only password files; it does not automatically mount those files into a running container or restart it. A reviewed host-specific Compose change must mount the config, password files, CA certificate, /proc, /sys and host rootfs as read-only paths as appropriate. Log collection sources must be selected after checking whether the existing container has Docker socket, journald or file access.

Credentials and private keys belong in Ansible Vault. Never commit secrets, render them in CI, or use debug tasks to print them. Mutating playbooks require obstack_apply=true and separate explicit production approval.


## Fleet size and staged rollout

There is no fixed ten-server limit. Add only the hosts approved for the current batch to the monitored group. Discovery and WireGuard peer templating iterate over current inventory membership. Start with two pilot hosts (preferably one AMD64 and one ARM64), then add three or four at a time after pilot and capacity gates pass. Continue adding hosts as needed; do not hardcode a fleet count.

Run discovery only against the current inventory:

    ansible-playbook -i inventory/hosts.yml playbooks/discover-alloy.yml

To scope it to a selected pilot subset, use a host pattern or --limit, for example:

    ansible-playbook -i inventory/hosts.yml playbooks/discover-alloy.yml --limit 'pilot-01,pilot-02'

The playbook is read-only, but it still requires working SSH/Ansible access and privilege escalation to inspect Docker. It cannot discover hosts that are not in the inventory or that cannot be reached. Discovery has not yet been run against the user's servers.

Review central CPU, memory, disk headroom, metrics/log ingestion, retention achieved and query latency before every expansion batch. The current central 2 vCPU / 2 GB / 14 GB configuration is only a pilot starting point; increase EC2/EBS resources or redesign storage based on measured growth. Resizing is not performed automatically by these playbooks.
