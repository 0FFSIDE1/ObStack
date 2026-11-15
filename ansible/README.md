# Ansible automation

The inventory example is intentionally incomplete. Copy it to inventory/hosts.yml only after replacing placeholders with verified host data and checking all address ranges.

## Central host: first-time provisioning

The central host playbook provisions a clean Ubuntu 24.04 ARM64 EC2 instance. It installs baseline security packages, configures conservative SSH hardening, UFW, fail2ban and unattended security updates, installs Docker Engine from Docker's official apt repository, generates a private ObStack CA and a central server certificate for the approved WireGuard IP, deploys the Compose stack, starts it and checks Prometheus/Grafana readiness.

Before running:
- Ensure SSH key-based access works and keep the current SSH session open during the first run. Password authentication remains enabled by default; disable it only after key-only access has been verified.
- Confirm the central host inventory address, SSH port, ARM64 architecture, approved WireGuard IP and administrator public IPv4 CIDR.
- Review the VPC/subnet, security group and host firewall rules. The playbook restricts SSH to `obstack_ssh_allowed_cidr`, allows UDP 51820 for WireGuard, and allows HTTPS only on wg0. Do not enable UFW until the SSH path and provider firewall are understood.
- Set `obstack_repo_root` to the checked-out repository root on the Ansible controller.
- Put `obstack_grafana_admin_user` and a unique 24+ character `obstack_grafana_admin_password` in Ansible Vault. Never put secrets in plaintext inventory or Git.
- Install controller collections: `ansible-galaxy collection install -r ansible/requirements.yml`.
- Check free disk space. The current 14 GB pilot disk is tight; this playbook does not resize EBS or guarantee requested retention.

Syntax-check and inspect first:

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/central.yml --syntax-check
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/central.yml --list-tasks
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/central.yml --check --diff --ask-vault-pass

After approval and during a maintenance window:

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/central.yml --ask-vault-pass -e obstack_apply=true

The central playbook is intentionally gated by `obstack_apply=true`. It does not create AWS resources, associate the Elastic IP, alter AWS security groups, configure WireGuard peers, or expose Grafana/Prometheus/Loki publicly. UFW HTTPS ingress is scoped to wg0. The private CA key and server key stay root-only on the central host; back them up securely offline before replacing the instance. The generated certificate SAN is the WireGuard IP, so remote agents must connect using that address and trust `/etc/obstack/pki/ca.crt`.

SSH password authentication is not disabled automatically to avoid locking out a first-time host. Validate key-only SSH in a separate session, then set `obstack_ssh_password_authentication: "no"` in protected host vars and rerun. Review the generated SSH drop-in and UFW rules before the first production run.

## Read-only discovery first

Run the preflight and Alloy discovery playbooks before any remote mutating playbook:

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/preflight.yml
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/discover-alloy.yml

The Alloy discovery playbook lists Docker containers and inspects only safe metadata (image, state, restart policy, mounts, Compose project/service labels and networks). It does not print environment variables, install packages, stop containers, or change configuration.

## WireGuard

The wireguard.yml playbook targets the wireguard inventory group and refuses to run unless obstack_apply=true is explicitly supplied. It installs WireGuard, writes a root-only interface config and enables wg-quick. This is a mutating playbook; do not run it until the VPC/overlay ranges, host addresses, peer keys, AWS security group, firewall, SSH rollback and maintenance window are reviewed.

Supply each private key only through Ansible Vault or an approved secret manager. The repository contains no production keys. Public keys and peer /32 metadata may be kept in protected inventory after verification.

## Alloy

The Alloy role defaults to preserve. It does not install a duplicate Alloy container or stop/restart an existing container. Run discovery, identify each container's Compose owner and config/data mounts, back up the existing config, then explicitly set that host's obstack_alloy_existing_policy=adopt.

Adoption stages a config and root-only password files; it does not automatically mount those files into a running container or restart it. A reviewed host-specific Compose change must mount the config, password files, CA certificate, /proc, /sys and host rootfs as read-only paths as appropriate. Log collection sources must be selected after checking whether the existing container has Docker socket, journald or file access.

Credentials and private keys belong in Ansible Vault. Never commit secrets, render them in CI, or use debug tasks to print them. Mutating playbooks require obstack_apply=true and separate explicit production approval.
