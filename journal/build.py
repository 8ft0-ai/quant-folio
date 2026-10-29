#!/usr/bin/env python3
"""Build a static, evidence-checked private journal preview. Never deploys or calls APIs."""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from briefing_source import SourceError, inspect_report  # noqa: E402
from journal import deep_assessment  # noqa: E402

JOURNAL = ROOT / "journal"
CONFIG = JOURNAL / "editorial.json"
OUTPUT = JOURNAL / "site" / "index.html"
EVIDENCE = JOURNAL / "evidence_review.json"
ANALYSIS = JOURNAL / "analysis" / "2026-10-25.json"

def confirm_git_source(date: str, sha: str, blob_sha: str, raw: str) -> None:
    """Validate commit/tree/blob membership locally; no mutable branch or network access."""
    rel = f"reports/{date}.md"
    try:
        blob = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", f"{sha}:{rel}"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        actual = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{sha}:{rel}"],
            check=True, capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SourceError("Pinned Git commit or report unavailable: full Git history is required") from exc
    if blob != blob_sha or actual != raw.encode("utf-8"):
        raise SourceError("Pinned Git commit does not contain the reviewed report blob/bytes")

def review_editorial(config: dict, papers: list[dict]) -> None:
    """Validate reviewed editorial text against its explicit source anchors.

    This is traceability, not machine semantic fact checking or scientific replication.
    """
    contract = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    lookup = {p["id"]: p for p in papers}
    selections = {p["id"]: p for p in config["priorities"]}
    if contract.get("source_commit") != config["source_main_sha"] or contract.get("source_blob") != config["report_git_blob_sha"]:
        raise SourceError("Evidence review provenance does not match the pinned source")
    entries = contract["priority_papers"]
    if set(entries) != set(selections) or len(entries) != 3:
        raise SourceError("Evidence contract has missing or extra priority paper identities")
    for paper_id, record in entries.items():
        source = lookup[paper_id]
        editorial = selections[paper_id]
        for field, key in (("finding", "finding_anchor"), ("relevance", "relevance_anchor"),
                           ("open_question", "open_question_anchor")):
            anchor = record.get(key)
            if not isinstance(anchor, str) or len(anchor) < 15 or anchor not in (source[field] or ""):
                raise SourceError(f"Evidence anchor mismatch for {paper_id}: {field}")
        for field in ("summary", "limitation"):
            digest = hashlib.sha256(editorial[field].encode("utf-8")).hexdigest()
            if digest != record.get(field + "_sha256"):
                raise SourceError(f"Editorial {field} changed without source-to-render review: {paper_id}")

def load_analysis(config: dict, papers: list[dict]) -> dict[str, dict]:
    """Optional pinned editorial enrichment; invalid/missing input falls back safely."""
    try:
        record = json.loads(ANALYSIS.read_text(encoding="utf-8"))
        if record["schema"] != "quant-folio-research-analysis-v1":
            return {}
        if record["edition"] != config["edition"] or record["source_commit"] != config["source_main_sha"]:
            return {}
        if record["source_report_sha256"] != config["report_sha256"]:
            return {}
        if record["prompt_version"] != "research-analysis-v1.0":
            return {}
        gen = record["generation"]
        if gen["method"] != "chatgpt-assisted-editorial-draft" or gen["external_provider_calls"] != 0:
            return {}
        expected = {p["id"]: p for p in papers}
        priorities = {p["id"] for p in config["priorities"]}
        result = {}
        allowed = {"method", "claim", "relevance", "limitations", "falsification"}
        for item in record["assessments"]:
            ident = item["id"]
            if ident not in priorities or ident in result:
                return {}
            if item["source_url"] != expected[ident]["url"] or item["title"] != expected[ident]["title"]:
                return {}
            for field, name in (("finding", "source_finding_sha256"),
                                ("relevance", "source_relevance_sha256"),
                                ("open_question", "source_open_question_sha256")):
                if item.get(name) != hashlib.sha256(expected[ident][field].encode("utf-8")).hexdigest():
                    return {}
            if item["source_scope"] != "pinned-report-abstract-summary-only":
                return {}
            if item["independent_verification"] != "none":
                return {}
            if item["evidence_status"] != "author-reported-and-analytical-interpretation":
                return {}
            if any(not isinstance(item.get(k), str) or not item[k].strip() for k in allowed):
                return {}
            result[ident] = item
        return result if set(result) == priorities else {}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def render_analysis(item: dict | None) -> str:
    if not item:
        return ""
    fields = (("Method", "method"), ("Author-reported findings", "claim"),
              ("Potential research relevance", "relevance"),
              ("Paper-specific limitations", "limitations"),
              ("Proposed falsification — not executed", "falsification"))
    detail = "".join(f'<section class="analysis-part"><h4>{e(label)}</h4><p>{e(item[key])}</p></section>'
                     for label, key in fields)
    return (f'<details class="research-analysis"><summary>AI Research Assessment'
            f'<span>ABSTRACT-LEVEL · UNVERIFIED</span></summary>'
            f'<div class="analysis-body"><p class="analysis-warning">AI-assisted editorial interpretation of the pinned report, '
            f'not independent paper review, experimental evidence or trading advice.</p>{detail}'
            f'<p class="analysis-source">SOURCE · {e(item["source_scope"])} · '
            f'{e(item["paper_version"])} · independent verification: none</p></div></details>')


def e(value: object) -> str:
    return html.escape(str(value), quote=True)

def a(url: str, title: str, cls: str = "") -> str:
    return f'<a href="{e(url)}" class="{e(cls)}" target="_blank" rel="noopener noreferrer">{e(title)}<span aria-hidden="true"> ↗</span></a>'

def build() -> str:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    date = config["edition"]
    sha = config["source_main_sha"]
    report = ROOT / "reports" / f"{date}.md"
    raw = report.read_text(encoding="utf-8")
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if digest != config["report_sha256"]:
        raise SourceError("Pinned editorial source checksum mismatch; refusing to render")
    # Use the repository's existing source validator, without fetching papers or running AI.
    source = inspect_report(raw, date, sha, as_of=dt.date.fromisoformat(date))
    if source["edition_type"] == "historical-draft":
        raise SourceError("Historical draft cannot be presented as a normal weekend edition")
    if source["edition_type"] != "retrospective-main-report":
        raise SourceError("Unexpected edition classification; editorial review required")
    papers = source["papers"]
    lookup = {p["id"]: p for p in papers}
    if len(papers) != 8 or source["counts"] != {
        "retrieved": None, "new_unique": 31, "ai_assessed": 24, "shortlisted": 8
    }:
        raise SourceError("The October reference edition's paper set or counts changed")
    priority_ids = [v["id"] for v in config["priorities"]]
    if len(set(priority_ids)) != 3 or any(pid not in lookup for pid in priority_ids):
        raise SourceError("Priority identities must be three distinct source paper IDs")
    if len(config["themes"]) != 3 or {t["category"] for t in config["themes"]} != set(source["categories_in_details"]):
        raise SourceError("Theme categories must reconcile with report")
    confirm_git_source(date, sha, config["report_git_blob_sha"], raw)
    review_editorial(config, papers)
    if any("<" in x for x in (config["headline"], config["standfirst"])):
        raise SourceError("Editorial text contains HTML and must be escaped")

    others = [p for p in papers if p["id"] not in priority_ids]
    categories = source["categories_in_details"]
    report_link = source["permalink"]
    date_display = dt.date.fromisoformat(date).strftime("%-d %B %Y")
    date_short = dt.date.fromisoformat(date).strftime("%d.%m.%Y")

    metrics = [
        ("31", "NEW UNIQUE", "Papers identified", "01"),
        ("24", "AI-ASSESSED", "Abstracts screened", "02"),
        ("08", "SHORTLISTED", "To investigate", "03"),
        ("—", "RETRIEVED", "Not recorded", "04"),
    ]
    metric_markup = "\n".join(
        f'<article class="metric"><span class="metric-kicker">{e(i)} / {e(label)}</span>'
        f'<strong>{e(value)}</strong><span class="metric-caption">{e(caption)}</span></article>'
        for value, label, caption, i in metrics
    )

    theme_markup = "\n".join(
        f'<article class="theme-card theme-{i}"><span class="theme-top"><span class="theme-index">0{i + 1}</span>'
        f'<span class="theme-count">{categories[t["category"]]} / {len(papers)} PAPERS</span></span>'
        f'<h3>{e(t["short"])}</h3><p>{e(t["desc"])}</p>'
        f'<div class="theme-meter"><span style="width:{categories[t["category"]] * 100 / len(papers):.1f}%"></span></div>'
        f'<span class="theme-category">{e(t["category"])}</span></article>'
        for i, t in enumerate(config["themes"])
    )

    def paper_category(c: str) -> str:
        return {"Market microstructure": "micro", "Portfolio and risk": "risk", "Signals and filtering": "signal"}[c]

    analyses = load_analysis(config, papers)
    deep_ready = deep_assessment.load() is not None
    features = []
    for i, v in enumerate(config["priorities"], 1):
        p = lookup[v["id"]]
        deep_markup = ('<a href="./assessments/2610.25802.html" class="deep-full-link">Read full assessment <span aria-hidden="true">→</span></a>\n             ' if deep_ready and p["id"] == deep_assessment.PAPER_ID else "")
        features.append(f'''<article class="feature-card" id="paper-{e(p["id"])}">
          <div class="feature-overline"><span class="feature-number">0{i}</span>
          <span class="category-tag {paper_category(p["category"])}">{e(p["category"])}</span>
          <span class="evidence-tag">ABSTRACT ONLY</span></div>
          <div class="feature-grid"><div class="feature-main">
             <p class="feature-question">{e(v["headline"])}</p>
             <h3>{e(p["title"])}</h3>
             <p class="feature-summary">{e(v["summary"])}</p>
             {a(p["url"], "Read on arXiv", "text-link")}
             {deep_markup}<button type="button" class="small-action feature-copy" data-copy-prompt data-id="{e(p["id"])}"
               data-title="{e(p["title"])}" data-url="{e(p["url"])}">Copy ChatGPT research prompt ↗</button>
          </div><aside class="feature-context"><span class="side-label">EDITORIAL CONSIDERATION</span>
             <p>{e(p["relevance"] or "Source relevance not recorded.")}</p>
             <span class="side-label limit-label">EVIDENCE LIMITATION</span>
             <p>{e(v["limitation"])}</p>
             {render_analysis(analyses.get(p["id"]))}
             <details class="source-record"><summary>Compare original source wording</summary>
               <p><strong>Author-reported finding:</strong> {e(p["finding"] or "Not recorded.")}</p>
               <p><strong>Original open question:</strong> {e(p["open_question"] or "Not recorded.")}</p>
             </details>
             <span class="paper-id">{e(p["id"])} · {e(p["paper_date"])}</span>
          </aside></div></article>''')
    feature_markup = "\n".join(features)

    list_items = []
    for i, p in enumerate(others, 1):
        c = paper_category(p["category"])
        list_items.append(f'''<article class="paper-row" data-category="{e(c)}" id="paper-{e(p["id"])}">
          <div class="paper-row-main"><span class="paper-row-index">{i:02d} — {e(p["id"])}</span>
            <h3>{e(p["title"])}</h3>
            <p>{e(p["finding"] or "Finding not recorded.")}</p>
            <p class="source-question"><strong>Original open question:</strong> {e(p["open_question"] or "Not recorded.")}</p>
            <div class="paper-row-footer"><span class="category-tag {c}">{e(p["category"])}</span>
              <span class="evidence-tag">ABSTRACT ONLY</span></div>
          </div><div class="paper-row-actions">
            {a(p["url"], "View paper", "text-link")}
            <button type="button" class="small-action" data-copy-prompt data-id="{e(p["id"])}"
              data-title="{e(p["title"])}" data-url="{e(p["url"])}" aria-label="Copy research prompt for {e(p["title"])}">
              Copy research prompt <span aria-hidden="true">↗</span></button>
          </div></article>''')
    remainder_markup = "\n".join(list_items)

    theme_buttons = '<button class="filter-button active" type="button" data-filter="all" aria-pressed="true">All five</button>' + "\n" + "\n".join(
        f'<button class="filter-button" type="button" data-filter="{paper_category(t["category"])}" aria-pressed="false">{e(t["category"])}</button>'
        for t in config["themes"]
    )
    proposal = config["experiment"]

    # Security posture: deliberately no CDN, telemetry, third-party fonts, or secrets.
    return f'''<!doctype html>
<html lang="en-AU"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark"><meta name="referrer" content="no-referrer">
<title>Quant Folio — The October Notebook · {e(date_display)}</title>
<meta name="description" content="{e(config["standfirst"])}">
<link rel="stylesheet" href="./assets/styles.css">
<script src="./assets/app.js" defer></script></head>
<body data-edition="{e(date)}" data-report-url="{e(report_link)}">
<a href="#main-content" class="skip-link">Skip to the briefing</a>
<div id="reading-progress" role="progressbar" aria-label="Reading progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"></div>
<div class="app-layout">
<aside class="rail" aria-label="Journal navigation">
  <a href="#overview" class="brand" aria-label="Quant Folio, beginning of edition">
    <span class="brand-mark" aria-hidden="true">Q<span>.</span></span><span><strong>QUANT<br>FOLIO</strong><small>RESEARCH INTELLIGENCE</small></span>
  </a>
  <div class="rail-rule"></div><div class="rail-label">THIS EDITION</div>
  <div class="nav-scroll-shell">
  <nav class="rail-nav" aria-label="Sections (scrollable on narrow screens)" tabindex="0">
   <a class="active" href="#overview"><span>01</span> Overview</a>
   <a href="#landscape"><span>02</span> Research landscape</a>
   <a href="#priority"><span>03</span> Essential reading</a>
   <a href="#insight"><span>04</span> The bigger picture</a>
   <a href="#library"><span>05</span> Paper index</a>
   <a href="#sources"><span>06</span> Source &amp; evidence</a>
  </nav>
  <button class="nav-more" type="button" aria-label="Show more navigation sections" hidden>More <span aria-hidden="true">→</span></button>
  </div>
  <div class="rail-bottom"><span class="rail-bottom-kicker">THE READING ROOM</span>
    <p>A quiet place for serious research.</p>
    <div class="safety-pill"><span class="safety-dot"></span> LOCAL DESIGN PREVIEW</div>
    <small>Not an authenticated or deployed private site.</small>
  </div>
</aside>
<main class="main-content" id="main-content">
  <header class="topbar"><span>RESEARCH LETTER <span class="topbar-divider">/</span> NO. 001</span>
    <span class="topbar-right"><span class="dot"></span> {e(date_display.upper())} <span class="topbar-sep">·</span> READ-ONLY PREVIEW</span></header>

  <section class="hero section" id="overview" aria-labelledby="hero-heading">
    <div class="hero-copy">
      <span class="eyebrow"><span class="eyebrow-line"></span>{e(config["eyebrow"])}</span>
      <h1 id="hero-heading">{e(config["headline"])}</h1>
      <p class="hero-standfirst">{e(config["standfirst"])}</p>
      <div class="hero-meta"><span class="hero-badge">OCTOBER 2026</span><span>8 PAPERS</span><span>3 RESEARCH THEMES</span></div>
    </div>
    <div class="hero-visual" aria-hidden="true">
      <div class="art-caption">FIG. 01 / PROBABILISTIC MARKET STRUCTURE</div>
      <svg class="hero-svg" viewBox="0 0 560 440" fill="none" preserveAspectRatio="xMidYMid meet">
      <defs><linearGradient id="linea" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#8de4d7"/><stop offset=".55" stop-color="#50b5c8"/><stop offset="1" stop-color="#d9b474"/></linearGradient>
      <radialGradient id="glow"><stop stop-color="#55d3cb" stop-opacity=".23"/><stop offset="1" stop-color="#55d3cb" stop-opacity="0"/></radialGradient></defs>
      <circle cx="272" cy="226" r="220" fill="url(#glow)"/>
      <g stroke="#405263" stroke-opacity=".44" stroke-width=".65">
        <path d="M36 75H524M36 133H524M36 191H524M36 249H524M36 307H524M36 365H524"/>
        <path d="M79 38V402M159 38V402M239 38V402M319 38V402M399 38V402M479 38V402"/>
      </g>
      <g stroke="#6bbfc2" stroke-opacity=".18">
       <path d="M36 322C98 295 119 342 176 304S261 250 319 273 425 196 524 174" stroke-width="62"/>
       <path d="M36 320C98 291 119 344 176 306S261 254 319 269 425 196 524 174" stroke-width="29"/>
      </g>
      <g stroke="url(#linea)" stroke-width="1.9" stroke-linejoin="round">
       <path d="M36 322C98 295 119 342 176 304S261 250 319 273 425 196 524 174"/>
       <path d="M36 350C113 328 137 356 191 331S269 304 325 311 433 259 524 241" stroke-opacity=".44"/>
       <path d="M36 292C98 255 133 302 176 264S271 204 319 230 431 149 524 116" stroke-opacity=".6"/>
       <path d="M36 262C90 229 133 268 176 233S266 180 319 193 429 107 524 85" stroke-opacity=".32"/>
      </g>
      <g fill="#a6e7dd"><circle cx="319" cy="273" r="5"/><circle cx="319" cy="273" r="13" stroke="#91ded3" stroke-opacity=".27"/></g>
      <g fill="#b0bbc7" font-size="9" font-family="monospace" letter-spacing="1"><text x="36" y="28">STATE / 02.34</text><text x="409" y="420">TIME SERIES →</text><text x="34" y="414">T–240</text></g>
      </svg>
      <div class="art-footer"><span>STOCHASTIC SIGNAL</span><span>∞ / MODEL SPACE</span></div>
    </div>
  </section>

  <section class="snapshot section" aria-labelledby="snapshot-heading">
   <div class="section-top"><span class="section-num">I / THE BRIEFING</span><span class="section-top-right">A THREE-MINUTE READ</span></div>
   <div class="intro-grid"><div><h2 id="snapshot-heading" class="editorial-title">The signal<br><em>beneath the noise.</em></h2></div>
     <div class="intro-text"><p>{e(config["opening"])}</p>
      <p>The reported results are research leads, not independently reproduced findings. This edition curates existing October recommendations; it is not a new research assessment.</p>
      <div class="intro-takeaway"><span>THE EDITOR'S NOTE</span><strong>{e(config["takeaway"])}</strong></div>
     </div></div>
  </section>

  <section class="section" id="landscape" aria-labelledby="landscape-heading">
   <div class="section-top"><span class="section-num">II / THE RESEARCH LANDSCAPE</span><span class="section-top-right">SOURCE-REPORTED METRICS</span></div>
   <div class="section-heading"><h2 id="landscape-heading">The week <em>in numbers.</em></h2>
     <p>A bounded arXiv search and abstract-based assessment, not a census of quantitative finance.</p></div>
   <div class="metric-grid">{metric_markup}</div>
   <div class="fineprint">Raw retrieval volume was not recorded in the original report. The other numbers are source-reported and describe different pipeline stages.</div>
   <div class="theme-heading"><h3>Three strands of enquiry</h3><span>SHARE OF EIGHT SHORTLISTED PAPERS</span></div>
   <div class="theme-grid">{theme_markup}</div>
  </section>

  <section class="section" id="priority" aria-labelledby="priority-heading">
   <div class="section-top"><span class="section-num">III / THE EDITOR'S SELECTION</span><span class="section-top-right">3 PAPERS · EDITORIAL, NOT QUALITY RANKING</span></div>
   <div class="section-heading"><h2 id="priority-heading">Worth your <em>attention.</em></h2>
    <p>Three distinct research directions selected for relevance and the questions they open, not for established trading performance.</p></div>
   <div class="features">{feature_markup}</div>
  </section>

  <section class="section" id="insight" aria-labelledby="insight-heading">
    <div class="insight-block"><span class="insight-kicker">IV / CONNECTING THE DOTS</span>
     <span class="insight-quote" aria-hidden="true">“</span>
     <h2 id="insight-heading">{e(config["synthesis_heading"])}</h2>
     <p>{e(config["synthesis"])}</p>
     <span class="insight-label">EDITORIAL SYNTHESIS · NOT AN EMPIRICAL FINDING</span>
    </div>
  </section>

  <section class="section" id="library" aria-labelledby="library-heading">
   <div class="section-top"><span class="section-num">V / THE REMAINING SHORTLIST</span><span class="section-top-right">5 PAPERS · ALL SOURCE-REFERENCED</span></div>
   <div class="section-heading"><h2 id="library-heading">Further <em>reading.</em></h2>
     <p>Every other selected paper, with its author-reported contribution and direct source link.</p></div>
   <div class="library-tools" aria-label="Filter remaining papers">{theme_buttons}</div>
   <div class="paper-list" id="paper-list">{remainder_markup}</div>
   <p id="empty-filter" class="empty-state" hidden>No papers in this category among the remaining shortlist.</p>
  </section>

  <section class="section" id="proposal" aria-labelledby="proposal-heading">
   <div class="proposal-card"><div><span class="proposal-kicker">VI / A QUESTION WORTH TESTING</span>
    <h2 id="proposal-heading">{e(proposal["headline"])}</h2>
    <p>{e(proposal["hypothesis"])}</p>
    <p class="proposal-detail"><strong>How it could be falsified:</strong> {e(proposal["criterion"])}</p>
    <p class="proposal-detail"><strong>Evidence boundary:</strong> {e(proposal["basis"])}</p></div>
    <div class="proposal-stamp">PROPOSED<br><span>NOT EXECUTED</span></div></div>
  </section>

  <section class="section sources" id="sources" aria-labelledby="sources-heading">
   <div class="section-top"><span class="section-num">VII / PROVENANCE</span><span class="section-top-right">TRACE THE EVIDENCE</span></div>
   <div class="section-heading"><h2 id="sources-heading">Behind <em>the briefing.</em></h2></div>
   <div class="source-grid"><div><span class="source-label">EDITION / CLASSIFICATION</span><p>{e(date_display)}<br>Retrospective main-branch report; not new inference.</p></div>
   <div><span class="source-label">RESEARCH EVIDENCE</span><p>Eight abstract-only entries. Author-reported results have not been independently verified or reproduced.</p></div>
   <div><span class="source-label">COVERAGE &amp; COUNTS</span><p>Bounded arXiv selection, not exhaustive. Raw retrieved count absent; 31 new unique, 24 assessed and 8 shortlisted recorded.</p></div>
   <div><span class="source-label">IMMUTABLE SOURCE</span><p>{a(report_link, "Open pinned report", "text-link")}<br><code>{e(sha[:14])}…</code></p></div></div>
   <div class="access-warning"><span class="warning-symbol">!</span><p><strong>Local design preview; no access controls are active.</strong> This build is not deployed. A future private site requires fail-closed authentication for every production, preview and alias URL. The source GitHub repository is public.</p></div>
  </section>
  <footer><span class="footer-brand">Q<span>.</span> &nbsp; QUANT FOLIO</span>
   <span>Research intelligence, with its uncertainties intact.</span><a href="#overview">BACK TO TOP ↑</a></footer>
</main></div>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
<dialog id="prompt-dialog" class="prompt-dialog" aria-labelledby="prompt-dialog-heading">
 <h2 id="prompt-dialog-heading">Continue in ChatGPT</h2>
 <p>Copy this source-qualified research prompt into a ChatGPT conversation.</p>
 <textarea id="prompt-text" readonly rows="10" aria-label="Copyable research prompt"></textarea>
 <form method="dialog"><button type="submit">Close</button></form>
</dialog>
</body></html>'''

def main() -> int:
    try:
        page = build()
    except (SourceError, OSError, KeyError, ValueError, TypeError) as exc:
        print(f"JOURNAL BLOCKED: {exc}", file=sys.stderr)
        return 2
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    assets = OUTPUT.parent / "assets"
    assets.mkdir(exist_ok=True)
    for name in ("styles.css", "app.js", "deep.css"):
        (assets / name).write_bytes((JOURNAL / "assets" / name).read_bytes())
    OUTPUT.write_text(page + "\n", encoding="utf-8")
    deep_assessment.write_preview()
    print(f"Built {OUTPUT.relative_to(ROOT)}; Git commit/blob and eight-paper evidence contract PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
