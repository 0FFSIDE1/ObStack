# Ansible automation

The inventory example is intentionally incomplete and contains placeholders. Copy it to `inventory/hosts.yml` only after replacing every placeholder with verified host data.

Start with the read-only preflight:

```bash
ansible-playbook playbooks/preflight.yml --check --diff
```

The preflight gathers facts and asserts Ubuntu 24.04 plus ARM64/AMD64 architecture. It does not install packages or change hosts.

No mutating playbooks are included yet. WireGuard peer keys, passwords and tokens must be supplied through Ansible Vault or an approved secret manager; never commit them to inventory or Git. Production playbooks require a separate change review and explicit authorization.
