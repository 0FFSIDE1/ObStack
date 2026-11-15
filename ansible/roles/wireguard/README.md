# WireGuard role

Required per-host values: obstack_wg_address, obstack_wg_private_key and obstack_wg_public_key. Spokes also require obstack_wg_endpoint. The hub requires each spoke's obstack_wg_vpn_ip and obstack_wg_public_key in inventory.

Private keys are read from controller environment variables named OBSTACK_WG_PRIVATE_KEY_<INVENTORY_HOST>. This role does not generate or print keys. It configures only hub/spoke peer routes; it does not enable forwarding or NAT.

The proposed 10.77.0.0/24 overlay is not final. Check AWS VPC, office/home/VPN routes and each host's local/Docker bridge ranges before setting addresses. Validate firewall, security-group allowlists, MTU, SSH rollback and pilot behavior before production.
