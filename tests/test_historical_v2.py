import datetime as dt
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from historical import reporting_week, output_paths, provenance, write_pair_new, query_for_dates


class V2Tests(unittest.TestCase):
    def test_completed_sunday_and_inclusive_week(self):
        self.assertEqual(reporting_week(dt.date(2026, 10, 11), dt.date(2026, 10, 26)),
                         (dt.date(2026, 10, 5), dt.date(2026, 10, 11)))
        self.assertIn("202610050000 TO 202610112359",
                      query_for_dates(*reporting_week(dt.date(2026,10,11),
                                                        dt.date(2026,10,26))))
        for end in (dt.date(2026,10,12), dt.date(2026,10,25), dt.date(2026,11,1),
                    dt.date(1990,12,30)):
            with self.subTest(end=end), self.assertRaises(ValueError):
                reporting_week(end, dt.date(2026,10,25))

    def test_exclusive_pair_no_overwrite(self):
        with TemporaryDirectory() as root:
            destination = Path(root) / "2026-10-11.md"
            report, manifest = output_paths(dt.date(2026,10,11),destination)
            write_pair_new(report,manifest,"abc",{"x":1})
            self.assertEqual(report.read_text(),"abc")
            with self.assertRaises(FileExistsError):
                output_paths(dt.date(2026,10,11),destination)
            with self.assertRaises(FileExistsError):
                write_pair_new(report,manifest,"changed",{"x":2})
            self.assertEqual(report.read_text(),"abc")
            with self.assertRaises(ValueError):
                output_paths(dt.date(2026,10,11),Path(root)/"2026-10-25.md")

    def test_manifest_checksums_and_order(self):
        p = {"id":"2610.00001","source_id":"https://arxiv.org/abs/2610.00001v2",
             "source_version":"2","updated":"2026-10-11T00:00:00Z",
             "published":"2026-10-05","title":"Title","url":"https://arxiv.org/abs/2610.00001",
             "abstract":"Abstract"}
        start=dt.date(2026,10,5); end=dt.date(2026,10,11)
        manifest=provenance([p],1,start,end,dt.datetime(2026,10,26,tzinfo=dt.timezone.utc),
                            [p],{"2610.00001"},[(p,"summary","why")],"report")
        self.assertEqual(manifest["report_sha256"],hashlib.sha256(b"report").hexdigest())
        self.assertEqual(manifest["papers"][0]["abstract_sha256"],
                         hashlib.sha256(b"Abstract").hexdigest())
        self.assertEqual(manifest["counts"],{"retrieved":1,"unique":1,"eligible":1,
                                             "assessed":1,"recommended":1})
        self.assertEqual(manifest["papers"][0]["source_version"],"2")
        self.assertNotIn("OPENROUTER_API_KEY",json.dumps(manifest))


if __name__=="__main__":
    unittest.main()
