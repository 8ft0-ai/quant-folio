# FRESH SESSION — copy into a new chat

Produce my **Quant Folio Research Briefing V1** from an existing report. **Execute now, read-only.**

**Repository:** https://github.com/8ft0-ai/quant-folio
**Skill instructions:** https://github.com/8ft0-ai/quant-folio/blob/main/skills/research-briefing/SKILL.md
**Source directory:** https://github.com/8ft0-ai/quant-folio/tree/main/reports

**Edition:** latest non-draft report on `main`.
**Optional explicit date:** none. (To request an edition, replace "none" with `YYYY-MM-DD`.)
**Optional editorial focus:** none. (Replace "none" with a project, e.g. TradeLab, NetEdge or Quant Radar.)

First retrieve the skill instructions if available, then resolve GitHub `main` to its exact commit SHA, enumerate `reports/YYYY-MM-DD.md` at that commit, and retrieve the latest non-draft edition (or my exact requested edition) from the **same immutable commit**. Prefer the skill's read-only `briefing_source.py` if it is accessible and runnable; otherwise perform equivalent connector/web verification. Only use `main` files; never use PR branches, historical artefacts or an invented snapshot. An explicitly requested historical backfill draft must be labelled **HISTORICAL BACKFILL — NON-PUBLISHED DRAFT**. Do not mistake retrospective source reformatting for new inference or infer that a report on `main` proves automated weekly publication.

Verify the report header/date, all source paper IDs/titles/arXiv links, individual evidence labels, original shortlist count, actual retrieved/new-unique/AI-assessed counts and missing-value qualifications. **Not recorded** means unknown. Distinguish abstract-only author claims from independently validated results. If the source cannot be verified, say **SOURCE UNVERIFIED — briefing withheld** and explain why rather than inventing an issue. If the newest report is over eight days old, label it **STALE** and give its actual date.

Create a readable, polished briefing with:
1. A 60-second executive overview and three evidence-based research themes.
2. The actual counts and category split, without extrapolation.
3. **Three editorial priority papers** (not necessarily original shortlist order), each linked to arXiv, with why it matters and a specific caveat.
4. One cross-paper editorial insight, explicitly labelled as synthesis.
5. **Every remaining shortlisted paper**, once each, linked with a short relevance note.
6. **At most one** clearly labelled **PROPOSAL — not executed** research experiment, only if evidence suggests a genuinely useful bounded test, with a falsifiable outcome.
7. Specific clickable follow-up suggestions where native ChatGPT features support them; otherwise simple copyable follow-up questions.

Conclude with the immutable GitHub report permalink, source edition type/date, freshness, known missing counts, abstract-only and arXiv-coverage limitations and whether external arXiv links were actually checked.

Do **not** run inference, revisit or re-rank source assessments, dispatch workflows, publish research, modify `data/seen.json`, change GitHub, operate infrastructure, place trades or create an automation. Editorial selection and synthesis are permitted, but must be identified as your own.

If the SKILL.md path is not on `main` yet, use these self-contained instructions directly; do not pretend a custom slash command is installed.
