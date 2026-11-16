#!/usr/bin/env python3
"""Validate application registrations and render deterministic Prometheus file-SD."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
APPLICATIONS = ROOT / "applications"
GENERATED = ROOT / "prometheus" / "file_sd"
SCHEMA = json.loads((APPLICATIONS / "schema.json").read_text())
FORBIDDEN_LABELS = {"user_id", "email", "request_id", "asset_id", "path", "url"}


def validate_registration(data: object, source: Path) -> list[str]:
    errors = [f"{source}:{'.'.join(map(str, error.path)) or '$'}: {error.message}" for error in Draft202012Validator(SCHEMA).iter_errors(data)]
    if not isinstance(data, dict):
        return errors
    name = data.get("application", source.stem)
    if name != source.stem:
        errors.append(f"{source}: filename must be {name}.yml")
    labels = data.get("logs", {}).get("labels", {})
    for label in labels:
        if label.lower() in FORBIDDEN_LABELS or label.lower().endswith(("_id", "_email")):
            errors.append(f"{source}: prohibited or high-cardinality log label {label}")
    if data.get("enabled"):
        for field, value in (("environment", data.get("environment")), ("inventory_host", data.get("inventory_host"))):
            if not value:
                errors.append(f"{source}: enabled registration requires {field}")
        metrics = data.get("metrics", {})
        if metrics.get("enabled") and not metrics.get("target_address"):
            errors.append(f"{source}: enabled metrics require metrics.target_address")
        health = data.get("health", {})
        if health.get("enabled") and not health.get("url"):
            errors.append(f"{source}: enabled health probe requires health.url")
        if metrics.get("target_address"):
            address = metrics["target_address"]
            if any(char in address for char in " /?#") or ":" not in address:
                errors.append(f"{source}: metrics.target_address must be a host:port, not a URL")
            try:
                port = int(address.rsplit(":", 1)[1])
                if not 1 <= port <= 65535:
                    raise ValueError
            except ValueError:
                errors.append(f"{source}: metrics.target_address requires a valid port")
            host = address.rsplit(":", 1)[0]
            if host.startswith("[") and host.endswith("]"):
                host = host[1:-1]
            try:
                ipaddress.ip_address(host)
            except ValueError:
                if not re.fullmatch(r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*", host):
                    errors.append(f"{source}: metrics.target_address host must be a valid IP address or DNS name")
        if health.get("url"):
            parsed = urlparse(health["url"])
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                errors.append(f"{source}: health.url must be HTTPS and must not embed credentials")
    return errors


def generated_targets(registrations: list[dict]) -> tuple[list[dict], list[dict]]:
    metrics, probes = [], []
    for app in registrations:
        if not app["enabled"]:
            continue
        labels = {"service": app["application"], "environment": app["environment"], "host": app["inventory_host"]}
        if app["metrics"]["enabled"]:
            metrics.append({"targets": [app["metrics"]["target_address"]], "labels": {**labels, "__metrics_path__": app["metrics"]["path"]}})
        if app["health"]["enabled"] and app["blackbox"]["enabled"]:
            probes.append({"targets": [app["health"]["url"]], "labels": labels})
    key = lambda item: (item["labels"]["service"], item["labels"]["environment"], item["labels"]["host"])
    return sorted(metrics, key=key), sorted(probes, key=key)


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
    parser.add_argument("--check-generated", action="store_true", help="fail if committed file-SD output is stale")
    args = parser.parse_args()
    files = sorted([*APPLICATIONS.glob("*.yml"), *APPLICATIONS.glob("*.yaml")])
    errors: list[str] = []
    registrations: list[dict] = []
    seen: set[str] = set()
    target_owners: dict[str, str] = {}
    probe_owners: dict[str, str] = {}
    for path in files:
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            errors.append(f"{path}: invalid YAML: {exc}")
            continue
        errors.extend(validate_registration(data, path))
        if not isinstance(data, dict):
            continue
        name = data.get("application")
        if name in seen:
            errors.append(f"{path}: duplicate application {name}")
        seen.add(name)
        if data.get("enabled"):
            target = data.get("metrics", {}).get("target_address")
            if target in target_owners:
                errors.append(f"{path}: duplicate metrics target {target} also used by {target_owners[target]}")
            if target:
                target_owners[target] = name
            logs = data.get("logs", {})
            if logs.get("enabled"):
                for key in ("service", "environment", "host"):
                    if not logs.get("labels", {}).get(key):
                        errors.append(f"{path}: enabled logs require non-empty {key} label")
                if logs.get("labels", {}).get("service") != name:
                    errors.append(f"{path}: logs.labels.service must match application")
                if logs.get("labels", {}).get("environment") != data.get("environment"):
                    errors.append(f"{path}: logs.labels.environment must match environment")
                if logs.get("labels", {}).get("host") != data.get("inventory_host"):
                    errors.append(f"{path}: logs.labels.host must match inventory_host")
            health = data.get("health", {})
            if health.get("enabled") and data.get("blackbox", {}).get("enabled"):
                url = health.get("url")
                if url in probe_owners:
                    errors.append(f"{path}: duplicate health target {url} also used by {probe_owners[url]}")
                if url:
                    probe_owners[url] = name
        registrations.append(data)
        print(f"Validated registration structure: {path.relative_to(ROOT)}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    metrics, probes = generated_targets(registrations)
    outputs = ((GENERATED / "application-metrics.json", metrics), (GENERATED / "application-health.json", probes))
    ok = all(write_or_check(path, value, args.check_generated) for path, value in outputs)
    if args.check_generated and ok:
        print("Generated target files are current")
    if not args.check_generated:
        print(f"Applications: {len(registrations)}; enabled: {sum(bool(a['enabled']) for a in registrations)}; active metrics targets: {len(metrics)}; active probes: {len(probes)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
