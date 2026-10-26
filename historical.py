#!/usr/bin/env python3
"""One-week isolated historical backfill; never uses production publication state."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from scout import API, SEARCH, ATOM, parse_atom
from curate import DEFAULT_MODEL, BATCH_SIZE, BATCH_RECOMMENDATIONS, MAX_ABSTRACT, MAX_RESPONSE_TOKENS, candidates_for_run, assess_batches, render

OS = "{http://a9.com/-/spec/opensearch/1.1/}"
PAGE = 100
MAX_RETRIEVED = 2000

def query_for_dates(start, end):
    if start > end:
        raise ValueError("start exceeds end")
    # arXiv submittedDate uses UTC timestamps, inclusive endpoints.
    return f"submittedDate:[{start:%Y%m%d}0000 TO {end:%Y%m%d}2359] AND {SEARCH}"

def fetch_historical(start, end, opener=urlopen, pause=time.sleep):
    query = query_for_dates(start, end)
    unique = {}
    expected = None
    fetched_raw = 0
    for offset in range(0, MAX_RETRIEVED, PAGE):
        params = urlencode({"search_query": query, "start": offset, "max_results": PAGE,
                            "sortBy": "submittedDate", "sortOrder": "ascending"})
        request = Request(API + "?" + params, headers={"User-Agent": "QuantFolio/0.1 (historical research)"})
        with opener(request, timeout=35) as response:
            raw = response.read(5_000_000)
        root = ET.fromstring(raw)
        if root.tag != "{http://www.w3.org/2005/Atom}feed":
            raise ValueError("Invalid arXiv feed")
        count = int(root.findtext(OS + "totalResults", default="-1"))
        if count < 0 or (expected is not None and expected != count):
            raise ValueError("Missing or inconsistent arXiv result count")
        expected = count
        entries = parse_atom(raw)
        source_entries = len(root.findall("{http://www.w3.org/2005/Atom}entry"))
        if source_entries != len(entries):
            raise ValueError("Unparseable arXiv source entries; refusing incomplete coverage")
        fetched_raw += source_entries
        for paper, entry in zip(entries, root.findall(ATOM + "entry")):
            source_id = (entry.findtext(ATOM + "id") or "").strip()
            paper["source_id"] = source_id
            paper["source_version"] = (re.search(r"v(\d+)$", source_id).group(1)
                                       if re.search(r"v(\d+)$", source_id) else None)
            paper["updated"] = (entry.findtext(ATOM + "updated") or "").strip() or None
            if not start <= dt.date.fromisoformat(paper["published"]) <= end:
                raise ValueError("arXiv returned paper outside submitted-date coverage")
            unique.setdefault(paper["id"], paper)
        if fetched_raw >= count:
            break
        if not source_entries:
            raise ValueError("Incomplete paginated historical retrieval")
        if offset + PAGE >= MAX_RETRIEVED:
            raise ValueError("Historical search exceeds safety cap; no partial report")
        pause(3)
    if fetched_raw != expected:
        raise ValueError(f"Historical results incomplete: {fetched_raw}/{expected}")
    return list(unique.values()), fetched_raw

def build_report(papers, retrieved, start, end, generation_date, selected):
    eligible = len({p["id"] for p in papers})
    report = render(end, selected, min(24, len(candidates_for_run(papers, set(), end, (end-start).days, 24)[0])),
                    eligible, DEFAULT_MODEL, fetched_count=retrieved)
    header = (f"**HISTORICAL BACKFILL — NON-PUBLISHED DRAFT**  \n"
              f"**Submission coverage (UTC):** {start.isoformat()}–{end.isoformat()} inclusive  \n"
              f"**Generated:** {generation_date.isoformat()} UTC  \n"
              f"**Source:** arXiv API, submittedDate, q-fin.TR/PM/ST/CP/MF; "
              f"paginated in ascending submission order.  \n"
              f"**Coverage limitation:** arXiv's current indexed records, not a snapshot of "
              f"what was visible during that week; subsequent revisions or withdrawals "
              f"can change results. Retrieval covers these categories only.  \n"
              f"**Deduplication:** independent historical identity set; production seen-state ignored.\n")
    report = report.replace("## 1. Executive briefing", header + "\n## 1. Executive briefing", 1)
    return report

def reporting_week(ending, now=None):
    """Validate a finished UTC Monday–Sunday research week."""
    today = now or dt.datetime.now(dt.timezone.utc).date()
    if ending.weekday() != 6:
        raise ValueError("week ending must be Sunday")
    if ending >= today:
        raise ValueError("week must be completed before today (UTC)")
    if ending < dt.date(1991, 1, 6):
        raise ValueError("week predates arXiv")
    return ending - dt.timedelta(days=6), ending


def output_paths(ending, output=None):
    """Protect all existing outputs; allow only the canonical report basename."""
    canonical = f"{ending.isoformat()}.md"
    report = Path(output) if output else Path("reports") / canonical
    if report.name != canonical or report.is_symlink():
        raise ValueError("output must be a non-symlink canonical weekly report filename")
    manifest = report.with_suffix(".provenance.json")
    if manifest.is_symlink() or report.exists() or manifest.exists():
        raise FileExistsError("historical output already exists; use an empty output directory")
    return report, manifest


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def provenance(papers, retrieved, start, end, timestamp, candidates, eligible_ids,
               selected, report):
    """Canonical ordered JSON content; retrieval timestamp is intentionally variable."""
    records = []
    for p in sorted(papers, key=lambda x: x["id"]):
        abstract = p["abstract"].encode("utf-8")
        metadata = {k: p.get(k) for k in
                    ("id", "source_id", "source_version", "updated", "published", "title", "url")}
        records.append({**metadata, "metadata_sha256": sha256(
            json.dumps(metadata, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8")),
                        "abstract_sha256": sha256(abstract)})
    return {
        "schema": "quant-folio-historical-provenance-v2",
        "coverage": {"start_utc": start.isoformat(), "end_utc": end.isoformat(),
                     "inclusive": True},
        "retrieved_at_utc": timestamp.isoformat().replace("+00:00", "Z"),
        "source": {"api": API, "query": query_for_dates(start, end),
                   "sort_by": "submittedDate", "sort_order": "ascending",
                   "page_size": PAGE, "max_results": MAX_RETRIEVED,
                   "limitations": "Current mutable arXiv index; not an immutable historical snapshot. Source versions are recorded only where returned by Atom."},
        "counts": {"retrieved": retrieved, "unique": len(papers),
                   "eligible": len(eligible_ids), "assessed": len(candidates),
                   "recommended": len(selected)},
        "papers": records,
        "eligible_ids": sorted(eligible_ids),
        "assessed_ids": [p["id"] for p in candidates],
        "recommended_ids": [p["id"] for p, _, _ in selected],
        "assessment": {"model": DEFAULT_MODEL, "temperature": 0,
                       "batch_size": BATCH_SIZE,
                       "batch_recommendations": BATCH_RECOMMENDATIONS,
                       "maximum_assessed": 24, "maximum_recommended": 8,
                       "maximum_abstract_chars": MAX_ABSTRACT,
                       "maximum_response_tokens": MAX_RESPONSE_TOKENS,
                       "reasoning_effort": "low"},
        "report_sha256": sha256(report.encode("utf-8")),
        "checksum_encoding": "UTF-8 SHA-256; metadata canonical JSON with sorted keys and compact separators; abstracts as received after parse_atom whitespace normalisation."
    }


def write_pair_new(report_path, manifest_path, report, manifest):
    """Exclusive new-file writes; existing outputs are never overwritten."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payloads = ((report_path, report), (manifest_path, json.dumps(
        manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"))
    created = []
    try:
        for path, content in payloads:
            with path.open("x", encoding="utf-8") as target:
                created.append(path)
                target.write(content)
    except BaseException:
        for path in created:
            path.unlink()
        raise


def main():
    parser = argparse.ArgumentParser(description="Isolated manual historical research backfill")
    parser.add_argument("--week-ending", required=True, type=dt.date.fromisoformat,
                        help="completed Sunday YYYY-MM-DD (UTC)")
    parser.add_argument("--output", type=Path, help="optional canonical report path in a new directory")
    args = parser.parse_args()
    try:
        start, end = reporting_week(args.week_ending)
        output, manifest_path = output_paths(end, args.output)
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    papers, retrieved = fetch_historical(start, end)
    candidates, eligible_ids = candidates_for_run(papers, set(), end, 6, 24)
    if candidates:
        selected, usage = assess_batches(candidates, 8, DEFAULT_MODEL,
                                          os.environ.get("OPENROUTER_API_KEY"))
    else:
        selected, usage = [], {}
    timestamp = dt.datetime.now(dt.timezone.utc)
    report = build_report(papers, retrieved, start, end, timestamp.date(), selected)
    for paper, _, _ in selected:
        if paper["url"] != "https://arxiv.org/abs/" + paper["id"]:
            raise ValueError("Invalid selected source identity")
        if report.count("](" + paper["url"] + ")") < 2:
            raise ValueError("Report omits selected source links")
    manifest = provenance(papers, retrieved, start, end, timestamp, candidates,
                          eligible_ids, selected, report)
    write_pair_new(output, manifest_path, report, manifest)
    print(f"report={output} provenance={manifest_path}")
    print(f"retrieved={retrieved} eligible={len(eligible_ids)} assessed={len(candidates)} "
          f"recommended={len(selected)} prompt_tokens={usage.get('prompt_tokens',0)} "
          f"completion_tokens={usage.get('completion_tokens',0)}")
    print("recommended_ids=" + ",".join(p["id"] for p, _, _ in selected))

if __name__ == "__main__":
    main()
