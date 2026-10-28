"""Focused offline contract checks for the V1 private journal candidate."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from briefing_source import SourceError
from journal import build


class ParseHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class JournalBuildTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(build.CONFIG.read_text(encoding="utf-8"))
        self.page = build.build()
        self.dom = ParseHTML()
        self.dom.feed(self.page)

    def altered_config(self, value):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "editorial.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with patch.object(build, "CONFIG", path):
                return build.build()

    def test_source_bound_to_immutable_report_and_expected_counts(self):
        self.assertIn(self.config["source_main_sha"], self.page)
        self.assertIn(self.config["report_sha256"], hashlib.sha256(
            (build.ROOT / "reports/2026-10-25.md").read_bytes()).hexdigest())
        self.assertIn("Not recorded", self.page)
        for value in ["31", "24", "08"]:
            self.assertIn(f"<strong>{value}</strong>", self.page)
        self.assertIn("Retrospective main-branch report", self.page)

    def test_eight_ids_each_have_one_editorial_entry(self):
        identifiers = [attrs["id"][6:] for _, attrs in self.dom.elements
                       if re.fullmatch(r"paper-\d{4}\.\d{4,5}", attrs.get("id", ""))]
        source_ids = {item["id"] for item in
                      build.inspect_report(
                          (build.ROOT / "reports/2026-10-25.md").read_text(),
                          "2026-10-25", self.config["source_main_sha"],
                          as_of="2026-10-25")["papers"]}
        self.assertEqual(len(identifiers), 8)
        self.assertEqual(set(identifiers), source_ids)
        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_all_paper_links_and_abstract_evidence(self):
        for identifier in ["2610.27100", "2610.25802", "2610.24544"]:
            self.assertIn(f'paper-{identifier}', self.page)
            self.assertIn(f"https://arxiv.org/abs/{identifier}", self.page)
        self.assertGreaterEqual(self.page.count("ABSTRACT ONLY"), 8)
        self.assertEqual(self.page.count("data-copy-prompt"), 8)
        self.assertIn('id="prompt-dialog"', self.page)
        self.assertIn("not been independently verified", self.page)
        self.assertIn("NOT EXECUTED", self.page)

    def test_refuse_source_checksum_mismatch(self):
        changed = dict(self.config, report_sha256="0" * 64)
        with self.assertRaisesRegex(SourceError, "checksum mismatch"):
            self.altered_config(changed)

    def test_refuse_historical_draft_even_with_matching_checksum(self):
        draft = (build.ROOT / "reports/2026-10-18.md").read_bytes()
        changed = dict(self.config, edition="2026-10-18",
                       report_sha256=hashlib.sha256(draft).hexdigest())
        with self.assertRaisesRegex(SourceError, "Historical draft"):
            self.altered_config(changed)

    def test_refuse_duplicate_editorial_priority(self):
        changed = json.loads(json.dumps(self.config))
        changed["priorities"][1]["id"] = changed["priorities"][0]["id"]
        with self.assertRaisesRegex(SourceError, "distinct"):
            self.altered_config(changed)

    def test_refuse_unknown_theme_or_inconsistent_source(self):
        changed = json.loads(json.dumps(self.config))
        changed["themes"][0]["category"] = "Invented category"
        with self.assertRaisesRegex(SourceError, "Theme categories"):
            self.altered_config(changed)

    def test_no_remote_dependencies_no_tracking_and_no_private_notes(self):
        for tag, attrs in self.dom.elements:
            if tag in ("script", "link"):
                uri = attrs.get("src") or attrs.get("href")
                if uri:
                    self.assertTrue(uri.startswith("./assets/"), uri)
        script = (build.JOURNAL / "assets/app.js").read_text(encoding="utf-8")
        self.assertNotIn("localStorage", script)
        self.assertNotIn("fetch(", script)
        self.assertNotIn("sendBeacon", script)
        self.assertIn("LOCAL DESIGN PREVIEW", self.page)
        self.assertIn("no access controls are active", self.page)

    def test_committed_render_matches_generator(self):
        existing = build.OUTPUT.read_text(encoding="utf-8")
        self.assertEqual(existing, self.page + "\n")


if __name__ == "__main__":
    unittest.main()
