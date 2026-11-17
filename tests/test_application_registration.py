import copy
import unittest
from pathlib import Path

import yaml

from scripts.validate_applications import generated_targets, validate_registration


ROOT = Path(__file__).resolve().parents[1]


class ApplicationRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ensams = yaml.safe_load((ROOT / "applications/ensams.yml").read_text())

    def test_unresolved_ensams_registration_is_valid_but_disabled(self):
        self.assertEqual(validate_registration(copy.deepcopy(self.ensams), ROOT / "applications/ensams.yml"), [])
        self.assertEqual(generated_targets([self.ensams]), ([], []))

    def test_enabled_registration_requires_verified_targets_and_identity(self):
        app = copy.deepcopy(self.ensams)
        app["enabled"] = True
        errors = validate_registration(app, ROOT / "applications/ensams.yml")
        self.assertTrue(any("requires environment" in error for error in errors))
        self.assertTrue(any("metrics.target_address" in error for error in errors))
        self.assertTrue(any("requires health.url" in error for error in errors))

    def test_enabled_registration_generates_labeled_metrics_and_health_targets(self):
        app = copy.deepcopy(self.ensams)
        app.update(environment="production", inventory_host="ensams-prod-01", enabled=True)
        app["metrics"]["target_address"] = "10.88.0.12:18082"
        app["health"]["url"] = "https://ensams.internal.example/up"
        app["logs"]["labels"].update(environment="production", host="ensams-prod-01")
        self.assertEqual(validate_registration(app, ROOT / "applications/ensams.yml"), [])
        metrics, probes = generated_targets([app])
        labels = {"service": "ensams", "environment": "production", "host": "ensams-prod-01"}
        self.assertEqual(metrics, [{"targets": ["10.88.0.12:18082"], "labels": {**labels, "__metrics_path__": "/metrics"}}])
        self.assertEqual(probes, [{"targets": ["https://ensams.internal.example/up"], "labels": labels}])

    def test_sensitive_log_label_is_rejected(self):
        app = copy.deepcopy(self.ensams)
        app["logs"]["labels"]["request_id"] = "bad"
        errors = validate_registration(app, ROOT / "applications/ensams.yml")
        self.assertTrue(any("prohibited or high-cardinality" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
