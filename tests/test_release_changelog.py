"""Unit tests for pending and promoted release changelog metadata."""

import unittest

from scripts.release_changelog import pending_notes, promote_changelog


PENDING = """# Pending release metadata: v1.2.3
Release date: 2026-11-15

### Added
- Add CIDR preflight reporting.

### Fixed
- Fix config parsing.
"""

CHANGELOG = """# Changelog

All notable changes to ObStack are documented in this file.

## [Unreleased]

### Added
- Keep next release notes here.
"""


class ReleaseChangelogTests(unittest.TestCase):
    def test_validates_and_extracts_pending_metadata(self):
        date, notes = pending_notes(PENDING, "v1.2.3")
        self.assertEqual(date, "2026-11-15")
        self.assertIn("## [v1.2.3] - 2026-11-15", notes)
        self.assertIn("Add CIDR preflight reporting.", notes)

    def test_rejects_missing_pending_metadata(self):
        with self.assertRaisesRegex(ValueError, "Pending metadata must begin"):
            pending_notes(PENDING, "v1.2.4")

    def test_rejects_invalid_release_date(self):
        with self.assertRaisesRegex(ValueError, "Invalid release date"):
            pending_notes(PENDING.replace("2026-11-15", "2026-13-45"), "v1.2.3")

    def test_rejects_placeholder_only_notes(self):
        placeholder = PENDING.replace("- Add CIDR preflight reporting.", "- TBD").replace("- Fix config parsing.", "- TBD")
        with self.assertRaisesRegex(ValueError, "meaningful bullet"):
            pending_notes(placeholder, "v1.2.3")

    def test_rejects_unsupported_category(self):
        invalid = PENDING.replace("### Added", "### Miscellaneous")
        with self.assertRaisesRegex(ValueError, "Unsupported changelog category"):
            pending_notes(invalid, "v1.2.3")

    def test_rejects_bullets_outside_categories(self):
        invalid = PENDING.replace("### Added\n", "").replace("### Fixed\n", "")
        with self.assertRaisesRegex(ValueError, "supported category"):
            pending_notes(invalid, "v1.2.3")

    def test_promotes_notes_before_unreleased(self):
        _, notes = pending_notes(PENDING, "v1.2.3")
        promoted = promote_changelog(CHANGELOG, "v1.2.3", notes)
        self.assertLess(promoted.index("## [v1.2.3]"), promoted.index("## [Unreleased]"))
        self.assertIn("Keep next release notes here.", promoted)

    def test_rejects_duplicate_promotion(self):
        _, notes = pending_notes(PENDING, "v1.2.3")
        promoted = promote_changelog(CHANGELOG, "v1.2.3", notes)
        with self.assertRaisesRegex(ValueError, "already contains"):
            promote_changelog(promoted, "v1.2.3", notes)


if __name__ == "__main__":
    unittest.main()

from scripts.generate_release_metadata import build_metadata, classify


class GenerateReleaseMetadataTests(unittest.TestCase):
    def test_generates_categorized_notes_from_merged_prs(self):
        prs = [
            {
                "number": 21,
                "title": "feat(metrics): add scrape health panel",
                "labels": [],
                "mergeCommit": {"oid": "abc123"},
                "url": "https://github.com/0FFSIDE1/ObStack/pull/21",
            },
            {
                "number": 22,
                "title": "fix: correct retention validation",
                "labels": [],
                "mergeCommit": {"oid": "def456"},
                "url": "https://github.com/0FFSIDE1/ObStack/pull/22",
            },
            {
                "number": 23,
                "title": "chore: update test tooling",
                "labels": [],
                "mergeCommit": {"oid": "ghi789"},
                "url": "https://github.com/0FFSIDE1/ObStack/pull/23",
            },
        ]
        result = build_metadata("v1.2.3", prs, {"abc123", "def456", "ghi789"}, "2026-11-15")
        self.assertIn("### Added", result)
        self.assertIn("add scrape health panel", result)
        self.assertIn("### Fixed", result)
        self.assertIn("correct retention validation", result)
        self.assertNotIn("update test tooling", result)

    def test_explicit_label_overrides_title_inference(self):
        pr = {"number": 24, "title": "improve alert routing", "labels": [{"name": "release:security"}]}
        self.assertEqual(classify(pr), "Security")

    def test_release_none_label_excludes_pr(self):
        pr = {"number": 25, "title": "feat: internal-only", "labels": [{"name": "release:none"}]}
        self.assertEqual(classify(pr), "None")

    def test_requires_classification_for_nonconventional_title(self):
        pr = {"number": 26, "title": "Improve things", "labels": []}
        with self.assertRaisesRegex(ValueError, "no release label"):
            classify(pr)

    def test_rejects_conflicting_release_labels(self):
        pr = {
            "number": 27,
            "title": "feat: something",
            "labels": [{"name": "release:added"}, {"name": "release:fixed"}],
        }
        with self.assertRaisesRegex(ValueError, "conflicting release labels"):
            classify(pr)

    def test_rejects_empty_release_window(self):
        with self.assertRaisesRegex(ValueError, "No user-facing merged pull requests"):
            build_metadata("v1.2.3", [], set(), "2026-11-15")
