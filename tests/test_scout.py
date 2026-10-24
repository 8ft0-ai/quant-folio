import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scout import build, parse_atom

FIXTURE = Path(__file__).with_name("fixture.atom")


class ScoutTests(unittest.TestCase):
    def setUp(self):
        self.papers = parse_atom(FIXTURE.read_bytes())
        self.today = dt.date(2026, 10, 24)

    def test_parse(self):
        self.assertEqual(len(self.papers), 3)
        self.assertEqual(self.papers[0]["id"], "2610.12345")

    def test_selection_and_deduplication(self):
        report, seen, count = build(self.papers + [self.papers[0]], set(), self.today, 8, 8)
        self.assertEqual(count, 1)
        self.assertIn("2610.12345", seen)
        self.assertIn("Abstract", report.lower().capitalize() if False else report)
        self.assertIn("not verified", report)

    def test_empty_valid(self):
        report, seen, count = build(self.papers, {"2610.12345", "2610.23456", "2610.33333"}, self.today, 8, 8)
        self.assertEqual(count, 0)
        self.assertIn("No new papers", report)

    def test_no_future_publication(self):
        report, seen, count = build(self.papers, set(), dt.date(2026, 10, 20), 8, 8)
        self.assertNotIn("2610.12345", seen)
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
