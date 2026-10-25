"""Deterministic safety assertions for gated weekly publication."""
from pathlib import Path
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/research.yml"


class WeeklyActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_schedule_and_manual_trigger(self):
        self.assertIn("cron: '17 1 * * 1'", self.workflow)
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn("default: false", self.workflow)

    def test_publication_requires_enabled_main_and_valid_event(self):
        self.assertIn("vars.QUANT_FOLIO_ENABLED == 'true'", self.workflow)
        self.assertIn("github.ref == 'refs/heads/main'", self.workflow)
        self.assertIn("github.event_name == 'schedule'", self.workflow)
        self.assertIn("github.event_name == 'workflow_dispatch' && inputs.publish", self.workflow)
        self.assertIn("github.event_name == 'workflow_dispatch' && !inputs.publish", self.workflow)

    def test_publication_is_one_serialised_commit(self):
        self.assertIn("group: quant-folio-publication", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)
        self.assertIn("git add -- reports/ data/seen.json", self.workflow)
        self.assertIn("git commit -m 'Publish Quant Folio digest'", self.workflow)
        self.assertIn("git push origin HEAD:main", self.workflow)
        self.assertIn("test -s data/seen.json", self.workflow)
        self.assertIn('test -s "reports/$(date -u +%F).md"', self.workflow)

    def test_publication_write_permission_job_scoped(self):
        self.assertIn("permissions:\n  contents: read", self.workflow)
        self.assertIn("    permissions:\n      contents: write", self.workflow)


if __name__ == "__main__":
    unittest.main()
