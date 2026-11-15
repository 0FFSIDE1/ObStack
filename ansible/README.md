# Ansible automation

The inventory example is intentionally incomplete. Copy it to inventory/hosts.yml only after replacing placeholders with verified non-secret host data. Never put passwords, private keys, tokens or vault passwords in inventory, group_vars, host_vars, GitHub files or command-line extra-vars.

## Secret and vault input contract

All sensitive Ansible values are read from the controller process environment through ansible/group_vars/all/env.yml. Required variables:

- OBSTACK_GRAFANA_ADMIN_USER
- OBSTACK_GRAFANA_ADMIN_PASSWORD
- OBSTACK_WG_PRIVATE_KEY_<INVENTORY_HOST> for each WireGuard host
- OBSTACK_ALLOY_METRICS_PASSWORD_<INVENTORY_HOST> for each monitored host
- OBSTACK_ALLOY_LOGS_PASSWORD_<INVENTORY_HOST> for each monitored host

For host-specific names, uppercase the inventory hostname and replace every non-alphanumeric character with an underscore (remote-01 becomes REMOTE_01).

Set the Ansible Vault password-file location through the standard ANSIBLE_VAULT_PASSWORD_FILE environment variable. For convenience, set OBSTACK_ANSIBLE_VAULT_PASSWORD_FILE to a protected file path and export it as ANSIBLE_VAULT_PASSWORD_FILE. The password file must be owned by the operator and mode 0600. Ansible reads the vault password from that file; do not put the password itself in the repository, command arguments or shell history. If encrypted vars files are used, their decryption key is supplied only through this environment-selected password file. Application secrets are environment-backed, not stored in committed vault files.

Example controller setup (populate values from your approved secret manager; do not commit this file):

    export OBSTACK_GRAFANA_ADMIN_USER='admin'
    export OBSTACK_GRAFANA_ADMIN_PASSWORD='...'
    export OBSTACK_WG_PRIVATE_KEY_OBSTACK_CENTRAL='...'
    export OBSTACK_WG_PRIVATE_KEY_REMOTE_01='...'
    export OBSTACK_ALLOY_METRICS_PASSWORD_REMOTE_01='...'
    export OBSTACK_ALLOY_LOGS_PASSWORD_REMOTE_01='...'
    export OBSTACK_ANSIBLE_VAULT_PASSWORD_FILE="$HOME/.config/obstack/vault-password"
    export ANSIBLE_VAULT_PASSWORD_FILE="$OBSTACK_ANSIBLE_VAULT_PASSWORD_FILE"
    chmod 0600 "$ANSIBLE_VAULT_PASSWORD_FILE"

Do not enable shell tracing while secrets are present. CI runs syntax/lint and config checks without production credentials and must not receive them.

## Central host: first-time provisioning

The central host playbook provisions Ubuntu 24.04 ARM64, installs baseline security packages and Docker, creates the private ObStack CA and central server certificate, deploys the Compose stack and checks service readiness.

Before running:
- Verify SSH access and keep the current SSH session open during first provisioning.
- Confirm central inventory address, approved WireGuard IP, administrator CIDR, VPC/subnet and security-group rules.
- Restrict SSH to the administrator CIDR, UDP 51820 to verified spoke egress IPs, and HTTPS to wg0 only.
- Set obstack_repo_root to the absolute repository path on the Ansible controller.
- Supply credentials using the environment contract above. Passwords must be unique and at least 24 characters.
- Install collections with: ansible-galaxy collection install -r ansible/requirements.yml.
- Host timezone defaults to Africa/Lagos; containers retain UTC unless deliberately configured otherwise.
- Nginx binds to loopback during bootstrap. After WireGuard is configured and verified, bind to the hub WireGuard IP. Keep AWS public TCP 443 closed.
- Check free disk space; the 14 GB pilot disk is tight and retention is not guaranteed without measuring ingestion.

Syntax-check and inspect:

    export ANSIBLE_CONFIG="$PWD/ansible/ansible.cfg"
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/central.yml --syntax-check
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/central.yml --list-tasks
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/central.yml --check --diff

After approval and during a maintenance window:

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/central.yml -e obstack_apply=true

Mutating playbooks require obstack_apply=true. No AWS resources, security groups or Elastic IP associations are created or modified by Ansible.

## WireGuard hub and spokes

The WireGuard playbook configures one hub and enrolled spokes. It validates unique overlay IPs, per-host key material and hub endpoint data. Spokes initiate outbound UDP 51820 and use PersistentKeepalive=25; no forwarding, NAT, default route or spoke-to-spoke routing is enabled.

The 10.77.0.0/24 value remains provisional. Do not run until VPC, office/home/VPN routes and Docker bridge ranges have been checked and Elastic IP, peer public addresses, UDP 51820 security-group allowlist, SSH rollback and maintenance window are verified.

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/wireguard.yml --syntax-check
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/wireguard.yml --list-tasks
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/wireguard.yml -e obstack_apply=true

## Certificate distribution and Alloy

Distribute only the public CA certificate after central provisioning:

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/distribute-ca.yml --syntax-check
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/distribute-ca.yml -e obstack_apply=true

The playbook never copies CA or central TLS private keys. Alloy adoption defaults to preserve and does not restart or rewire an existing container. Before mounting staged password files, discover the container UID/GID and grant read-only access through a dedicated group. Never make password files world-readable.

## Central validation

After the hub is active, CA is distributed and Nginx is bound to the WireGuard IP, run:

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/validate-central.yml

This read-only validation checks Compose rendering, services, readiness, Prometheus remote-write receiver, TLS trust and authentication behavior. Secret-bearing tasks retain no_log=true.
