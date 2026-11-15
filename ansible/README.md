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
