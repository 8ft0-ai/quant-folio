"""Issue #18: one source-pinned full-paper assessment and safe static preview."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from journal import build, deep_assessment as deep


class DeepAssessmentPilotTests(unittest.TestCase):
    def test_pinned_full_paper_and_generation_provenance(self):
        loaded = deep.load()
        self.assertIsNotNone(loaded)
        md, record = loaded
        self.assertEqual(record["pdf_sha256"], deep.PDF_SHA256)
        self.assertEqual(record["pdf_url"], deep.PAPER_URL)
        self.assertEqual(record["paper_version"], "v2")
        self.assertEqual(record["retrieved_on"], "2026-10-29")
        self.assertEqual(record["pdf_bytes"], 1000584)
        self.assertEqual(record["markdown_sha256"], hashlib.sha256(deep.SOURCE.read_bytes()).hexdigest())
        self.assertTrue(2000 <= len(md.split()) <= 3500)
        self.assertEqual(record["generation"]["external_provider_calls"], 0)
        self.assertIsNone(record["generation"]["cost_usd"])
        self.assertIn("[PROPOSED / NOT RUN]", md)
        self.assertIn("Table 2", md)
        self.assertIn("Appendix B", md)

    def test_single_target_link_preserves_all_other_interactions(self):
        page = build.build()
        self.assertEqual(page.count('class="deep-full-link"'), 1)
        self.assertIn('./assessments/2610.25802.html', page)
        self.assertEqual(page.count('data-copy-prompt'), 8)
        self.assertEqual(page.count('class="research-analysis"'), 3)
        self.assertEqual(page.count('class="feature-card"'), 3)
        self.assertEqual(page.count('class="paper-row"'), 5)
        self.assertEqual(page.count("Compare original source wording"), 3)
        self.assertIn("ABSTRACT-LEVEL · UNVERIFIED", page)

    def test_full_page_has_causal_navigation_and_safe_links(self):
        md, record = deep.load()
        page = deep.render(md, record)
        self.assertEqual(page.count("<h1"), 1)
        self.assertIn('href="../index.html#paper-2610.25802"', page)
        self.assertIn('href="../assets/deep.css"', page)
        self.assertIn('href="#5-falsifiable-read-only-validation-protocol"', page)
        self.assertIn('id="5-falsifiable-read-only-validation-protocol"', page)
        self.assertIn('href="https://arxiv.org/pdf/2610.25802v2#page=9"', page)
        self.assertIn("OFFLINE PREVIEW", page)
        self.assertIn(deep.PDF_SHA256, page)
        self.assertNotIn("<script", page)

    def test_malformed_or_missing_metadata_removes_only_deep_enrichment(self):
        original = json.loads(deep.MANIFEST.read_text())
        for mutate in (
            lambda v: v.update(markdown_sha256="0" * 64),
            lambda v: v.update(pdf_sha256="0" * 64),
            lambda v: v.update(paper_version="v1"),
            lambda v: v.update(pdf_url="https://evil.example/fake.pdf"),
            lambda v: v["generation"].update(external_provider_calls=1),
        ):
            candidate = json.loads(json.dumps(original))
            mutate(candidate)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "metadata.json"
                path.write_text(json.dumps(candidate))
                with patch.object(deep, "MANIFEST", path):
                    self.assertIsNone(deep.load())
                    page = build.build()
                    self.assertNotIn('class="deep-full-link"', page)
                    self.assertEqual(page.count('data-copy-prompt'), 8)
                    self.assertEqual(page.count('class="research-analysis"'), 3)
        with patch.object(deep, "SOURCE", Path("/this/path/is/not/a/deep-paper.md")):
            self.assertIsNone(deep.load())
            self.assertNotIn('class="deep-full-link"', build.build())

    def test_escapes_untrusted_markup_and_does_not_accept_arbitrary_links(self):
        dangerous = '<script>alert(1)</script> **Bold** [bad](javascript:alert(1)) [other](https://evil.example/)'
        html = deep.inline(dangerous)
        self.assertNotIn("<script", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn('href="javascript:', html)
        self.assertNotIn('href="https://evil.example/', html)
        self.assertIn("<strong>Bold</strong>", html)
        self.assertEqual(deep.inline("[source](https://arxiv.org/pdf/2610.25802v2)").count("<a "), 1)

    def test_stale_prebuilt_page_is_removed_when_manifest_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "2610.25802.html"
            output.write_text("stale deep page")
            with patch.object(deep, "OUTPUT", output), patch.object(deep, "MANIFEST", Path(directory) / "missing.json"):
                self.assertFalse(deep.write_preview())
                self.assertFalse(output.exists())

    def test_generated_static_site_contains_real_source_and_no_browser_inference(self):
        self.assertTrue(deep.write_preview())
        html = deep.OUTPUT.read_text()
        self.assertIn("RESEARCH ANALYSIS V2", html)
        self.assertIn("SOURCE-CHECKED", html)
        self.assertIn("Falsifiable, read-only validation protocol", html)
        self.assertNotIn("fetch(", html)
        self.assertNotIn("localStorage", html)


if __name__ == "__main__":
    unittest.main()
