"""Issue #16: evidence-labelled optional research analysis pilot."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from journal import build


class ResearchAnalysisPilotTests(unittest.TestCase):
    def test_three_priority_disclosures_and_original_copy_interaction(self):
        page = build.build()
        self.assertEqual(page.count('class="research-analysis"'), 3)
        self.assertEqual(page.count('data-copy-prompt'), 8)
        self.assertIn("ABSTRACT-LEVEL · UNVERIFIED", page)
        self.assertEqual(page.count("Proposed falsification — not executed"), 3)
        self.assertIn("2610.27100", page)
        self.assertIn("2610.25802", page)
        self.assertIn("2610.24544", page)

    def test_schema_metadata_and_exact_pinned_report(self):
        record = json.loads(build.ANALYSIS.read_text())
        config = json.loads(build.CONFIG.read_text())
        self.assertEqual(record["source_commit"], config["source_main_sha"])
        self.assertEqual(record["source_report_sha256"], config["report_sha256"])
        self.assertEqual(record["generation"]["external_provider_calls"], 0)
        self.assertIsNone(record["generation"]["prompt_tokens"])
        self.assertEqual({x["id"] for x in record["assessments"]},
                         {x["id"] for x in config["priorities"]})
        self.assertTrue(all(x["independent_verification"] == "none" for x in record["assessments"]))

    def test_invalid_evidence_falls_back_to_unenriched_journal(self):
        original = json.loads(build.ANALYSIS.read_text())
        for change in (
            lambda v: v.update(source_commit="0" * 40),
            lambda v: v["assessments"][0].update(independent_verification="verified"),
            lambda v: v["assessments"][0].update(source_url="https://invalid.example"),
            lambda v: v["assessments"][0].update(source_finding_sha256="0" * 64),
            lambda v: v["assessments"].pop(),
        ):
            data = json.loads(json.dumps(original))
            change(data)
            with tempfile.TemporaryDirectory() as directory:
                tmp = Path(directory) / "analysis.json"
                tmp.write_text(json.dumps(data))
                with patch.object(build, "ANALYSIS", tmp):
                    html = build.build()
                    self.assertEqual(html.count('class="research-analysis"'), 0)
                    self.assertEqual(html.count('data-copy-prompt'), 8)
        with patch.object(build, "ANALYSIS", Path("/tmp/nonexistent-quantfolio-16-file.json")):
            self.assertNotIn('class="research-analysis"', build.build())

    def test_escaped_untrusted_assessment_content(self):
        record = json.loads(build.ANALYSIS.read_text())
        record["assessments"][0]["method"] = '<script>alert("x")</script>'
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory) / "analysis.json"
            tmp.write_text(json.dumps(record))
            with patch.object(build, "ANALYSIS", tmp):
                html = build.build()
                self.assertIn('&lt;script&gt;', html)
                self.assertNotIn('<script>alert("x")</script>', html)

    def test_only_static_files_not_dynamic_inference(self):
        html = build.build()
        self.assertEqual(html.count('class="research-analysis"'), 3)
        script = (build.JOURNAL / "assets/app.js").read_text()
        self.assertNotIn("fetch(", script)
        self.assertNotIn("localStorage", script)
        self.assertIn('type="button" class="small-action feature-copy"', html)


if __name__ == "__main__":
    unittest.main()
