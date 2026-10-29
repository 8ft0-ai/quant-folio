"""Bounded offline renderer for the one pinned full-paper assessment.

No network access, external Markdown dependency, browser inference or arbitrary HTML.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "journal" / "analysis" / "2610.25802v2-deep.md"
MANIFEST = SOURCE.with_suffix(".json")
OUTPUT = ROOT / "journal" / "site" / "assessments" / "2610.25802.html"
PAPER_ID = "2610.25802"
PAPER_URL = "https://arxiv.org/pdf/2610.25802v2"
PDF_SHA256 = "dfb27aac8f65328c04486b7831c4a2c89a488a8a92c2deebe122b5e9a3e037b5"
REQUIRED_HEADINGS = (
    "Executive research judgement", "1. What the model actually estimates",
    "2. Simulator fit, training and calibration",
    "3. Data, fair comparators and author-reported outcomes",
    "4. Evidence quality, failure modes and reproducibility",
    "5. Falsifiable, read-only validation protocol",
    "6. Open questions and final verdict",
)
LABELS = ("[SOURCE-CHECKED]", "[AUTHOR-REPORTED]", "[ANALYSIS]", "[PROPOSED / NOT RUN]")


def load() -> tuple[str, dict] | None:
    """A broken or absent deep assessment never breaks the existing journal."""
    try:
        raw = SOURCE.read_bytes()
        record = json.loads(MANIFEST.read_text(encoding="utf-8"))
        md = raw.decode("utf-8")
        if (
            record["schema"] != "quant-folio-deep-assessment-v2"
            or record["paper_id"] != PAPER_ID
            or record["paper_version"] != "v2"
            or record["pdf_url"] != PAPER_URL
            or record["pdf_sha256"] != PDF_SHA256
            or record["source_format"] != "application/pdf"
            or record["retrieved_on"] != "2026-10-29"
            or record["generation"]["method"] != "chatgpt-full-paper-assisted-editorial"
            or record["generation"]["external_provider_calls"] != 0
            or record["generation"]["prompt_tokens"] is not None
            or record["generation"]["completion_tokens"] is not None
            or record["generation"]["cost_usd"] is not None
            or record["markdown_sha256"] != hashlib.sha256(raw).hexdigest()
            or not md.startswith("# Neural filtering")
            or not 2000 <= len(md.split()) <= 3500
            or any("# " + h not in md for h in REQUIRED_HEADINGS)
            or any(label not in md for label in LABELS)
            or md.count("https://arxiv.org/pdf/2610.25802v2#page=") < 12
        ):
            return None
        return md, record
    except (OSError, ValueError, UnicodeError, KeyError, TypeError):
        return None


def inline(text: str) -> str:
    """Explicitly escape all text; permit only HTTPS paper/code links."""
    links: list[str] = []

    def replace(match: re.Match) -> str:
        label, url = match.groups()
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc not in ("arxiv.org", "github.com"):
            return html.escape(match.group(0), quote=True)
        if parsed.netloc == "github.com" and not parsed.path.startswith("/minkeymouse/nfe"):
            return html.escape(match.group(0), quote=True)
        links.append(
            f'<a href="{html.escape(url, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{html.escape(label)}</a>'
        )
        return f"QFLINKPLACEHOLDER{len(links) - 1}END"

    text = re.sub(r"\[([^\]\n]+)\]\((https://[^\s)]+)\)", replace, text)
    text = html.escape(text, quote=True)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    for i, link in enumerate(links):
        text = text.replace(f"QFLINKPLACEHOLDER{i}END", link)
    return text


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def to_html(md: str) -> str:
    """Render the intentionally restricted authored Markdown subset."""
    blocks: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            blocks.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    for line in md.splitlines():
        line = line.strip()
        if not line:
            flush()
            continue
        if line == "---":
            flush()
            blocks.append("<hr>")
            continue
        match = re.match(r"^(#{1,3}) (.+)$", line)
        if match:
            flush()
            level, title = len(match.group(1)), match.group(2)
            # Only the standalone document title uses H1; subsections are H2.
            if level == 1:
                blocks.append(f'<p class="deep-doc-title">{inline(title)}</p>')
            else:
                blocks.append(f'<h{level} id="{slug(title)}">{inline(title)}</h{level}>')
            continue
        paragraph.append(line)
    flush()
    return "\n".join(blocks)


def render(md: str, record: dict) -> str:
    sections = [(h, slug(h)) for h in REQUIRED_HEADINGS]
    nav = "\n".join(
        f'<a href="#{target}">{html.escape(title)}</a>'
        for title, target in sections
    )
    source_hash = html.escape(record["pdf_sha256"])
    body = to_html(md)
    return f"""<!doctype html>
<html lang="en-AU">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark"><meta name="referrer" content="no-referrer">
<meta name="description" content="Evidence-linked full paper assessment for arXiv 2610.25802v2. Offline journal preview.">
<title>Neural filtering — Deep assessment · Quant Folio</title>
<link rel="stylesheet" href="../assets/styles.css">
<link rel="stylesheet" href="../assets/deep.css"></head>
<body class="deep-page">
<a class="skip-link" href="#deep-main">Skip to assessment</a>
<header class="deep-top"><a href="../index.html#paper-2610.25802" class="deep-back">← Back to research snapshot</a>
<span class="deep-brand">Q. <span>QUANT FOLIO / RESEARCH ANALYSIS</span></span></header>
<main id="deep-main">
<section class="deep-cover" aria-labelledby="deep-hero">
<p class="deep-kicker">RESEARCH ANALYSIS V2 <span>/</span> FULL PAPER 01</p>
<p class="deep-cover-note">Evidence before conviction.</p>
<h1 id="deep-hero">The uncertainty<br><em>is the signal.</em></h1>
<p class="deep-dek">A critical full-paper reading of neural filtering in statistical arbitrage.
The methodological claim is worth testing; incremental alpha is not established.</p>
<div class="deep-meta"><span>29 OCT 2026</span><span>arXiv 2610.25802v2</span><span>OFFLINE PREVIEW</span></div>
<div class="deep-judgement"><span>RESEARCH VERDICT</span><strong>Investigate methods. Do not infer returns.</strong></div>
</section>
<div class="deep-layout">
<nav class="deep-toc" aria-label="Assessment sections"><p>IN THIS ASSESSMENT</p>{nav}
<a href="#deep-source">Source integrity ↓</a></nav>
<article class="deep-article" aria-label="Full paper assessment">{body}
<section class="deep-source" id="deep-source" aria-label="Source provenance">
<span>IMMUTABLE SOURCE EVIDENCE</span>
<p>arXiv:2610.25802v2 · PDF · retrieved 29 October 2026</p>
<code>SHA-256 {source_hash}</code>
<p>Source-referenced editorial assessment, not independent replication, financial advice or live inference.</p>
<a href="https://arxiv.org/pdf/2610.25802v2" target="_blank" rel="noopener noreferrer">Inspect source PDF ↗</a>
</section></article>
</div></main>
<footer class="deep-footer"><a href="../index.html#paper-2610.25802">← Return to journal</a><span>STATIC, READ-ONLY DESIGN PREVIEW</span></footer>
</body></html>"""


def write_preview() -> bool:
    loaded = load()
    if loaded is None:
        OUTPUT.unlink(missing_ok=True)
        return False
    md, record = loaded
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(md, record) + "\n", encoding="utf-8")
    return True
