# Ansible automation

The inventory example is intentionally incomplete. Copy it to inventory/hosts.yml only after replacing placeholders with verified host data and checking all address ranges.

## Central host: first-time provisioning

The central host playbook provisions a clean Ubuntu 24.04 ARM64 EC2 instance. It installs baseline security packages, configures conservative SSH hardening, UFW, fail2ban and unattended security updates, installs Docker Engine from Docker's official apt repository, generates a private ObStack CA and a central server certificate for the approved WireGuard IP, deploys the Compose stack including a hardened Docker Nginx TLS reverse proxy, starts it and checks Nginx, Prometheus, Grafana, Loki, Alertmanager and Blackbox readiness.

Before running:
- Ensure SSH key-based access works and keep the current SSH session open during the first run. Password authentication remains enabled by default; disable it only after key-only access has been verified.
- Confirm the central host inventory address, SSH port, ARM64 architecture, approved WireGuard IP and administrator public IPv4 CIDR.
- Review the VPC/subnet, security group and host firewall rules. The playbook restricts SSH to the approved administrator CIDR, allows UDP 51820 for WireGuard, and allows HTTPS only on wg0. Do not enable UFW until the SSH path and provider firewall are understood.
- Set the repository root variable to the absolute path of the checked-out ObStack repository on the Ansible controller.
- Put Grafana administrator credentials and a unique 24+ character password in Ansible Vault. Never put secrets in plaintext inventory or Git.
- For every enrolled host in the monitored group, put separate unique metrics and logs passwords (24+ characters) in Ansible Vault. Usernames are generated deterministically from the Ansible inventory hostname; do not override them. Central provisioning writes bcrypt htpasswd entries; secrets never enter the repository.
- Install controller collections with: ansible-galaxy collection install -r ansible/requirements.yml.
- The host timezone defaults to Africa/Lagos; chrony maintains clock synchronization. Container services retain their default UTC time unless deliberately configured otherwise.
- Nginx is published on loopback port 443 by default, so it is not remotely accessible during bootstrap. After the WireGuard hub is configured and verified, set the Nginx bind address to the hub's WireGuard IPv4 address and rerun the central playbook. Keep AWS security-group TCP 443 closed to the public internet.
- Check free disk space. The current 14 GB pilot disk is tight; this playbook does not resize EBS or guarantee requested retention.

Syntax-check and inspect first:

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/central.yml --syntax-check
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/central.yml --list-tasks
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/central.yml --check --diff --ask-vault-pass

After approval and during a maintenance window:

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/central.yml --ask-vault-pass -e obstack_apply=true

The central playbook is intentionally gated by obstack_apply=true. It does not create AWS resources, associate the Elastic IP, alter AWS security groups, or configure WireGuard peers. Nginx runs in Docker and proxies HTTPS to Grafana; it is loopback-only during bootstrap. Once WireGuard is configured, bind it to the WireGuard IP and keep public TCP 443 closed. Prometheus, Loki and other backend ports remain loopback-only. The private CA key and server key stay root-only on the central host; back them up securely offline before replacing the instance. The generated certificate SAN is the WireGuard IP, so remote agents must connect using that address and trust the distributed /etc/obstack/pki/ca.crt.

SSH password authentication is not disabled automatically to avoid locking out a first-time host. Validate key-only SSH in a separate session, then set the protected host variable to no and rerun. Review the generated SSH drop-in and UFW rules before the first production run.

## WireGuard hub and spokes

The wireguard playbook configures exactly one observability hub and the currently enrolled monitored spokes. It validates unique spoke overlay IPs, unique /32 spoke assignments, per-host key material and hub endpoint data before writing the root-only wg0.conf. Spokes initiate outbound UDP 51820 connections and use PersistentKeepalive=25; the hub allows only each spoke's /32. No IP forwarding, NAT, default route or remote-to-remote routing is enabled.

The 10.77.0.0/24 value remains a provisional example, not an approved network. Do not run WireGuard provisioning until the VPC CIDR, office/home/existing VPN routes, remote host routes and Docker bridge ranges have been checked, and the Elastic IP, peer public addresses, UDP 51820 security-group source allowlist, SSH rollback and maintenance window are verified. Private keys must be stored in Ansible Vault; never commit them.

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/wireguard.yml --syntax-check
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/wireguard.yml --list-tasks
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/wireguard.yml --ask-vault-pass -e obstack_apply=true

## Certificate distribution and Alloy

After central provisioning has generated /etc/obstack/pki/ca.crt, distribute only the public CA certificate:

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/distribute-ca.yml --syntax-check
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/distribute-ca.yml --ask-vault-pass -e obstack_apply=true

The playbook reads the CA certificate from the sole observability host and copies it to /etc/obstack/pki/ca.crt on enrolled spokes. It never copies the CA private key or central TLS private key. Mount the host certificate read-only into the existing Alloy container at /etc/ssl/certs/obstack-ca.crt.

Run read-only discovery before onboarding:

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/preflight.yml
    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/discover-alloy.yml

The Alloy role defaults to preserve. It does not install a duplicate Alloy container or stop/restart an existing container. Run discovery, identify each container's Compose owner and config/data mounts, back up the existing config, then explicitly set the host's existing Alloy policy to adopt.

Adoption stages a non-secret config file and root-only password files; it does not automatically mount those files into a running container or restart it. Before mounting the password files, discover the existing Alloy container's UID/GID and grant read-only access through a dedicated group or an equivalent least-privilege mechanism. Do not make password files world-readable. A reviewed host-specific Compose change must mount:
- The host Alloy config file at the container's Alloy config path.
- The metrics and logs password files as /run/secrets/metrics_password and /run/secrets/logs_password.
- /etc/obstack/pki/ca.crt as /etc/ssl/certs/obstack-ca.crt.
- /proc, /sys and host rootfs as read-only paths as appropriate.

Log collection sources must be selected after checking whether the existing container has Docker socket, journald or file access. The adoption role stages files only and deliberately does not restart or rewire a running container.

## Central validation

After the hub is active, the CA is distributed and Nginx is bound to the WireGuard IP, run the read-only central validation:

    ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/validate-central.yml --ask-vault-pass

It checks Compose rendering, running services, all service health endpoints, the Prometheus remote-write receiver flag, TLS trust, and that both ingestion routes reject unauthenticated requests and accept a known enrolled host's credentials. It does not change services.

Credentials and private keys belong in Ansible Vault. Never commit secrets, render them in CI, or use debug tasks to print them. Mutating playbooks require obstack_apply=true and separate explicit production approval.
