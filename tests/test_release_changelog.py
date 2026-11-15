"""Unit tests for the version changelog release gate."""

import unittest

from scripts.release_changelog import release_notes


VALID = """# Changelog

## [v1.2.3] - 2026-11-15

### Added
- Add CIDR preflight reporting.

### Fixed
- Fix config parsing.

## [Unreleased]
"""


class ReleaseChangelogTests(unittest.TestCase):
    def test_extracts_only_requested_version(self):
        notes = release_notes(VALID, "v1.2.3")
        self.assertIn("Add CIDR preflight reporting.", notes)
        self.assertNotIn("[Unreleased]", notes)

    def test_rejects_missing_version_entry(self):
        with self.assertRaisesRegex(ValueError, "Missing dated changelog"):
            release_notes(VALID, "v1.2.4")

    def test_rejects_invalid_tag_format(self):
        with self.assertRaisesRegex(ValueError, "Invalid release version"):
            release_notes(VALID, "1.2.3")

    def test_rejects_placeholder_only_entry(self):
        changelog = VALID.replace("- Add CIDR preflight reporting.\n\n### Fixed\n- Fix config parsing.", "- TBD")
        with self.assertRaisesRegex(ValueError, "meaningful bullet"):
            release_notes(changelog, "v1.2.3")

    def test_rejects_duplicate_version_sections(self):
        duplicate = VALID.replace("## [Unreleased]", "## [v1.2.3] - 2026-11-15\n\n### Fixed\n- Duplicate entry.\n\n## [Unreleased]")
        with self.assertRaisesRegex(ValueError, "Duplicate changelog entries"):
            release_notes(duplicate, "v1.2.3")

    def test_rejects_invalid_calendar_date(self):
        changelog = VALID.replace("2026-11-15", "2026-13-45")
        with self.assertRaisesRegex(ValueError, "Invalid release date"):
            release_notes(changelog, "v1.2.3")


if __name__ == "__main__":
    unittest.main()
