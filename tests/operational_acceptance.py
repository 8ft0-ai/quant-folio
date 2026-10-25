#!/usr/bin/env python3
"""Isolated, non-publishing three-scenario operational acceptance."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import re
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


def report_ids(report):
    return set(re.findall(r"\\*\\*arXiv:\\*\\* ([^ \\n]+)", report))


def report_counts(report):
    match = re.search(r"\\*\\*AI-assessed candidates:\\*\\* (\\d+)\\s+· \\*\\*Recommended:\\*\\* (\\d+)", report)
    if not match:
        raise AssertionError("Missing report counts")
    return tuple(map(int, match.groups()))


def observed_execute(args, papers):
    observed = {}
    original = curate.assess_batches

    def capture(candidates, limit, model, api_key):
        result, usage = original(candidates, limit, model, api_key)
        observed["assessed_ids"] = sorted(p["id"] for p in candidates)
        observed["usage"] = usage
        return result, usage

    with patch.object(curate, "fetch", return_value=papers), patch.object(
        curate, "assess_batches", side_effect=capture
    ):
        report = curate.execute(args)
    observed.setdefault("assessed_ids", [])
    observed.setdefault("usage", {"prompt_tokens": 0, "completion_tokens": 0})
    observed["counts"] = report_counts(report)
    observed["recommended_ids"] = sorted(report_ids(report))
    assert len(observed["recommended_ids"]) == observed["counts"][1]
    return report, observed


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
    report1, obs1 = observed_execute(first, papers)
    assert "## 1." in report1, "Baseline had no recommendations"
    assert "**Assessment depth:** Abstract only." in report1
    assert "https://arxiv.org/abs/" in report1
    baseline_seen = ids(first.state)
    assert baseline_seen == set(obs1["assessed_ids"])
    assert baseline_seen == {p["id"] for p in eligible}

    second = args("run2")
    shutil.copyfile(first.state, second.state)
    expected2, _ = curate.candidates_for_run(papers, baseline_seen, today, 8, 10)
    report2, obs2 = observed_execute(second, papers)
    second_seen = ids(second.state)
    new_ids = set(obs2["assessed_ids"])
    assert new_ids == {p["id"] for p in expected2}
    assert new_ids.isdisjoint(baseline_seen), "Previously assessed paper reassessed"
    assert set(obs2["recommended_ids"]).isdisjoint(report_ids(report1)), "Duplicate recommendation"
    assert baseline_seen <= second_seen
    assert second_seen == baseline_seen | new_ids, "Incorrect state transition"
    assert obs2["counts"][0] == len(new_ids)
    if not expected2:
        assert obs2["counts"] == (0, 0)
        assert obs2["usage"] == {"prompt_tokens": 0, "completion_tokens": 0}
    # A truly exhausted input must produce a valid zero-candidate digest without inference.
    exhausted = args("exhausted")
    shutil.copyfile(second.state, exhausted.state)
    exhausted_seen = ids(exhausted.state)
    with patch.object(curate, "fetch", return_value=papers), patch.object(
        curate, "request_assessment", side_effect=AssertionError("inference on exhausted input")
    ):
        exhausted_report = curate.execute(exhausted)
    exhausted_candidates, _ = curate.candidates_for_run(papers, exhausted_seen, today, 8, 10)
    if not exhausted_candidates:
        assert report_counts(exhausted_report) == (0, 0)
        assert ids(exhausted.state) == exhausted_seen

    third = args("run3")
    report_path = third.reports / (today.isoformat() + ".md")
    before = (digest(third.state), digest(report_path))
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
    assert before == (digest(third.state), digest(report_path))
    print("run3_failed_state_and_digest=unchanged")
    report3, obs3 = observed_execute(third, papers)
    assert "## 1." in report3
    assert ids(third.state) == set(obs3["assessed_ids"]) == baseline_seen
    assert len(obs3["recommended_ids"]) == obs3["counts"][1]
    assert len(obs3["recommended_ids"]) == len(set(obs3["recommended_ids"]))
    summary = {
        "source_revision": os.environ.get("GITHUB_SHA", "local"),
        "model": MODEL, "arxiv_fetched": len(papers),
        "run1": {**obs1, "state_ids": sorted(baseline_seen), "report_sha256": digest(first.reports / (today.isoformat() + ".md"))},
        "run2": {**obs2, "state_ids_before": sorted(baseline_seen), "state_ids_after": sorted(second_seen),
                 "new_ids": sorted(new_ids), "report_sha256": digest(second.reports / (today.isoformat() + ".md"))},
        "empty_check": {"candidates": report_counts(exhausted_report)[0],
                        "state_unchanged": ids(exhausted.state) == exhausted_seen},
        "run3_fault": {"mode": "deterministic malformed-response injection",
                       "rejected": True, "state_and_digest_unchanged": True},
        "run3_recovery": {**obs3, "state_ids": sorted(ids(third.state)),
                          "report_sha256": digest(report_path), "inference": "live provider"},
        "publication": "disabled", "schedule": "disabled"
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("ACCEPTANCE_SCENARIOS_COMPLETED", json.dumps(summary))


if __name__ == "__main__":
    root = Path(os.environ.get("ACCEPTANCE_DIR", "/tmp/quant-folio-acceptance"))
    root.mkdir(parents=True, exist_ok=True)
    run(root)
