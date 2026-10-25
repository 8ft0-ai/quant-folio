import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from io import BytesIO
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from curate import candidates_for_run, execute, load_seen, render, validate_assessment, request_json, assess_batches
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
        self.assertIn("Abstract only",report)
        self.assertIn("not independently replicated",report)
        self.assertIn("Why investigate",report)

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
            self.assertEqual(load_seen(args.state), {p["id"] for p in self.candidates})
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

    def test_structured_responses_and_diagnostics(self):
        class MockResponse:
            def __init__(self, data):
                self.data = data
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, *args):
                return json.dumps(self.data).encode()

        def response(content, reason):
            return {"choices": [{"finish_reason": reason, "message": {"content": content}}],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 42}}

        cases = [
            (json.dumps(VALID), "stop", None),
            ('{"recommendations":[{"id":"2610.', "length", "Incomplete model response"),
            ('{"recommendations":[{"id":"2610.', "stop", "Malformed completed model JSON"),
            (None, "stop", "Missing or non-text model content"),
        ]
        for content, reason, expected in cases:
            with self.subTest(reason=reason, expected=expected):
                with patch("curate.urlopen", return_value=MockResponse(response(content, reason))):
                    if expected:
                        with self.assertRaisesRegex(ValueError, expected) as raised:
                            request_json([], "nvidia/nemotron-3.5-super-vl:free", "test-key", 200)
                        self.assertIn("prompt_tokens=100", str(raised.exception))
                        self.assertIn("chars=", str(raised.exception))
                        self.assertIn("finish_reason=", str(raised.exception))
                    else:
                        value, usage = request_json([], "nvidia/nemotron-3.5-super-vl:free", "test-key", 200)
                        self.assertEqual(value, VALID)
                        self.assertEqual(usage["completion_tokens"], 42)

    def test_invalid_recommendation_extra_fields(self):
        value = {"recommendations": [dict(VALID["recommendations"][0], extra="untrusted")]}
        with self.assertRaises(ValueError):
            validate_assessment(value, self.candidates, 8)

    def test_abstract_only_succeeds_without_pdf_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = self.arguments(root)
            args.ai_fixture = None
            with patch("curate.fetch", return_value=self.papers), \
                 patch("curate.request_assessment", return_value=(VALID, {"prompt_tokens": 10, "completion_tokens": 20})), \
                 patch("curate.extract_paper", side_effect=AssertionError("unexpected PDF extraction")):
                output = execute(args)
            self.assertIn("· Abstract only", output)
            self.assertEqual(load_seen(args.state), {p["id"] for p in self.candidates})

    def test_live_assessment_failure_preserves_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = self.arguments(root)
            args.ai_fixture = None
            args.state.write_text('{"seen":["prior"]}')
            args.reports.mkdir()
            previous = args.reports / "2026-10-24.md"
            previous.write_text("previous")
            with patch("curate.fetch", return_value=self.papers), \
                 patch("curate.request_assessment", side_effect=ValueError("Incomplete model response")):
                with self.assertRaises(ValueError):
                    execute(args)
            self.assertEqual(previous.read_text(), "previous")
            self.assertEqual(load_seen(args.state), {"prior"})

    def test_five_abstract_batches_and_global_cap(self):
        papers = [
            dict(self.candidates[0], id=f"paper-{index}")
            for index in range(12)
        ]
        seen_sizes = []

        def fake_assessment(batch, limit, model, api_key):
            seen_sizes.append((len(batch), limit))
            return {
                "recommendations": [
                    {"id": paper["id"], "summary": "Abstract-grounded finding",
                     "why": "Relevant quantitative research"}
                    for paper in batch[:limit]
                ]
            }, {"prompt_tokens": 10, "completion_tokens": 20}

        with patch("curate.request_assessment", side_effect=fake_assessment):
            selected, usage = assess_batches(papers, 8, "test-model", "test-key")
        self.assertEqual(seen_sizes, [(5, 3), (5, 3), (2, 3)])
        self.assertEqual(len(selected), 8)
        self.assertEqual([p["id"] for p, _, _ in selected],
                         [f"paper-{i}" for i in (0, 1, 2, 5, 6, 7, 10, 11)])
        self.assertEqual(usage, {"prompt_tokens": 30, "completion_tokens": 60})

    def test_batch_failure_is_not_silently_ignored(self):
        papers = [dict(self.candidates[0], id=f"paper-{i}") for i in range(6)]
        def fake_assessment(batch, limit, model, api_key):
            if batch[0]["id"] == "paper-5":
                return {"recommendations": [{"id": "unrecognised", "summary": "x", "why": "y"}]}, {}
            return {"recommendations": []}, {}
        with patch("curate.request_assessment", side_effect=fake_assessment):
            with self.assertRaisesRegex(ValueError, "Unknown or duplicate"):
                assess_batches(papers, 8, "test-model", "test-key")

    def test_unassessed_candidates_remain_eligible(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = self.arguments(root)
            args.ai_fixture = None
            with patch("curate.fetch", return_value=self.papers), \
                 patch("curate.request_assessment", return_value=(VALID, {})):
                execute(args)
            self.assertNotIn(self.papers[1]["id"], load_seen(args.state))

    def test_future_papers_excluded(self):
        result,_=candidates_for_run(self.papers,set(),dt.date(2026,10,20),8,24)
        self.assertEqual(result,[])

if __name__=="__main__": unittest.main()
