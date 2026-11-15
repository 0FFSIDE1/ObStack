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
