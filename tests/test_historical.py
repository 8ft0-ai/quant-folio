import datetime as dt
import unittest
from unittest.mock import patch
from io import BytesIO
import xml.etree.ElementTree as ET
from pathlib import Path
from historical import query_for_dates, build_report, fetch_historical
from curate import candidates_for_run

def paper(id, date):
    return {"id":id, "title":"Portfolio risk forecasting study", "abstract":"Portfolio risk forecasting and volatility market analysis", "published":date, "url":"https://arxiv.org/abs/"+id}

class HistoricalTests(unittest.TestCase):
    def test_inclusive_date_expression(self):
        q=query_for_dates(dt.date(2026,10,12),dt.date(2026,10,18))
        self.assertIn("submittedDate:[202610120000 TO 202610182359]",q)
        self.assertIn("cat:q-fin.TR",q)
        with self.assertRaises(ValueError):
            query_for_dates(dt.date(2026,10,19),dt.date(2026,10,18))
    def test_boundaries_and_isolation(self):
        papers=[paper("x","2026-10-11"),paper("a","2026-10-12"),
                paper("b","2026-10-18"),paper("z","2026-10-19")]
        selected,eligible=candidates_for_run(papers,set(),dt.date(2026,10,18),6,24)
        self.assertEqual({p["id"] for p in selected},{"a","b"})
        self.assertEqual(eligible,{"a","b"})
        # historical selection disregards even overlapping production IDs
        selected,_=candidates_for_run(papers,set(),dt.date(2026,10,18),6,24)
        self.assertEqual(len(selected),2)
    def test_empty_and_small_report(self):
        a=dt.date(2026,10,12);b=dt.date(2026,10,18)
        for selected in ([],[(paper("2610.10000","2026-10-12"),"Author reports modelling.","Relevant to risk.")]):
            with self.subTest(size=len(selected)):
                report=build_report([paper("2610.10000","2026-10-12")],1,a,b,dt.date(2026,10,26),selected)
                self.assertIn("HISTORICAL BACKFILL",report)
                self.assertIn("2026-10-26 UTC",report)
                self.assertIn("2026-10-12–2026-10-18",report)
                self.assertEqual(report.count("| **Finding / method** |"),len(selected))
                self.assertIn("## 2. Research at a glance",report)
                self.assertNotIn("## 4. Research opportunities",report)

    def test_historical_pagination_and_inconsistent_totals(self):
        ns = "http://www.w3.org/2005/Atom"
        osns = "http://a9.com/-/spec/opensearch/1.1/"
        def feed(ids, total):
            root = ET.Element("{%s}feed" % ns)
            ET.SubElement(root, "{%s}totalResults" % osns).text = str(total)
            for id in ids:
                e = ET.SubElement(root, "{%s}entry" % ns)
                ET.SubElement(e, "{%s}id" % ns).text = "https://arxiv.org/abs/" + id
                ET.SubElement(e, "{%s}title" % ns).text = "Portfolio forecasting"
                ET.SubElement(e, "{%s}summary" % ns).text = "Portfolio market study"
                ET.SubElement(e, "{%s}published" % ns).text = "2026-10-12T08:00:00Z"
            return ET.tostring(root)
        class Response:
            def __init__(self, payload):
                self.payload = payload
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, cap):
                return self.payload
        first = ["2610.%05d" % i for i in range(100)]
        second = ["2610.00100"]
        calls = iter([feed(first, 101), feed(second, 101)])
        def open_page(*args, **kwargs):
            return Response(next(calls))
        papers, raw = fetch_historical(dt.date(2026,10,12),
                                       dt.date(2026,10,18),
                                       opener=open_page, pause=lambda _: None)
        self.assertEqual((len(papers), raw), (101, 101))
        calls = iter([feed(first, 101), feed(second, 102)])
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            fetch_historical(dt.date(2026,10,12), dt.date(2026,10,18),
                             opener=open_page, pause=lambda _: None)

    def test_report_discloses_version_and_simulation_limits(self):
        report = Path("reports/2026-10-18.md").read_text(encoding="utf-8")
        self.assertIn("ideal simulated arbitrageur", report)
        self.assertIn("did not retain the input abstract payload/version", report)
        self.assertIn("not independently verified", report)
        self.assertNotIn("yielding 3.5% weekly risk-free returns", report)

if __name__=="__main__": unittest.main()
