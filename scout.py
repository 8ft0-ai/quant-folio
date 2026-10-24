#!/usr/bin/env python3
"""Quant Folio: bounded, reproducible arXiv research shortlist (stdlib only)."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"
ID_RE = re.compile(r"^(?:\d{4}\.\d{4,5}|[a-z.-]+/\d{7})$", re.I)
TOPICS = {
    "forecast": 4, "trading": 4, "portfolio": 4, "financial": 3,
    "market": 3, "execution": 4, "microstructure": 5, "risk": 2,
    "volatility": 3, "asset pricing": 3, "reinforcement learning": 2,
    "time series": 2, "return prediction": 4, "order book": 5,
    "foreign exchange": 5, "factor model": 3, "backtest": 2,
}
SEARCH = "(cat:q-fin.TR OR cat:q-fin.PM OR cat:q-fin.ST OR cat:q-fin.CP OR cat:q-fin.MF)"
API = "https://export.arxiv.org/api/query"


def clean(s):
    return " ".join((s or "").split())


def parse_atom(data):
    root = ET.fromstring(data)
    if root.tag != ATOM + "feed":
        raise ValueError("Not an Atom feed")
    entries = []
    for e in root.findall(ATOM + "entry"):
        url = clean(e.findtext(ATOM + "id"))
        paper_id = url.rstrip("/").split("/")[-1].split("v")[0]
        if not ID_RE.fullmatch(paper_id):
            continue
        title = clean(e.findtext(ATOM + "title"))
        abstract = clean(e.findtext(ATOM + "summary"))
        published = clean(e.findtext(ATOM + "published"))
        if not title or not abstract or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*", published):
            continue
        entries.append({"id": paper_id, "title": title, "abstract": abstract,
                        "published": published[:10], "url": "https://arxiv.org/abs/" + paper_id})
    return entries


def fetch(limit):
    params = urlencode({"search_query": SEARCH, "start": 0, "max_results": limit,
                        "sortBy": "submittedDate", "sortOrder": "descending"})
    request = Request(API + "?" + params, headers={"User-Agent": "QuantFolio/0.1 (research shortlist)"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=25) as response:
                return parse_atom(response.read(5_000_000))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def rank(paper):
    text = (paper["title"] + " " + paper["abstract"]).lower()
    score = sum(weight for phrase, weight in TOPICS.items() if phrase in text)
    matching = [phrase for phrase in TOPICS if phrase in text]
    return score, matching


def build(entries, seen, today, window, limit):
    earliest = today - dt.timedelta(days=window)
    unique = {}
    for p in entries:
        date = dt.date.fromisoformat(p["published"])
        if earliest <= date <= today and p["id"] not in seen:
            unique.setdefault(p["id"], p)
    scored = [(rank(p)[0], p) for p in unique.values()]
    scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    selection = [(s, p) for s, p in scored if s >= 4][:limit]
    title = "# Quant Folio — " + today.isoformat()
    lines = [title, "", "Automated abstract-level triage, not independent validation.",
             "Search: arXiv quantitative-finance categories. Retrieval is capped and is **not exhaustive**.",
             "Claims about trading performance, replication and implementation are **not verified**.", ""]
    if not selection:
        lines += ["No new papers met this week's preliminary relevance threshold.", ""]
    for i, (score, p) in enumerate(selection, 1):
        matching = rank(p)[1]
        lines += [f"## {i}. [{p['title']}]({p['url']})",
                  f"**arXiv:** {p['id']} · **Submitted:** {p['published']} · **Evidence:** abstract only",
                  "Why it may be relevant: " + ", ".join(matching[:5]) + ".",
                  "Assessment: automated keyword-based triage only; read the paper before relying on its claims.", ""]
    lines += [f"**New unique candidates in window:** {len(unique)} · **Recommended:** {len(selection)}",
              "No evidence of research effectiveness or absence of relevant papers outside the bounded search is implied.", ""]
    # Only seen IDs actually retrieved within the date window; do not mark excluded older papers.
    return "\n".join(lines), seen | set(unique), len(selection)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, help="Offline Atom XML for deterministic testing")
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.datetime.now(dt.timezone.utc).date())
    parser.add_argument("--state", type=Path, default=Path("data/seen.json"))
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    parser.add_argument("--window", type=int, default=8)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--fetch-limit", type=int, default=200)
    args = parser.parse_args()
    if not (1 <= args.window <= 31 and 1 <= args.limit <= 20 and 1 <= args.fetch_limit <= 500):
        parser.error("invalid bounded limits")
    state = json.loads(args.state.read_text()) if args.state.exists() else {"seen": []}
    seen = set(state["seen"])
    papers = parse_atom(args.fixture.read_bytes()) if args.fixture else fetch(args.fetch_limit)
    report, updated, count = build(papers, seen, args.today, args.window, args.limit)
    output = args.reports / (args.today.isoformat() + ".md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps({"seen": sorted(updated)}, indent=2) + "\n", encoding="utf-8")
    print(f"report={output} fetched={len(papers)} recommendations={count} seen={len(updated)}")


if __name__ == "__main__":
    main()
