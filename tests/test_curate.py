import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from curate import candidates_for_run, execute, load_seen, render, validate_assessment
from scout import parse_atom

FIXTURE = Path(__file__).with_name("fixture.atom")
VALID = {"recommendations":[{"id":"2610.12345","summary":"The abstract discusses foreign exchange forecasting with order-book signals.","why":"Relevant to microstructure predictors."}]}

class CurateTests(unittest.TestCase):
    def setUp(self):
        self.papers=parse_atom(FIXTURE.read_bytes())
        self.today=dt.date(2026,10,24)
        self.candidates,_=candidates_for_run(self.papers,set(),self.today,8,24)

    def arguments(self,root):
        from argparse import Namespace
        return Namespace(fixture=FIXTURE,ai_fixture=root/"ai.json",today=self.today,
            state=root/"seen.json",reports=root/"reports",window=8,limit=8,
            fetch_limit=15,max_candidates=24,model="fixture-model")

    def test_abstract_evidence(self):
        selected=validate_assessment(VALID,self.candidates,8)
        report=render(self.today,selected,1,3,"fixture-model")
        self.assertIn("abstract only",report)
        self.assertIn("not independently",report)
        self.assertIn("Why read it:",report)

    def test_invalid_results_fail(self):
        for value in [
            {"recommendations":[{"id":"unknown","summary":"x","why":"y"}]},
            {"recommendations":VALID["recommendations"]*2},
            {"recommendations":"bad"},
        ]:
            with self.assertRaises(ValueError):
                validate_assessment(value,self.candidates,8)

    def test_repeated_run_and_empty_shortlist(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); args=self.arguments(root)
            args.ai_fixture.write_text(json.dumps(VALID))
            first=execute(args)
            second=execute(args)
            self.assertIn("Foreign Exchange Forecasting",first)
            self.assertIn("No new papers",second)
            self.assertEqual(len(load_seen(args.state)),3)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); args=self.arguments(root)
            args.ai_fixture.write_text('{"recommendations":[]}')
            self.assertIn("No new papers",execute(args))

    def test_failed_assessment_does_not_change_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); args=self.arguments(root)
            args.state.write_text('{"seen":["prior"]}')
            args.reports.mkdir()
            report=args.reports/"2026-10-24.md"; report.write_text("previous")
            args.ai_fixture.write_text('{"recommendations":[{"id":"invalid","summary":"x","why":"y"}]}')
            with self.assertRaises(ValueError): execute(args)
            self.assertEqual(report.read_text(),"previous")
            self.assertEqual(load_seen(args.state),{"prior"})

    def test_future_papers_excluded(self):
        result,_=candidates_for_run(self.papers,set(),dt.date(2026,10,20),8,24)
        self.assertEqual(result,[])

if __name__=="__main__": unittest.main()

[executed on device: voyager-rdc (39776536-9592-45e3-9fe6-64ec59327689)]