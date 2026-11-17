#!/usr/bin/env python3
"""Validate registrations and generate deterministic Prometheus file-SD/rules."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
APPLICATIONS = ROOT / "applications"
GENERATED = ROOT / "prometheus" / "file_sd"
SCHEMA = json.loads((APPLICATIONS / "schema.json").read_text())
POLICY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "approved_wireguard_cidr", "approved_inventory_hosts"],
    "properties": {
        "schema_version": {"const": 1},
        "approved_wireguard_cidr": {"type": ["string", "null"]},
        "approved_inventory_hosts": {
            "type": "array", "uniqueItems": True,
            "items": {"type": "string", "pattern": "^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9])?(?:\\.[A-Za-z0-9](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9])?)*$"},
        },
    },
}
Draft202012Validator.check_schema(SCHEMA)
PORT_PATTERN = re.compile(r"^[1-9][0-9]{0,4}$")
IPV4_TARGET = re.compile(r"^([^:\[\]]+):([0-9]+)$")
IPV6_TARGET = re.compile(r"^\[([^\[\]]+)\]:([0-9]+)$")
RFC1918_NETWORKS = tuple(ipaddress.ip_network(value) for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
IPV6_UNIQUE_LOCAL = ipaddress.ip_network("fd00::/8")
INVENTORY_HOST_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9_-]{0,61}[A-Za-z0-9])?)*$"
)


def _schema_errors(data: object, source: Path) -> list[str]:
    name = data.get("application", source.stem) if isinstance(data, dict) else source.stem
    errors = []
    for error in Draft202012Validator(SCHEMA).iter_errors(data):
        field = ".".join(str(item) for item in error.absolute_path) or "$"
        errors.append(f"application {name}: {field}: {error.message}")
    return errors


def _mapping(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def parse_approved_network(value: object) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network | None, str | None]:
    if value is None:
        return None, None
    if not isinstance(value, str) or not value:
        return None, "applications/policy.yml: approved_wireguard_cidr must be a CIDR string or null"
    try:
        network = ipaddress.ip_network(value, strict=True)
    except ValueError as exc:
        return None, f"applications/policy.yml: invalid approved_wireguard_cidr {value!r}: {exc}"
    start, end = network.network_address, network.broadcast_address
    special = lambda address: (
        address.is_loopback or address.is_link_local or address.is_multicast
        or address.is_unspecified or address.is_reserved
    )
    private_pools = RFC1918_NETWORKS if network.version == 4 else (IPV6_UNIQUE_LOCAL,)
    if (
        not network.is_private or network.is_global or special(start) or special(end)
        or not any(network.subnet_of(pool) for pool in private_pools)
    ):
        return None, "applications/policy.yml: approved_wireguard_cidr must be within RFC1918 private IPv4 or IPv6 unique-local space"
    return network, None


def parse_metrics_target(value: object) -> tuple[str | None, str | None]:
    """Accept only an unambiguous literal IP address with an explicit port."""
    if not isinstance(value, str) or not value or value != value.strip():
        return None, "target_address must be a literal IP address and port"
    match = IPV6_TARGET.fullmatch(value)
    if match:
        host_text, port_text = match.groups()
        try:
            address = ipaddress.IPv6Address(host_text)
        except ValueError:
            return None, "target_address contains an invalid IPv6 address"
        if address.ipv4_mapped is not None or address.scope_id is not None:
            return None, "target_address must not use IPv4-mapped or scoped IPv6 notation"
    else:
        match = IPV4_TARGET.fullmatch(value)
        if not match:
            return None, "target_address must use IPv4:port or [IPv6]:port; hostnames are not allowed"
        host_text, port_text = match.groups()
        try:
            address = ipaddress.IPv4Address(host_text)
        except ValueError:
            return None, "target_address contains an invalid IPv4 address; hostnames are not allowed"
    if not PORT_PATTERN.fullmatch(port_text):
        return None, "target_address port must be canonical decimal from 1 through 65535"
    port = int(port_text)
    if port > 65535:
        return None, "target_address port must be from 1 through 65535"
    if (
        not address.is_private or address.is_global or address.is_loopback
        or address.is_link_local or address.is_multicast or address.is_unspecified
        or address.is_reserved
    ):
        return None, "target_address must be an ordinary private, non-special IP address"
    private_pools = RFC1918_NETWORKS if address.version == 4 else (IPV6_UNIQUE_LOCAL,)
    if not any(address in pool for pool in private_pools):
        return None, "target_address must be within RFC1918 private IPv4 or IPv6 unique-local space"
    normalized = f"[{address.compressed}]:{port}" if address.version == 6 else f"{address}:{port}"
    return normalized, None


def _validate_source_reference(repository: str, value: str | None, app: str, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, str):
        return []  # The JSON Schema error is more actionable for this type mismatch.
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "" in path.parts:
        return [f"application {app}: {field} must be a safe repository-relative path"]
    if repository == "obstack" and not (ROOT / Path(*path.parts)).is_file():
        return [f"application {app}: {field} references missing ObStack file {value}"]
    return []


def validate_registration(
    data: object,
    source: Path,
    approved_network: ipaddress.IPv4Network | ipaddress.IPv6Network | None = None,
    policy_error: str | None = None,
    approved_inventory_hosts: set[str] | None = None,
) -> list[str]:
    errors = _schema_errors(data, source)
    if not isinstance(data, dict):
        return errors
    app = data.get("application", source.stem)
    if app != source.stem:
        errors.append(f"application {app}: application: filename must be {app}.yml")
    inventory_host = data.get("inventory_host")
    if isinstance(inventory_host, str) and INVENTORY_HOST_PATTERN.fullmatch(inventory_host):
        try:
            ipaddress.ip_address(inventory_host)
        except ValueError:
            pass
        else:
            errors.append(f"application {app}: inventory_host must be an inventory name, not an IP address")
    dashboard = _mapping(data.get("dashboards"))
    dashboard_files = dashboard.get("source_files", [])
    for reference in dashboard_files if isinstance(dashboard_files, list) else []:
        errors.extend(_validate_source_reference(dashboard.get("source_repository", ""), reference, app, "dashboards.source_files"))
    alerts = _mapping(data.get("alerts"))
    errors.extend(_validate_source_reference(alerts.get("source_repository", ""), alerts.get("source_file"), app, "alerts.source_file"))

    metrics = _mapping(data.get("metrics"))
    target = metrics.get("target_address")
    if data.get("enabled"):
        if policy_error:
            errors.append(f"application {app}: onboarding: {policy_error}")
        elif approved_network is None:
            errors.append(f"application {app}: onboarding: applications/policy.yml must set approved_wireguard_cidr before enabling applications")
        if approved_inventory_hosts is None:
            errors.append(f"application {app}: onboarding: approved inventory host list is not configured")
        elif data.get("inventory_host") not in approved_inventory_hosts:
            errors.append(f"application {app}: inventory_host is not in applications/policy.yml approved_inventory_hosts")
    if target is not None:
        normalized, target_error = parse_metrics_target(target)
        if target_error:
            errors.append(f"application {app}: metrics.target_address: {target_error}")
        elif policy_error:
            errors.append(f"application {app}: metrics.target_address: {policy_error}")
        elif approved_network is None:
            errors.append(f"application {app}: metrics.target_address: approved WireGuard CIDR is not configured")
        else:
            address_text = normalized.rsplit(":", 1)[0].strip("[]")
            address = ipaddress.ip_address(address_text)
            if address.version != approved_network.version or address not in approved_network:
                errors.append(
                    f"application {app}: metrics.target_address {normalized} is outside approved WireGuard network {approved_network}"
                )
    health = _mapping(data.get("health"))
    if health.get("enabled") and isinstance(health.get("url"), str):
        try:
            parsed = urlsplit(health["url"])
        except ValueError:
            errors.append(f"application {app}: health.url is malformed")
            return errors
        if (
            parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment
        ):
            errors.append(f"application {app}: health.url must be HTTPS without credentials, query parameters, or fragments")
        elif health.get("enabled"):
            try:
                probe_address = ipaddress.ip_address(parsed.hostname)
            except ValueError:
                errors.append(f"application {app}: health.url host must be a literal private IP address; hostnames are not allowed")
            else:
                private_pools = RFC1918_NETWORKS if probe_address.version == 4 else (IPV6_UNIQUE_LOCAL,)
                if (
                    not probe_address.is_private or probe_address.is_global or probe_address.is_loopback
                    or probe_address.is_link_local or probe_address.is_multicast or probe_address.is_unspecified
                    or probe_address.is_reserved
                    or not any(probe_address in pool for pool in private_pools)
                ):
                    errors.append(f"application {app}: health.url host must be an ordinary RFC1918 or IPv6 unique-local address")
                elif policy_error:
                    errors.append(f"application {app}: health.url: {policy_error}")
                elif approved_network is None:
                    errors.append(f"application {app}: health.url: approved WireGuard CIDR is not configured")
                elif probe_address.version != approved_network.version or probe_address not in approved_network:
                    errors.append(f"application {app}: health.url host {probe_address} is outside approved WireGuard network {approved_network}")
        try:
            if parsed.port is not None and not 1 <= parsed.port <= 65535:
                raise ValueError
        except ValueError:
            errors.append(f"application {app}: health.url contains an invalid port")
    return errors


def validate_registrations(
    registrations: list[tuple[dict, Path]],
    approved_network: ipaddress.IPv4Network | ipaddress.IPv6Network | None,
    policy_error: str | None,
    approved_inventory_hosts: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    app_owners: dict[str, str] = {}
    target_owners: dict[str, str] = {}
    probe_owners: dict[str, str] = {}
    for data, source in registrations:
        errors.extend(validate_registration(data, source, approved_network, policy_error, approved_inventory_hosts))
        app = data.get("application", source.stem)
        if isinstance(app, str):
            if app in app_owners:
                errors.append(f"application {app}: duplicate identifier also registered in {app_owners[app]}")
            app_owners[app] = source.name
        if not data.get("enabled"):
            continue
        metrics = _mapping(data.get("metrics"))
        if metrics.get("enabled") and metrics.get("target_address"):
            normalized, target_error = parse_metrics_target(metrics["target_address"])
            if normalized:
                if normalized in target_owners:
                    errors.append(f"application {app}: duplicate scrape target {normalized} also used by {target_owners[normalized]}")
                target_owners[normalized] = app
        health = _mapping(data.get("health"))
        if health.get("enabled") and _mapping(data.get("blackbox")).get("enabled") and isinstance(health.get("url"), str):
            if health["url"] in probe_owners:
                errors.append(f"application {app}: duplicate health target also used by {probe_owners[health['url']]}")
            probe_owners[health["url"]] = app
    return errors


def generated_targets(registrations: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    metrics, probes, rules = [], [], []
    for app in registrations:
        if not app["enabled"]:
            continue
        labels = {
            "application": app["application"],
            "environment": app["environment"],
            "host": app["inventory_host"],
        }
        if app["metrics"]["enabled"]:
            metrics.append({
                "targets": [parse_metrics_target(app["metrics"]["target_address"])[0]],
                "labels": {**labels, "__metrics_path__": app["metrics"]["path"]},
            })
            matcher = ",".join(f'{key}="{value}"' for key, value in labels.items())
            rules.append({
                "alert": "ApplicationMetricsTargetMissing",
                "expr": f'absent(up{{job="application-metrics",{matcher}}})',
                "for": "5m",
                "labels": {**labels, "severity": "critical", "category": "telemetry"},
                "annotations": {
                    "summary": "Registered application metrics target disappeared",
                    "description": f"Prometheus has no scrape series for {app['application']} on {app['inventory_host']}. Check registration generation and the private WireGuard path.",
                },
            })
        if app["health"]["enabled"] and app["blackbox"]["enabled"]:
            probes.append({"targets": [app["health"]["url"]], "labels": labels})
            matcher = ",".join(f'{key}="{value}"' for key, value in labels.items())
            rules.append({
                "alert": "ApplicationHealthProbeTargetMissing",
                "expr": f'absent(probe_success{{job="blackbox",{matcher}}})',
                "for": "5m",
                "labels": {**labels, "severity": "critical", "category": "telemetry"},
                "annotations": {
                    "summary": "Registered application health probe disappeared",
                    "description": f"Prometheus has no health probe series for {app['application']} on {app['inventory_host']}. Check generated targets and Blackbox availability.",
                },
            })
    order = lambda item: (item["labels"]["application"], item["labels"]["environment"], item["labels"]["host"])
    return sorted(metrics, key=order), sorted(probes, key=order), sorted(rules, key=lambda item: (item["alert"], item["labels"]["application"]))


def write_or_check(path: Path, value: object, check: bool) -> bool:
    content = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if check:
        if not path.exists() or path.read_text() != content:
            print(f"Generated file is stale: {path.relative_to(ROOT)}", file=sys.stderr)
            return False
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"Wrote {path.relative_to(ROOT)}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-generated", action="store_true", help="fail if committed generated files are stale")
    parser.add_argument("--policy", type=Path, default=APPLICATIONS / "policy.yml", help="central approved-network policy")
    args = parser.parse_args()
    try:
        policy_data = yaml.safe_load(args.policy.read_text())
    except (OSError, yaml.YAMLError) as exc:
        print(f"Cannot load network policy {args.policy}: {exc}", file=sys.stderr)
        return 1
    policy_errors = [f"applications/policy.yml: {error.message}" for error in Draft202012Validator(POLICY_SCHEMA).iter_errors(policy_data)]
    approved_network, network_error = parse_approved_network(policy_data.get("approved_wireguard_cidr") if isinstance(policy_data, dict) else None)
    host_values = policy_data.get("approved_inventory_hosts") if isinstance(policy_data, dict) else None
    approved_inventory_hosts = set(host_values) if isinstance(host_values, list) and all(isinstance(host, str) for host in host_values) else None
    if network_error:
        policy_errors.append(network_error)

    files = sorted(
        path for pattern in ("*.yml", "*.yaml")
        for path in APPLICATIONS.glob(pattern)
        if path.name != "policy.yml"
    )
    errors: list[str] = policy_errors[:]
    registrations: list[dict] = []
    registration_sources: list[tuple[dict, Path]] = []
    for path in files:
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            errors.append(f"{path}: invalid YAML: {exc}")
            continue
        if isinstance(data, dict):
            registrations.append(data)
            registration_sources.append((data, path))
            print(f"Validated registration structure: {path.relative_to(ROOT)}")
            dashboards = _mapping(data.get("dashboards"))
            if dashboards.get("source_repository") == "application":
                references = dashboards.get("source_files", [])
                for reference in references if isinstance(references, list) else []:
                    print(f"External dashboard source (not checked out here): {data.get('application')}:{reference}")
            alerts = _mapping(data.get("alerts"))
            if alerts.get("source_repository") == "application" and isinstance(alerts.get("source_file"), str):
                print(f"External alert source (not checked out here): {data.get('application')}:{alerts['source_file']}")
        else:
            errors.append(f"application {path.stem}: registration file must contain a YAML mapping")
    errors.extend(validate_registrations(registration_sources, approved_network, network_error, approved_inventory_hosts))
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    metrics, probes, rules = generated_targets(registrations)
    outputs = (
        (GENERATED / "application-metrics.json", metrics),
        (GENERATED / "application-health.json", probes),
        (ROOT / "prometheus" / "rules" / "generated-applications.yml", {"groups": [{"name": "registered-applications", "rules": rules}]}),
    )
    if args.check_generated:
        rendered_rules = yaml.safe_dump(outputs[2][1], sort_keys=False, default_flow_style=False)
        rules_ok = outputs[2][0].exists() and outputs[2][0].read_text() == rendered_rules
        if not rules_ok:
            print("Generated file is stale: prometheus/rules/generated-applications.yml", file=sys.stderr)
        ok = write_or_check(outputs[0][0], outputs[0][1], True) and write_or_check(outputs[1][0], outputs[1][1], True) and rules_ok
    else:
        ok = write_or_check(outputs[0][0], outputs[0][1], False) and write_or_check(outputs[1][0], outputs[1][1], False)
        outputs[2][0].write_text(yaml.safe_dump(outputs[2][1], sort_keys=False, default_flow_style=False))
        print(f"Wrote {outputs[2][0].relative_to(ROOT)}")
    if args.check_generated and ok:
        print("Generated target and alert files are current")
    if not args.check_generated:
        print(f"Applications: {len(registrations)}; enabled: {sum(bool(a['enabled']) for a in registrations)}; metrics: {len(metrics)}; probes: {len(probes)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
