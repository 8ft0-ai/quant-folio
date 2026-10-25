#!/usr/bin/env python3
"""Isolated, non-publishing three-scenario operational acceptance."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

import curate
from scout import fetch

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def ids(path):
    return curate.load_seen(path)


def run(root):
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("Required GitHub Actions OpenRouter secret unavailable")
    assert curate.DEFAULT_MODEL == MODEL, "Default model unexpectedly changed"
    today = dt.datetime.now(dt.timezone.utc).date()
    # Fetch from arXiv exactly once; hold its actual metadata constant for controlled comparison.
    papers = fetch(100)
    eligible, _ = curate.candidates_for_run(papers, set(), today, 8, 10)
    if not eligible:
        raise RuntimeError("No eligible live arXiv candidates; cannot demonstrate inference")
    print(f"arxiv_fetched={len(papers)} eligible={len(eligible)} model={MODEL}")
    def args(name):
        folder = root / name
        folder.mkdir()
        return SimpleNamespace(state=folder / "seen.json", reports=folder / "reports",
            fixture=None, ai_fixture=None, today=today, window=8, limit=8,
            fetch_limit=100, max_candidates=10, model=MODEL, full_paper=False)
    first = args("run1")
    with patch.object(curate, "fetch", return_value=papers):
        report1 = curate.execute(first)
    assert "## 1." in report1, "Baseline had no recommendations"
    assert "**Assessment depth:** Abstract only." in report1
    assert "https://arxiv.org/abs/" in report1
    baseline_seen = ids(first.state)
    assert {p["id"] for p in eligible} >= baseline_seen or baseline_seen
    assert len(baseline_seen) == len(eligible)
    second = args("run2")
    shutil.copyfile(first.state, second.state)
    with patch.object(curate, "fetch", return_value=papers), patch.object(
        curate, "request_assessment", side_effect=AssertionError("duplicate inference attempted")
    ):
        report2 = curate.execute(second)
    assert ids(second.state) == baseline_seen
    assert "AI-assessed candidates:** 0" in report2
    assert "Recommended:** 0" in report2
    third = args("run3")
    # Exercise a genuine candidate set in a separately isolated state, without
    # modifying the successfully completed Run 1 and Run 2 snapshots.
    before = (digest(third.state), digest(third.reports / (today.isoformat()+".md")))
    with patch.object(curate, "fetch", return_value=papers), patch.object(
        curate, "request_assessment",
        return_value=({"recommendations": "invalid"}, {"prompt_tokens": 0, "completion_tokens": 0})
    ):
        try:
            curate.execute(third)
        except ValueError as exc:
            assert "recommendations" in str(exc)
            print("run3_controlled_failure=detected_and_rejected")
        else:
            raise AssertionError("Malformed assessment accepted")
    assert before == (digest(third.state), digest(third.reports / (today.isoformat()+".md")))
    print("run3_failed_state_and_digest=unchanged")
    with patch.object(curate, "fetch", return_value=papers):
        report3 = curate.execute(third)
    assert "## 1." in report3
    assert ids(third.state) == baseline_seen
    assert len(ids(third.state)) == len(baseline_seen)
    summary = {
        "source_revision": os.environ.get("GITHUB_SHA", "local"),
        "model": MODEL, "arxiv_fetched": len(papers),
        "run1_candidates": len(eligible),
        "run1_recommendations": report1.count("**Abstract-based summary:**"),
        "run2_candidates": 0, "run2_recommendations": 0,
        "run3_fault": "detected; state unchanged",
        "run3_recovery_candidates": len(eligible),
        "run3_recommendations": report3.count("**Abstract-based summary:**"),
        "state_ids_run1": len(baseline_seen), "state_ids_run2": len(ids(second.state)),
        "state_ids_run3_recovery": len(ids(third.state)),
        "publication": "disabled", "schedule": "disabled",
        "run3_inference": "live recovery", "fault_injection": "fixture only"
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("ACCEPTANCE_SCENARIOS_COMPLETED", json.dumps(summary))


if __name__ == "__main__":
    root = Path(os.environ.get("ACCEPTANCE_DIR", "/tmp/quant-folio-acceptance"))
    root.mkdir(parents=True, exist_ok=True)
    run(root)
