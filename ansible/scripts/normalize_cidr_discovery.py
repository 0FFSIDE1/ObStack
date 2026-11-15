#!/usr/bin/env python3
"""Normalize read-only AWS and Ansible network discovery inputs for ObStack."""
import argparse
import ipaddress
import json
from pathlib import Path


def add_network(records, name, cidr, source):
    if not cidr:
        return
    net = ipaddress.ip_network(cidr, strict=False)
    if net.version == 4:
        records.append({"name": name, "cidr": str(net), "source": source})


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--vpcs", required=True, type=Path)
    p.add_argument("--subnets", required=True, type=Path)
    p.add_argument("--hosts-dir", required=True, type=Path)
    p.add_argument("--approved-vpc-cidr", required=True)
    p.add_argument("--vpn-cidr", action="append", default=[])
    p.add_argument("--candidate", action="append", default=[])
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()

    records = []
    add_network(records, "Approved AWS VPC CIDR", args.approved_vpc_cidr, "approved AWS input")
    vpcs = json.loads(args.vpcs.read_text())
    for vpc in vpcs.get("Vpcs", []):
        vid = vpc.get("VpcId", "unknown-vpc")
        add_network(records, f"AWS VPC {vid} primary", vpc.get("CidrBlock"), "AWS VPC")
        for assoc in vpc.get("CidrBlockAssociationSet", []):
            add_network(records, f"AWS VPC {vid} association", assoc.get("CidrBlock"), "AWS VPC association")
    subnets = json.loads(args.subnets.read_text())
    for subnet in subnets.get("Subnets", []):
        add_network(records, f"AWS subnet {subnet.get('SubnetId', 'unknown')}", subnet.get("CidrBlock"), "AWS subnet")
    for index, cidr in enumerate(args.vpn_cidr, 1):
        add_network(records, f"Home/office VPN {index}", cidr, "operator supplied VPN")

    # Host discovery JSON files contain route text and Docker network inspect JSON.
    for path in sorted(args.hosts_dir.glob("*.json")):
        host = json.loads(path.read_text())
        hostname = host.get("host", path.stem)
        route_text = host.get("routes", "")
        # Only connected prefixes are included; via routes are not the local network.
        for line in route_text.splitlines():
            if " via " in f" {line} ":
                continue
            for token in line.split():
                if "/" in token:
                    try:
                        net = ipaddress.ip_network(token, strict=False)
                    except ValueError:
                        continue
                    if net.version == 4 and token != "default":
                        add_network(records, f"{hostname} route", str(net), "host route")
                        break
        docker_text = host.get("docker_networks", "")
        if docker_text.strip():
            try:
                networks = json.loads(docker_text)
            except json.JSONDecodeError:
                networks = []
            for docker_net in networks if isinstance(networks, list) else []:
                for config in docker_net.get("IPAM", {}).get("Config", []) or []:
                    add_network(records, f"{hostname} Docker {docker_net.get('Name', 'network')}", config.get("Subnet"), "Docker network")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"networks": records, "candidates": args.candidate}, indent=2) + "\n")
    print(f"Normalized {len(records)} IPv4 network records into {args.output}")


if __name__ == "__main__":
    main()
