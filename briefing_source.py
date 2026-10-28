#!/usr/bin/env python3
"""Read-only, dependency-free source checks for the ChatGPT editorial briefing skill.

No inference, report publication, seen-state reads/writes or external paper fetches.
"""
import argparse
import base64
from collections import Counter
import datetime as dt
import hashlib
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = "8ft0-ai/quant-folio"
API = f"https://api.github.com/repos/{REPO}"
REPORT_PATH = re.compile(r"^reports/(\d{4}-\d{2}-\d{2})\.md$")
DETAIL = re.compile(
    r"^###\s+\d+\.\s+\[([^\]\n]+)\]\((https://arxiv\.org/abs/(\d{4}\.\d{4,5}))\)\s*$",
    re.M,
)
COUNT_ROW = re.compile(
    r"^\*\*Retrieved:\*\* (.*?) · \*\*New unique:\*\* (.*?) · "
    r"\*\*AI-assessed:\*\* (.*?) · \*\*Shortlisted:\*\* (.*?)\s*$", re.M,
)


class SourceError(ValueError):
    """The report cannot be presented as verified source material."""


def github_json(url):
    request = Request(url, headers={
        "User-Agent": "quant-folio-read-only-briefing/1",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urlopen(request, timeout=12) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise SourceError(f"GitHub source unavailable: {exc}") from exc


def _date(value):
    try:
        return dt.date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise SourceError(f"Invalid ISO report date: {value!r}") from exc


def _metric(value):
    if value == "Not recorded in original report":
        return None
    if re.fullmatch(r"\d+", value):
        return int(value)
    raise SourceError(f"Unrecognised metric: {value!r}")


def inspect_report(markdown, report_date, commit_sha, as_of=None, focus=None):
    """Validate a main-commit Markdown report without consulting mutable state."""
    requested = _date(report_date)
    as_of = _date(as_of) if isinstance(as_of, str) else (as_of or dt.date.today())
    if requested > as_of:
        raise SourceError("Report date is in the future relative to as-of date")
    heading = re.search(
        r"^# Quant Folio — Research intelligence briefing · (\d{4}-\d{2}-\d{2})\s*$",
        markdown, re.M,
    )
    if not heading or heading.group(1) != report_date:
        raise SourceError("Report heading/date does not match its path")
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise SourceError("Missing immutable GitHub commit identity")
    count_match = COUNT_ROW.search(markdown)
    keys = ("retrieved", "new_unique", "ai_assessed", "shortlisted")
    counts = dict(zip(keys, map(_metric, count_match.groups()))) if count_match else dict.fromkeys(keys)
    warnings = []
    if not count_match or any(v is None for v in counts.values()):
        warnings.append("Some retrieval/assessment counts are not recorded; do not estimate them.")
    if all(counts[k] is not None for k in ("retrieved", "new_unique")) and counts["new_unique"] > counts["retrieved"]:
        raise SourceError("New-unique count exceeds retrieval count")
    if all(counts[k] is not None for k in ("new_unique", "ai_assessed")) and counts["ai_assessed"] > counts["new_unique"]:
        raise SourceError("Assessed count exceeds new-unique count")

    matches = list(DETAIL.finditer(markdown))
    papers = []
    for i, match in enumerate(matches):
        chunk = markdown[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(markdown)]
        metadata = re.search(r"^\*\*([^*\n]+)\*\* · arXiv (\d{4}\.\d{4,5}) · (\d{4}-\d{2}-\d{2}) · ([^\n]+)", chunk, re.M)
        if not metadata or metadata.group(2) != match.group(3):
            raise SourceError(f"Missing or mismatched evidence metadata for {match.group(3)}")
        fields = {}
        for key, field in (("finding", "Finding / method"), ("relevance", "Why investigate"), ("open_question", "Open question")):
            found = re.search(r"^\| \*\*" + re.escape(field) + r"\*\* \| (.*?) \|\s*$", chunk, re.M)
            fields[key] = found.group(1) if found else None
        papers.append({
            "id": match.group(3), "title": match.group(1), "url": match.group(2),
            "category": metadata.group(1), "paper_date": metadata.group(3),
            "evidence": metadata.group(4).strip(), **fields,
        })
    ids = [p["id"] for p in papers]
    if len(ids) != len(set(ids)):
        raise SourceError("Duplicate paper identifiers in research details")
    if counts["shortlisted"] is not None and counts["shortlisted"] != len(papers):
        raise SourceError("Shortlisted count does not match unique detail papers")
    if not papers and counts["shortlisted"] != 0:
        warnings.append("No paper details available; do not construct a shortlist.")
    glance = re.search(r"^## 2\. Research at a glance\s*$(.*?)^## 3\. Research details", markdown, re.M | re.S)
    if papers and (not glance or set(re.findall(r"https://arxiv\.org/abs/(\d{4}\.\d{4,5})", glance.group(1))) != set(ids)):
        raise SourceError("Research-at-a-glance paper IDs do not match detail IDs")
    first = re.search(r"\*\*Investigate first \(shortlist order, not a quality ranking\):\*\*(.*?)\*\*Evidence:\*\*", markdown, re.S)
    if first and not set(re.findall(r"https://arxiv\.org/abs/(\d{4}\.\d{4,5})", first.group(1))).issubset(set(ids)):
        raise SourceError("Source shortlist references an unknown paper")

    historical = bool(re.search(r"HISTORICAL BACKFILL.*NON-PUBLISHED DRAFT", markdown, re.I))
    retrospective = "Retrospective formatting" in markdown
    edition_type = "historical-draft" if historical else ("retrospective-main-report" if retrospective else "main-report")
    if historical:
        warnings.append("HISTORICAL BACKFILL — NON-PUBLISHED DRAFT; never call this a weekly publication.")
    if retrospective:
        warnings.append("Retrospective formatting of existing recommendations, not a new assessment.")
    if (as_of - requested).days > 8:
        warnings.append(f"STALE: report is {(as_of - requested).days} days old; do not describe as this week's research.")
    warnings.append("Presence on main does not independently prove an automated weekly publication or paper correctness.")
    warnings.append("arXiv links are source references, not live-checked or independently verified results.")
    themes = re.search(r"^\*\*Themes in this shortlist:\*\* (.+)$", markdown, re.M)
    evidence_note = re.search(r"^\*\*Evidence:\*\* (.+)$", markdown, re.M)
    return {
        "repository": REPO, "branch": "main", "commit_sha": commit_sha,
        "report_path": f"reports/{report_date}.md", "report_date": report_date,
        "permalink": f"https://github.com/{REPO}/blob/{commit_sha}/reports/{report_date}.md",
        "sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        "edition_type": edition_type, "age_days": (as_of - requested).days,
        "project_focus": focus, "counts": counts,
        "themes_as_reported": themes.group(1) if themes else None,
        "categories_in_details": dict(Counter(p["category"] for p in papers)),
        "evidence_note": evidence_note.group(1) if evidence_note else None,
        "papers": papers, "warnings": warnings,
    }


def retrieve_report(date=None, as_of=None, focus=None, get=github_json):
    """Pin main before discovery/content retrieval; never use branch-relative raw files."""
    commit = get(f"{API}/commits/main")
    sha = commit.get("sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise SourceError("GitHub did not return a valid main commit")
    listing = get(f"{API}/contents/reports?ref={sha}")
    if not isinstance(listing, list):
        raise SourceError("GitHub report listing is unavailable")
    dates = sorted(m.group(1) for f in listing if (m := REPORT_PATH.fullmatch(f.get("path", ""))))
    if not dates:
        raise SourceError("No Markdown research reports found on main")
    target = date or dates[-1]
    _date(target)
    if target not in dates:
        raise SourceError(f"Report {target} not found on main; do not substitute another edition")
    file_data = get(f"{API}/contents/reports/{target}.md?ref={sha}")
    try:
        if file_data.get("encoding") != "base64":
            raise ValueError("not base64")
        raw = base64.b64decode(file_data["content"], validate=False)
        markdown = raw.decode("utf-8")
    except (KeyError, ValueError, UnicodeDecodeError, TypeError) as exc:
        raise SourceError("Report bytes unavailable or invalid") from exc
    manifest = inspect_report(markdown, target, sha, as_of=as_of, focus=focus)
    manifest["git_blob_sha"] = file_data.get("sha")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only GitHub report provenance and briefing input")
    parser.add_argument("--date", help="Explicit YYYY-MM-DD on main; default latest filename")
    parser.add_argument("--focus", help="Optional editorial focus, does not alter source facts")
    parser.add_argument("--as-of", help="ISO date for freshness checks (defaults to today's date)")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(retrieve_report(args.date, args.as_of, args.focus), indent=2, ensure_ascii=False))
    except SourceError as exc:
        print(f"SOURCE UNVERIFIED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
