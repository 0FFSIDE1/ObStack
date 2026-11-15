# Alloy onboarding

Default policy is preserve. It does not install Alloy, create a duplicate container, stop/restart a container, or overwrite its mounted config.

1. Run playbooks/discover-alloy.yml (read-only).
2. Record image/tag, Compose labels, config and state mounts, network mode and existing collection scope. Never dump container environment variables or secrets.
3. Back up current config and identify its Compose owner.
4. For an approved host, explicitly set obstack_alloy_existing_policy=adopt and provide per-host credentials through Ansible Vault.
5. Review the staged config and container bind mount before a separate approved Compose change.

The starter config forwards host metrics with ObStack external labels (`project`, `environment`, `server`, `service`, `role`, `region`) and defines a Loki writer. Set `project` and `environment` for each host; optionally set `obstack_server_role` and `obstack_region` to override the defaults. It does not yet collect Docker logs or journald; choose log sources only after discovering each host's actual setup. Alloy running in Docker does not prove host metrics/logs are currently collected. The central HTTPS ingress, auth and trusted CA must exist before adoption.
