import io
import unittest
from unittest.mock import patch
from full_paper import FIELDS, validate_full_assessment, extract_paper
from curate import request_json


class FullPaperTests(unittest.TestCase):
    def test_validate_evidence_contract(self):
        valid = {name: {"claim": "Claim", "evidence": "Section 2",
                        "status": "verified_from_text"} for name in FIELDS}
        self.assertEqual(validate_full_assessment(valid), valid)
        valid["findings"]["evidence"] = ""
        with self.assertRaises(ValueError):
            validate_full_assessment(valid)

    def test_unknown_and_extra_fields_rejected(self):
        with self.assertRaises(ValueError):
            validate_full_assessment({"objective": "unstructured"})

    def test_invalid_paper_id_does_not_fetch(self):
        with self.assertRaises(ValueError):
            extract_paper("../../private")

    def test_paid_model_rejected_before_transport(self):
        with self.assertRaises(ValueError):
            request_json([], "nvidia/nemotron-3.5-super-vl", "dummy", 100)

    def test_no_key_rejected(self):
        with self.assertRaises(RuntimeError):
            request_json([], "nvidia/nemotron-3.5-super-vl:free", "", 100)


if __name__ == "__main__":
    unittest.main()
