import datetime as dt
import unittest

from curate import render


def paper(id, title):
    return {
        "id": id, "title": title,
        "url": "https://arxiv.org/abs/" + id,
        "published": "2026-10-20",
    }


class IntelligenceReportTests(unittest.TestCase):
    def setUp(self):
        self.today = dt.date(2026, 10, 26)
        self.selected = [
            (paper("2610.10001", "Limit Order Book Forecasting"),
             "The authors propose an order book forecasting model.",
             "Could inform probabilistic liquidity modelling."),
            (paper("2610.10002", "Limit Order Book Market Impact"),
             "The authors study market impact using a simulator.",
             "Could help assess simulator realism."),
        ]

    def test_complete_report_counts_and_links(self):
        report = render(self.today, self.selected, 2, 4, "fixture", fetched_count=11)
        self.assertIn("**Retrieved:** 11 · **New unique:** 4 · **AI-assessed:** 2 · **Shortlisted:** 2", report)
        for heading in ("## 1. Executive briefing", "## 2. Research at a glance",
                        "## 3. Research details"):
            self.assertIn(heading, report)
        self.assertIn("Market microstructure (2 papers)", report)
        for entry, _, _ in self.selected:
            self.assertEqual(report.count("](" + entry["url"] + ")"), 3)
        self.assertEqual(report.count("· Abstract only"), 2)
        self.assertEqual(report.count("| **Finding / method** |"), 2)
        self.assertNotIn("## 4. Research opportunities", report)
        self.assertNotIn("historical trend", report.split("## 3. Research details")[1])

    def test_empty_and_single_paper(self):
        empty = render(self.today, [], 0, 0, "fixture", fetched_count=3)
        self.assertIn("**Retrieved:** 3", empty)
        self.assertIn("No new papers", empty)
        self.assertIn("No comparison is possible", empty)
        self.assertNotIn("| Paper |", empty)
        one = render(self.today, self.selected[:1], 1, 1, "fixture", fetched_count=1)
        self.assertIn("too varied", one)
        self.assertEqual(one.count("### 1."), 1)
        self.assertNotIn("### 2.", one)

    def test_markup_and_full_paper_evidence(self):
        item = paper("2610.10003", "Risk | Return")
        selected = [(item, "Novel [approach] | method", "Use for *risk* assessment")]
        output = render(self.today, selected, 1, 1, "fixture",
                        full_results={item["id"]: [
                            "**Assessment depth:** Full paper, 5 pages.",
                        ]}, fetched_count=1)
        self.assertIn("&#124;", output)
        self.assertIn("· Full-paper assessment", output)
        self.assertNotIn("## 4. Research opportunities", output)


if __name__ == "__main__":
    unittest.main()
