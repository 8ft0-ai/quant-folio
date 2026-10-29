"""Regression contract for dormant private-hosting candidate."""
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from journal.hosting.preflight import check, CONFIG

ROOT = Path(__file__).resolve().parents[1]


class HostingContractTests(unittest.TestCase):
    def test_offline_candidate_passes(self):
        self.assertEqual(check(), [])

    def test_no_automatic_deployment_workflow(self):
        for workflow in (ROOT / ".github/workflows").glob("*.yml"):
            text = workflow.read_text().lower()
            self.assertNotIn("wrangler deploy", text)
            self.assertNotIn("cloudflare/wrangler-action", text)

    def test_access_is_not_claimed_as_provisioned(self):
        docs = (ROOT / "journal/hosting/README.md").read_text()
        self.assertIn("NOT DEPLOYED", docs)
        self.assertIn("separately owner-approved identity", docs)
        self.assertIn("unauthenticated", docs)
        self.assertIn("preview/version", docs)

    def test_no_public_route_or_preview(self):
        config = json.loads(re.sub(r"(?m)^\s*//.*$", "", CONFIG.read_text()))
        self.assertIs(config["workers_dev"], False)
        self.assertIs(config["preview_urls"], False)
        self.assertNotIn("routes", config)
        self.assertNotIn("route", config)

    def test_rejects_preview_activation(self):
        changed = CONFIG.read_text().replace('"preview_urls": false', '"preview_urls": true')
        with patch.object(Path, "read_text", autospec=True) as reader:
            original = Path.read_text
            reader.side_effect = lambda path, *args, **kwargs: changed if path == CONFIG else original(path, *args, **kwargs)
            self.assertTrue(any("preview_urls" in x for x in check()))

    def test_rejects_worker_public_hostname(self):
        changed = CONFIG.read_text().replace('"workers_dev": false', '"workers_dev": true')
        with patch.object(Path, "read_text", autospec=True) as reader:
            original = Path.read_text
            reader.side_effect = lambda path, *args, **kwargs: changed if path == CONFIG else original(path, *args, **kwargs)
            self.assertTrue(any("workers_dev" in x for x in check()))


if __name__ == "__main__":
    unittest.main()
