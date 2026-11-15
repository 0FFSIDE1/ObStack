#!/usr/bin/env python3
"""Normalize read-only AWS, host-interface, route and Docker CIDR discovery."""
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
    host_scan_count = 0
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

    host_files = sorted(
        path for path in args.hosts_dir.glob("*.json")
        if path.name not in {"aws-vpcs.json", "aws-subnets.json"}
    )
    for path in host_files:
        host = json.loads(path.read_text())
        hostname = host.get("host", path.stem)
        if not isinstance(host.get("routes"), str) or not isinstance(host.get("addresses"), str):
            raise ValueError(f"{hostname}: missing route or interface-address discovery; refusing incomplete validation")
        host_scan_count += 1

        # Interface addresses expose connected host CIDRs, including secondary addresses.
        for line in host["addresses"].splitlines():
            fields = line.split()
            for field in fields:
                if "/" in field:
                    try:
                        interface = ipaddress.ip_interface(field)
                    except ValueError:
                        continue
                    if interface.version == 4:
                        add_network(records, f"{hostname} interface {fields[1] if len(fields) > 1 else 'unknown'}", str(interface.network), "host interface CIDR")
                        break

        # Inspect the destination prefix (first token) on every route line.
        # Do not skip 'via' routes: routed remote networks also matter for overlap.
        for line in host["routes"].splitlines():
            fields = line.split()
            if not fields or fields[0] == "default" or "/" not in fields[0]:
                continue
            try:
                route_net = ipaddress.ip_network(fields[0], strict=False)
            except ValueError:
                continue
            if route_net.version == 4:
                add_network(records, f"{hostname} route {fields[0]}", str(route_net), "host route")

        docker_text = host.get("docker_networks", "[]")
        if host.get("docker_present") and docker_text.strip():
            try:
                docker_networks = json.loads(docker_text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{hostname}: Docker inspect output is not valid JSON") from exc
            if not isinstance(docker_networks, list):
                raise ValueError(f"{hostname}: Docker inspect output must be a JSON array")
            for docker_net in docker_networks:
                for config in docker_net.get("IPAM", {}).get("Config", []) or []:
                    add_network(records, f"{hostname} Docker {docker_net.get('Name', 'network')}", config.get("Subnet"), "Docker network")

    if host_scan_count < 11:
        raise ValueError(f"Only {host_scan_count} host records found; expected central host plus 10 remote servers")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "networks": records,
        "candidates": args.candidate,
        "discovery": {"host_records": host_scan_count, "expected_host_records": 11},
    }, indent=2) + "\n")
    print(f"Normalized {len(records)} IPv4 network records from {host_scan_count} host records into {args.output}")


if __name__ == "__main__":
    main()
