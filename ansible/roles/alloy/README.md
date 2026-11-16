# Alloy onboarding

Default policy is preserve. It does not install Alloy, create a duplicate container, stop/restart a container, or overwrite its mounted config.

1. Run playbooks/discover-alloy.yml (read-only).
2. Record image/tag, Compose labels, config and state mounts, network mode and existing collection scope. Never dump container environment variables or secrets.
3. Back up current config and identify its Compose owner.
4. For an approved host, explicitly set obstack_alloy_existing_policy=adopt and provide per-host credentials through Ansible Vault.
5. Review the staged config and container bind mount before a separate approved Compose change.

The starter config contains an Alloy Unix exporter/remote-write pipeline and a Loki writer, with identity labels from host inventory. The role only stages this config and secret files; it does not install Alloy, mount host sources, restart a container, or verify ingestion. The Loki writer has no log source. Application registrations therefore reject enabled remote logs and host monitoring until an approved collector/source lifecycle exists. Do not use Docker socket access as a presumed read-only boundary. CI syntax validation is not runtime or privilege validation. The central HTTPS ingress, authentication and trusted CA must exist before a separately approved agent adoption.
