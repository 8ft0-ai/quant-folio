---
name: quant-folio-research-briefing
description: Turn an existing, source-verified Quant Folio report on GitHub main into a concise, evidence-labelled, interactive ChatGPT research briefing; latest, explicit-date and optional project focus.
---

# Quant Folio — Research Briefing V1

## Purpose and scope
This is a **read-only editorial skill**, not an arXiv search, model assessment or publication workflow. Transform an existing report into a briefing, without inventing facts, scoring papers afresh or claiming independent replication. Run from any ChatGPT session by pasting [PROMPT.md](PROMPT.md) if skill registration is unavailable. A repository file does **not** automatically install a ChatGPT slash command or a runtime skill.

## Inputs
- **Latest (default):** newest non-draft report on `8ft0-ai/quant-folio` **main**, by `reports/YYYY-MM-DD.md` date; skip explicitly labelled historical/non-published drafts. Do not guess based on a GitHub Actions artefact, PR branch or memory.
- **Date:** `YYYY-MM-DD` to read that exact main-branch report. An explicitly requested historical draft is allowed, prominently labelled as such. Do not silently substitute another date.
- **Focus (optional):** project/topic to inform editorial choice; do not change source identity, paper set, numbers or evidence claims.
- **As-of:** user's actual local date; >8 days since report date is **STALE**, not a new weekly briefing.

## Source acquisition and verification
1. Prefer the checked-in, stdlib-only `briefing_source.py` when a Python checkout and outbound public GitHub access are available:
   `python briefing_source.py [--date YYYY-MM-DD] [--focus "topic"]`.
   The command pins `main` to a commit, lists dated reports, retrieves content from that SHA, checks the heading/date, numeric counts, paper identities, links and metadata, and returns a source manifest. It does **not** independently check arXiv URLs or validate author claims.
2. In ChatGPT without a checkout/CLI, perform the **equivalent read-only GitHub steps** with a GitHub connector or public GitHub fetch: resolve `main` to one 40-character commit SHA; list `reports/` at **that same SHA**; choose the newest non-draft for latest (or exact requested date); fetch the file at that SHA. Do not substitute raw `main` URLs that may change between reads. Read and cross-check all detailed entries, dates, title/link/id agreement, source summary and counts. Preserve that commit permalink. Never claim checks that you did not execute.
3. Distinguish **main-committed** from **automatically published**. Main-branch presence alone does not prove a successful weekly Actions run, owner acceptance or independent scientific validation. `HISTORICAL BACKFILL — NON-PUBLISHED DRAFT` is never a weekly edition. A report saying `Retrospective formatting` is an editorial reformatting of past recommendations, not new inference.
4. A source `Retrieved: Not recorded in original report` is **unknown**, not 31, 40, 50 or 0. Likewise, absent counters remain **not recorded**; if a count contradicts validated detail records, stop with a source-integrity warning. Do not extrapolate from previous weeks.
5. Preserve exact arXiv IDs, titles and links from the report and do not attribute new results to a paper. Abstract-only methods, outcomes and applications are **author-reported**, not independent proof. Limitations must be specific where available; otherwise state the lack of full-text review and replication. External URLs are pointers, not proof of current accessibility unless opened.
6. If GitHub is unavailable, the chosen report is missing, the metadata are contradictory or the complete source cannot be read, output **SOURCE UNVERIFIED — briefing withheld** with the precise failure and source link. Do not silently regenerate or use a plausible sample. If latest is older than eight days, give the dated briefing with a prominent stale warning. If only drafts exist, report that no verified non-draft edition is available.

## Output contract
Use the platform's native rich display elements **when genuinely supported**, otherwise clear Markdown with working direct links. Do not assume icons, interactive cards or custom actions work.

1. **60-second executive overview:** report date, edition classification, three **editorial research themes** supported by the report, significance in practical language, and one-sentence conclusion. Themes must be represented in the actual source; distinguish your synthesis from source facts.
2. **Research metrics:** exactly recorded retrieved, new unique, AI assessed and shortlisted counts, with `not recorded` as necessary. Show category split separately if supported by verified detail records.
3. **Three editorial priority papers:** select three distinct papers from the original shortlist based on relevance and optional focus. Give title, original arXiv link, concise reason to read, paper-specific limitation/open question and an explicit **editorial priority, not the source ranking** label. Do not automatically reproduce the source's first three.
4. **One cross-paper insight:** identify the common principle and indicate it is an editorial inference, not an established empirical result.
5. **Remainder of the shortlist:** include each unfeatured paper **exactly once** with title, link and one useful sentence. Do not hide the less relevant papers.
6. **At most one proposed experiment (optional):** label **PROPOSAL — not executed**, identify hypothesis, existing potential input, measurable falsification criterion and constraints. Never imply data access, legal rights, successful validation, projected returns or permission to trade.
7. **Interactive follow-ups:** 2–4 specific reader choices. If supported, use genuine ChatGPT follow-up interactions; otherwise provide copyable natural-language prompts. No buttons that imply actual tool execution without acting.

Conclude with **Source and evidence**: immutable commit permalink, report date/type, freshness as of the user's date, limits of arXiv coverage, any missing counts, any unverified external links and abstract/full-text status.

## Safety and completion
Never initiate arXiv retrieval, inference, paper reassessment, workflow dispatch, publication, scheduled tasks, repository mutation, `data/seen.json` reads/writes or trading. Do not modify any other project. A briefing is complete only when every displayed paper ID and count reconciles against the retrieved report.

## Reference
- [Standalone fresh-session prompt](PROMPT.md)
- [Verified 25 October demonstration](example-2026-10-25.md)
- Source-check and error-path tests: `python -m unittest tests.test_briefing_source -v` (or `python -m unittest discover -s tests -v`).
