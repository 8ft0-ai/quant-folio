"""Offline tests for Research Briefing V1 source identity and failure boundaries."""
import base64
import datetime as dt
import json
from pathlib import Path
import unittest

from briefing_source import API, SourceError, inspect_report, retrieve_report, COUNT_ROW

ROOT = Path(__file__).resolve().parents[1]
SHA = "b72ff11d666a3dfbd583a8197b990cb0cb5a9097"
EXPECTED = [
    "2610.25495", "2610.28753", "2610.24544", "2610.27100",
    "2610.28863", "2610.24558", "2610.25802", "2610.26919",
]


def report(date):
    return (ROOT / "reports" / f"{date}.md").read_text(encoding="utf-8")


def fake_source(content=None, files=None):
    content = content if content is not None else report("2026-10-25")
    files = files if files is not None else ["2026-10-11", "2026-10-18", "2026-10-25"]
    requests = []

    def get(url):
        requests.append(url)
        if url == f"{API}/commits/main":
            return {"sha": SHA}
        if url == f"{API}/contents/reports?ref={SHA}":
            return [{"path": f"reports/{name}.md"} for name in files]
        if url == f"{API}/contents/reports/2026-10-25.md?ref={SHA}":
            return {
                "encoding": "base64",
                "sha": "44a4a0bea1aca480af6261c31b1e399cced3a2d4",
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            }
        raise SourceError(f"Unexpected URL {url}")
    return get, requests


class BriefingSourceTests(unittest.TestCase):
    def test_actual_25_october_report_eight_identities_counts_links(self):
        m = inspect_report(report("2026-10-25"), "2026-10-25", SHA,
                           as_of="2026-10-28", focus="TradeLab")
        self.assertEqual([p["id"] for p in m["papers"]], EXPECTED)
        self.assertEqual([p["url"] for p in m["papers"]],
                         [f"https://arxiv.org/abs/{id}" for id in EXPECTED])
        self.assertEqual(m["counts"], {
            "retrieved": None, "new_unique": 31, "ai_assessed": 24, "shortlisted": 8,
        })
        self.assertEqual(m["categories_in_details"], {
            "Market microstructure": 4, "Portfolio and risk": 2,
            "Signals and filtering": 2,
        })
        self.assertEqual(m["edition_type"], "retrospective-main-report")
        self.assertEqual(m["age_days"], 3)
        self.assertEqual(m["project_focus"], "TradeLab")
        self.assertTrue(all(p["evidence"] == "Abstract only" for p in m["papers"]))
        self.assertTrue(all(p["finding"] and p["relevance"] and p["open_question"]
                            for p in m["papers"]))
        self.assertIn("not a new assessment", " ".join(m["warnings"]))
        self.assertIn("unverified", " ".join(m["warnings"]))
        self.assertEqual(len(m["sha256"]), 64)

    def test_latest_pinned_main_retrieval_and_explicit_focus(self):
        get, requests = fake_source()
        m = retrieve_report(as_of="2026-10-28", focus="Quant Radar", get=get)
        self.assertEqual(m["report_date"], "2026-10-25")
        self.assertEqual(m["project_focus"], "Quant Radar")
        self.assertEqual(len(requests), 3)
        self.assertTrue(all(req.endswith(f"ref={SHA}") for req in requests[1:]))
        self.assertIn(f"/blob/{SHA}/reports/2026-10-25.md", m["permalink"])

    def test_missing_report_does_not_fall_back_to_another_date(self):
        get, requests = fake_source()
        with self.assertRaisesRegex(SourceError, "not found"):
            retrieve_report(date="2026-10-12", as_of="2026-10-28", get=get)
        self.assertEqual(len(requests), 2)

    def test_no_reports_on_main(self):
        get, _ = fake_source(files=[])
        with self.assertRaisesRegex(SourceError, "No Markdown"):
            retrieve_report(get=get)

    def test_stale_report_is_explicitly_labelled(self):
        m = inspect_report(report("2026-10-25"), "2026-10-25", SHA,
                           as_of="2026-11-09")
        self.assertTrue(any(s.startswith("STALE:") for s in m["warnings"]))
        self.assertEqual(m["age_days"], 15)

    def test_historical_draft_not_treated_as_weekly_publication(self):
        m = inspect_report(report("2026-10-18"), "2026-10-18", SHA,
                           as_of="2026-10-28")
        self.assertEqual(m["edition_type"], "historical-draft")
        self.assertEqual(m["counts"], {
            "retrieved": 50, "new_unique": 50, "ai_assessed": 24, "shortlisted": 8,
        })
        self.assertTrue(any("NON-PUBLISHED DRAFT" in w for w in m["warnings"]))

    def test_missing_counts_are_unknown_not_inferred(self):
        incomplete = COUNT_ROW.sub("", report("2026-10-25"))
        m = inspect_report(incomplete, "2026-10-25", SHA, as_of="2026-10-28")
        self.assertEqual(m["counts"], {
            "retrieved": None, "new_unique": None,
            "ai_assessed": None, "shortlisted": None,
        })
        self.assertEqual(len(m["papers"]), 8)
        self.assertTrue(any("do not estimate" in s for s in m["warnings"]))

    def test_unavailable_github_source_fails_closed(self):
        def unavailable(_):
            raise SourceError("GitHub source unavailable: HTTP 503")
        with self.assertRaisesRegex(SourceError, "unavailable"):
            retrieve_report(as_of="2026-10-28", get=unavailable)

    def test_id_date_or_count_mismatch_is_rejected(self):
        raw = report("2026-10-25")
        for corrupted in [
            raw.replace("briefing · 2026-10-25", "briefing · 2026-10-24"),
            raw.replace("**Shortlisted:** 8", "**Shortlisted:** 7"),
            raw.replace("arXiv 2610.25495", "arXiv 2610.99999"),
            raw.replace("https://arxiv.org/abs/2610.27100",
                        "https://arxiv.org/abs/2610.99999"),
        ]:
            with self.subTest(corrupted=corrupted[:80]):
                with self.assertRaises(SourceError):
                    inspect_report(corrupted, "2026-10-25", SHA, as_of="2026-10-28")

    def test_source_links_not_claimed_as_live_verified(self):
        m = inspect_report(report("2026-10-25"), "2026-10-25", SHA,
                           as_of="2026-10-28")
        self.assertTrue(any("not live-checked" in w for w in m["warnings"]))


if __name__ == "__main__":
    unittest.main()
