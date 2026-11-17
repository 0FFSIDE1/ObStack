# Ansible automation

The inventory example is intentionally incomplete. Copy it to inventory/hosts.yml only after replacing placeholders with verified non-secret host data. Never put passwords, private keys, tokens or vault passwords in inventory, group_vars, host_vars, GitHub files or command-line extra-vars.

## Secret and vault input contract

All sensitive Ansible values are read from the controller process environment through ansible/group_vars/all/env.yml. Required variables:

- OBSTACK_GRAFANA_ADMIN_USER
- OBSTACK_ALERTMANAGER_WEBHOOK_URL (optional; must be HTTPS; unset keeps alerts on the non-delivery sink)
- OBSTACK_GRAFANA_ADMIN_PASSWORD
- OBSTACK_WG_PRIVATE_KEY_<INVENTORY_HOST> for each WireGuard host
- OBSTACK_ALLOY_METRICS_PASSWORD_<INVENTORY_HOST> for each monitored host
- OBSTACK_ALLOY_LOGS_PASSWORD_<INVENTORY_HOST> for each monitored host

For host-specific names, uppercase the inventory hostname and replace every non-alphanumeric character with an underscore (remote-01 becomes REMOTE_01).

Set the Ansible Vault password-file location through the standard ANSIBLE_VAULT_PASSWORD_FILE environment variable. For convenience, set OBSTACK_ANSIBLE_VAULT_PASSWORD_FILE to a protected file path and export it as ANSIBLE_VAULT_PASSWORD_FILE. The password file must be owned by the operator and mode 0600. Ansible reads the vault password from that file; do not put the password itself in the repository, command arguments or shell history. If encrypted vars files are used, their decryption key is supplied only through this environment-selected password file. Application secrets are environment-backed, not stored in committed vault files.

Example controller setup (populate values from your approved secret manager; do not commit this file):

    export OBSTACK_ALERTMANAGER_WEBHOOK_URL='https://your-approved-alert-webhook.example/path'
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

## Pending release metadata

Prepare versioned release notes on the Ansible controller before opening the
release PR. This playbook does not connect to production hosts or publish a
release:

```bash
ANSIBLE_CONFIG="$PWD/ansible/ansible.cfg" ansible-playbook \
  ansible/playbooks/prepare-release-metadata.yml \
  -e '{"release_version":"v1.3.0","obstack_release_notes":{"Added":["Describe the new capability."],"Fixed":["Describe the fix."]}}'
```

The playbook uses the `Africa/Lagos` date, accepts only Added, Changed,
Deprecated, Removed, Fixed and Security categories, validates meaningful
content with `scripts/release_changelog.py`, and refuses to overwrite existing
metadata. Review and commit the generated file through a normal PR. See
[versioning and changelog policy](../docs/versioning-and-changelog.md).

## Central host: first-time provisioning

The central host playbook provisions Ubuntu 24.04 ARM64, installs baseline security packages and Docker, creates the private ObStack CA and central server certificate, deploys the Compose stack and checks service readiness. When OBSTACK_ALERTMANAGER_WEBHOOK_URL is supplied, Ansible renders a protected Alertmanager config to enable webhook delivery of firing and resolved alerts; otherwise the default receiver is a sink and no notifications are delivered. The URL must be HTTPS and is stored in the generated config with root ownership and 0640 permissions for the dedicated container group.

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

## Central-host SSH, command auditing and TLS renewal

The central playbook applies the following controls after checking that the
active Ansible login already has a non-empty `authorized_keys` file:

- SSH public-key authentication only; password and keyboard-interactive
  authentication disabled, root login denied, and forwarding disabled.
- SSH configuration is syntax-checked before the daemon is reloaded. Keep the
  current SSH session open and verify a second key-based session before
  closing it. Supply the verified administrator CIDR before UFW is enabled.
- `auditd` records process execution syscalls (`execve`/`execveat`) with
  arguments in `/var/log/audit/audit.log`, and watches SSH/sudo/audit policy
  changes. Query with `ausearch -k obstack-command-exec`.
- Sudo command invocations are separately recorded in
  `/var/log/sudo/commands.log`. Both log locations are root-controlled.
  Audit records are local to this EC2 instance; they are not tamper-proof
  against a root compromise and are not yet forwarded off-host. Shell built-ins
  that do not execute a process are not individually captured by execve audit.
- A weekly persistent systemd timer checks the central leaf certificate and
  renews it when it has 30 days or less remaining, verifies the chain/key, then
  tests and reloads the Docker Nginx service. Failed renewal is visible in
  `journalctl -u obstack-cert-renew.service`; the previous certificate is
  restored if Nginx rejects the new one. The private CA is not automatically
  rotated; CA expiry within 90 days raises a failure requiring planned CA
  rotation and renewed trust distribution.

Useful checks:

```bash
sudo sshd -t
sudo sshd -T | grep -E 'passwordauthentication|permitrootlogin|pubkeyauthentication|authenticationmethods'
sudo systemctl status auditd obstack-cert-renew.timer
sudo ausearch -k obstack-command-exec --start today
sudo tail -n 50 /var/log/sudo/commands.log
sudo journalctl -u obstack-cert-renew.service
sudo systemctl list-timers obstack-cert-renew.timer
```

This config is repository automation only until the explicitly gated central
Ansible playbook is run during an approved maintenance window. Keep a recovery
path through the EC2 console/SSM before changing SSH authentication policy.

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

The playbook never copies CA or central TLS private keys. Alloy onboarding defaults to preserve and does not install, restart, or rewire an existing container. Its staged config has no log source, and staged files do not prove host metrics are collected. Remote log and host-monitoring registration methods are disabled pending a reviewed source and privilege design. Never expose a Docker socket over TCP or treat a read-only socket mount as a security boundary. Before any separately approved adoption, discover the container UID/GID and protect staged password files; never make them world-readable.

## Central validation

After the hub is active, CA is distributed and Nginx is bound to the WireGuard IP, run:

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/validate-central.yml

This read-only validation checks Compose rendering, services, readiness, Prometheus remote-write receiver, TLS trust and authentication behavior. Secret-bearing tasks retain no_log=true.


## Automated CIDR overlap discovery (read-only)

See [the CIDR preflight guide](../docs/network-cidr-overlap-preflight.md). The playbook queries AWS VPC/subnet CIDRs with the AWS CLI and collects IPv4 routes and Docker IPAM ranges from hosts in the inventory `wireguard` group. AWS CLI credentials must be available on the Ansible controller with read-only `ec2:DescribeVpcs` and `ec2:DescribeSubnets` access. Home/office VPN CIDRs are explicit operator inputs, not inferred.

Example (replace every placeholder with approved/verified values):

```bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/cidr-overlap-discovery.yml \\
  -e '{"obstack_aws_region":"YOUR_AWS_REGION","obstack_approved_vpc_cidr":"YOUR_APPROVED_VPC_CIDR","obstack_home_office_vpn_cidrs":["YOUR_HOME_VPN_CIDR","YOUR_OFFICE_VPN_CIDR"],"obstack_candidate_overlay_cidrs":["10.77.0.0/24","10.240.0.0/24","172.30.240.0/24","192.168.240.0/24"]}'
```

Discovery creates private temporary network records under `ansible/tmp/network-discovery`; remove these after use. It is read-only and does not deploy WireGuard. The candidate must be approved by the network owner before any inventory edit or mutating playbook execution.
