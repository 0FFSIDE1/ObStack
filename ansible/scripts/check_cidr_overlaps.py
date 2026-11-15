#!/usr/bin/env python3
"""Read-only IPv4 CIDR overlap checker for ObStack network discovery.

Input JSON schema:
{
  "networks": [{"name": "AWS VPC", "cidr": "10.0.0.0/16", "source": "AWS"}],
  "candidates": ["10.77.0.0/24", "172.30.240.0/24"]
}
Never changes networking. Candidate selection is advisory and requires operator approval.
"""
import argparse
import ipaddress
import json
import sys


def network(value, name):
    try:
        parsed = ipaddress.ip_network(value, strict=False)
    except ValueError as exc:
        raise ValueError(f"{name}: invalid CIDR {value!r}: {exc}") from exc
    if parsed.version != 4:
        raise ValueError(f"{name}: only IPv4 CIDRs are supported: {value}")
    return parsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", help="normalized discovery JSON file")
    args = parser.parse_args()
    with open(args.input_json, encoding="utf-8") as handle:
        payload = json.load(handle)

    known = []
    for item in payload.get("networks", []):
        if not item.get("cidr"):
            continue
        net = network(item["cidr"], item.get("name", "network"))
        known.append((item.get("name", "unnamed"), item.get("source", "unknown"), net))

    candidates = [network(value, "candidate") for value in payload.get("candidates", [])]
    conflicts = []
    for index, (name, source, net) in enumerate(known):
        for other_name, other_source, other_net in known[index + 1:]:
            if net.overlaps(other_net):
                conflicts.append((name, source, str(net), other_name, other_source, str(other_net)))

    clean, candidate_conflicts = [], []
    for candidate in candidates:
        hits = [(name, source, str(net)) for name, source, net in known if candidate.overlaps(net)]
        if hits:
            candidate_conflicts.append((str(candidate), hits))
        else:
            clean.append(str(candidate))

    print("ObStack CIDR overlap discovery (read-only)")
    print(f"Networks inspected: {len(known)}")
    if conflicts:
        print("\nExisting network overlaps (review; some may be intentional):")
        for a, a_src, a_net, b, b_src, b_net in conflicts:
            print(f"  CONFLICT: {a} [{a_src}] {a_net} overlaps {b} [{b_src}] {b_net}")
    else:
        print("\nNo overlaps found among discovered network records.")

    if candidate_conflicts:
        print("\nCandidate WireGuard CIDRs rejected due to overlap:")
        for cidr, hits in candidate_conflicts:
            print(f"  {cidr} overlaps:")
            for name, source, net in hits:
                print(f"    - {name} [{source}] {net}")
    if clean:
        print("\nNon-overlapping candidate CIDRs (proposal only):")
        for cidr in clean:
            print(f"  AVAILABLE: {cidr}")
        print(f"Suggested first candidate: {clean[0]} (requires human approval)")
    elif candidates:
        print("\nNo candidate CIDR passed. Add reviewed candidates and rerun.")
    else:
        print("\nNo candidates supplied; overlap discovery only.")

    if conflicts or (candidates and not clean):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
