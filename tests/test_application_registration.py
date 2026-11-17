import copy
import ipaddress
import unittest
from pathlib import Path

import yaml

from scripts.validate_applications import (
    generated_targets,
    parse_approved_network,
    parse_metrics_target,
    validate_registration,
    validate_registrations,
)


ROOT = Path(__file__).resolve().parents[1]
APPROVED = ipaddress.ip_network("10.88.0.0/24")


class ApplicationRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ensams = yaml.safe_load((ROOT / "applications/ensams.yml").read_text())

    def enabled_app(self, name="ensams", target="10.88.0.12:18082"):
        app = copy.deepcopy(self.ensams)
        app.update(schema_version=2, application=name, environment="production", inventory_host=f"{name}-prod-01", enabled=True)
        app["metrics"].update(enabled=True, target_address=target)
        return app

    def check_app(self, app, network=APPROVED, inventory_hosts=None):
        if inventory_hosts is None:
            host = app.get("inventory_host")
            inventory_hosts = {host} if isinstance(host, str) else set()
        return validate_registration(
            app,
            ROOT / f"applications/{app.get('application', 'invalid')}.yml",
            network,
            approved_inventory_hosts=inventory_hosts,
        )

    def test_disabled_ensams_validates_without_network_values(self):
        self.assertEqual(validate_registration(self.ensams, ROOT / "applications/ensams.yml"), [])
        self.assertEqual(generated_targets([self.ensams]), ([], [], []))

    def test_enabled_application_requires_network_policy(self):
        errors = self.check_app(self.enabled_app(), network=None)
        self.assertTrue(any("approved_wireguard_cidr" in error for error in errors))

    def test_enabled_application_inventory_host_must_be_centrally_approved(self):
        errors = self.check_app(self.enabled_app(), inventory_hosts={"other-prod-01"})
        self.assertTrue(any("not in applications/policy.yml approved_inventory_hosts" in error for error in errors))

    def test_any_enabled_application_requires_network_policy(self):
        app = self.enabled_app()
        app["metrics"].update(enabled=False, target_address=None)
        app["health"].update(enabled=True, url="https://ensams.example.test/up")
        app["blackbox"]["enabled"] = True
        errors = self.check_app(app, network=None)
        self.assertTrue(any("onboarding" in error and "approved_wireguard_cidr" in error for error in errors))

    def test_approved_private_wireguard_target_is_accepted(self):
        app = self.enabled_app()
        self.assertEqual(self.check_app(app), [])
        metrics, probes, rules = generated_targets([app])
        self.assertEqual(metrics[0]["targets"], ["10.88.0.12:18082"])
        self.assertEqual(metrics[0]["labels"]["application"], "ensams")
        self.assertEqual(probes, [])
        self.assertEqual(rules[0]["alert"], "ApplicationMetricsTargetMissing")

    def test_health_target_generates_disappearance_rule_and_low_cardinality_labels(self):
        app = self.enabled_app()
        app["health"].update(enabled=True, url="https://10.88.0.12/up")
        app["blackbox"]["enabled"] = True
        self.assertEqual(self.check_app(app), [])
        metrics, probes, rules = generated_targets([app])
        self.assertEqual(len(metrics), 1)
        self.assertEqual(probes[0]["labels"], {
            "application": "ensams", "environment": "production", "host": "ensams-prod-01"
        })
        self.assertIn("ApplicationHealthProbeTargetMissing", {rule["alert"] for rule in rules})

    def test_health_target_must_be_a_private_ip_inside_the_approved_network(self):
        for url, expected in (
            ("https://health.ensams.example/up", "hostnames are not allowed"),
            ("https://8.8.8.8/up", "ordinary RFC1918"),
            ("https://10.89.0.12/up", "outside approved WireGuard"),
        ):
            app = self.enabled_app()
            app["health"].update(enabled=True, url=url)
            app["blackbox"]["enabled"] = True
            errors = self.check_app(app)
            self.assertTrue(any(expected in error for error in errors), (url, errors))

    def test_public_ipv4_is_rejected(self):
        self.assert_target_rejected("8.8.8.8:9100", "ordinary private")

    def test_public_ipv6_is_rejected(self):
        self.assert_target_rejected("[2606:4700:4700::1111]:9100", "ordinary private")

    def test_loopback_is_rejected(self):
        self.assert_target_rejected("127.0.0.1:9100", "ordinary private")

    def test_link_local_is_rejected(self):
        self.assert_target_rejected("169.254.1.5:9100", "ordinary private")

    def test_multicast_unspecified_and_reserved_addresses_are_rejected(self):
        for target in ("224.0.0.1:9100", "0.0.0.0:9100", "192.0.2.1:9100", "100.64.0.1:9100"):
            normalized, error = parse_metrics_target(target)
            self.assertIsNone(normalized, target)
            self.assertTrue(error, target)
            app = self.enabled_app(target=target)
            errors = self.check_app(app)
            self.assertTrue(any("metrics.target_address" in item for item in errors), target)

    def test_target_outside_approved_cidr_is_rejected(self):
        app = self.enabled_app(target="10.89.0.12:18082")
        errors = self.check_app(app)
        self.assertTrue(any("outside approved WireGuard" in error for error in errors))

    def test_invalid_port_is_rejected(self):
        for target in ("10.88.0.12:0", "10.88.0.12:65536", "10.88.0.12:08082"):
            self.assert_target_rejected(target, "port")

    def test_invalid_and_hostname_targets_are_rejected(self):
        for target in ("ensams.internal:18082", "10.88.0.12", "10.88.0.12:80/path", "010.88.0.12:80", "10.88.0.12:1:2"):
            self.assert_target_rejected(target, "target_address")

    def test_ipv6_requires_brackets_and_can_be_scoped_to_policy(self):
        network = ipaddress.ip_network("fd77:1234::/48")
        app = self.enabled_app(target="[fd77:1234::12]:18082")
        self.assertEqual(self.check_app(app, network=network), [])
        self.assert_target_rejected("fd77:1234::12:18082", "IPv4:port or [IPv6]:port")

    def test_invalid_and_non_private_network_policy_is_rejected(self):
        for cidr in ("10.88.0.1/24", "8.8.8.0/24", "127.0.0.0/8", "fe80::/10", "fc00::/8"):
            network, error = parse_approved_network(cidr)
            self.assertIsNone(network, cidr)
            self.assertTrue(error, cidr)

    def test_unsupported_log_and_host_collection_methods_cannot_be_enabled(self):
        app = self.enabled_app()
        app["logs"].update(enabled=True, method="alloy_docker_agent")
        app["host_monitoring"].update(enabled=True, method="alloy_remote_write")
        errors = self.check_app(app)
        self.assertTrue(any("logs.enabled" in error for error in errors))
        self.assertTrue(any("host_monitoring.enabled" in error for error in errors))

    def test_application_cannot_override_central_network_policy(self):
        app = self.enabled_app()
        app["approved_wireguard_cidr"] = "0.0.0.0/0"
        errors = self.check_app(app)
        self.assertTrue(any("unexpected" in error and "approved_wireguard_cidr" in error for error in errors))

    def test_dynamic_labels_are_rejected_and_inventory_host_cannot_be_an_ip(self):
        app = self.enabled_app()
        app["labels"] = {"request_id": "abc", "email": "user@example.test"}
        errors = self.check_app(app)
        self.assertTrue(any("labels" in error for error in errors))
        app = self.enabled_app()
        app["inventory_host"] = "10.88.0.12"
        self.assertTrue(self.check_app(app))

    def test_external_source_references_are_explicit_and_not_claimed_as_local(self):
        app = copy.deepcopy(self.ensams)
        self.assertEqual(validate_registration(app, ROOT / "applications/ensams.yml"), [])
        app["dashboards"]["source_repository"] = "obstack"
        errors = validate_registration(app, ROOT / "applications/ensams.yml")
        self.assertTrue(any("missing ObStack file" in error for error in errors))

    def test_duplicate_scrape_targets_are_rejected(self):
        first = self.enabled_app("ensams")
        second = self.enabled_app("rabbitlala")
        second["metrics"]["target_address"] = first["metrics"]["target_address"]
        errors = validate_registrations(
            [(first, ROOT / "applications/ensams.yml"), (second, ROOT / "applications/rabbitlala.yml")],
            APPROVED,
            None,
            {"ensams-prod-01", "rabbitlala-prod-01"},
        )
        self.assertTrue(any("duplicate scrape target" in error for error in errors))

    def test_duplicate_application_ids_are_rejected(self):
        first = self.enabled_app("ensams")
        second = self.enabled_app("ensams")
        errors = validate_registrations(
            [(first, ROOT / "applications/ensams.yml"), (second, ROOT / "applications/ensams-copy.yml")],
            APPROVED,
            None,
            {"ensams-prod-01"},
        )
        self.assertTrue(any("duplicate identifier" in error for error in errors))

    def assert_target_rejected(self, target, expected_text):
        normalized, error = parse_metrics_target(target)
        self.assertIsNone(normalized, target)
        self.assertIn(expected_text, error)
        app = self.enabled_app(target=target)
        errors = self.check_app(app)
        self.assertTrue(any("metrics.target_address" in item for item in errors), target)


if __name__ == "__main__":
    unittest.main()
