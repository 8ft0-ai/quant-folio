#!/usr/bin/env python3
"""One-week isolated historical backfill; never uses production publication state."""
import argparse
import datetime as dt
import os
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from scout import API, SEARCH, parse_atom
from curate import DEFAULT_MODEL, candidates_for_run, assess_batches, render, atomic_write

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
        for paper in entries:
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=dt.date.fromisoformat, default=dt.date(2026, 10, 12))
    parser.add_argument("--end", type=dt.date.fromisoformat, default=dt.date(2026, 10, 18))
    parser.add_argument("--output", type=Path, default=Path("reports/2026-10-18.md"))
    args = parser.parse_args()
    if (args.start, args.end) != (dt.date(2026,10,12), dt.date(2026,10,18)):
        parser.error("V1 is fixed to 12–18 October 2026")
    if args.output.resolve() == Path("reports/2026-10-25.md").resolve():
        parser.error("cannot overwrite production report")
    papers, retrieved = fetch_historical(args.start, args.end)
    candidates, eligible_ids = candidates_for_run(papers, set(), args.end, 6, 24)
    if candidates:
        selected, usage = assess_batches(candidates, 8, DEFAULT_MODEL,
                                          os.environ.get("OPENROUTER_API_KEY"))
    else:
        selected, usage = [], {}
    generation = dt.datetime.now(dt.timezone.utc).date()
    report = build_report(papers, retrieved, args.start, args.end, generation, selected)
    # Validate all links and IDs before any output.
    for paper, _, _ in selected:
        assert paper["url"] == "https://arxiv.org/abs/" + paper["id"]
        assert report.count("](" + paper["url"] + ")") >= 2
    atomic_write(args.output, report)
    print(f"retrieved={retrieved} eligible={len(eligible_ids)} assessed={len(candidates)} "
          f"recommended={len(selected)} prompt_tokens={usage.get('prompt_tokens',0)} "
          f"completion_tokens={usage.get('completion_tokens',0)}")
    print("recommended_ids=" + ",".join(p["id"] for p,_,_ in selected))

if __name__ == "__main__":
    main()
