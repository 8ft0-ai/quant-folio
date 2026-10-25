import datetime as dt
import unittest
from unittest.mock import patch
from pathlib import Path
from historical import query_for_dates, build_report
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
if __name__=="__main__": unittest.main()

[executed on device: voyager-rdc (39776536-9592-45e3-9fe6-64ec59327689)]