# Quant Folio

Bounded arXiv discovery, abstract-based AI triage and evidence-labelled recommendations using direct OpenRouter requests. Optional full-PDF assessment is available via `--full-paper`.

## Activation status

**Not activated.** A weekly schedule is prepared for Mondays at **01:17 UTC** (Monday **12:17 AEDT** or **11:17 AEST** in Sydney). It is inert while repository variable `QUANT_FOLIO_ENABLED` is not `true`. Manual non-publishing runs remain available. A manual publishing dispatch requires `publish=true` on `main` and the same enable variable. Do not set the variable or run a production publication without separate owner approval.

## Research pipeline

1. `scout.py` retrieves a bounded recent arXiv Atom feed and ranks candidates.
2. `curate.py` sends up to 24 titles/abstracts to a free model and validates a shortlist of at most eight.
3. Optional `--full-paper`: `full_paper.py` downloads each shortlisted paper from public arXiv (12 MB and 100-page limits), extracts PDF text with `pypdf` and limits transmitted extracted text to 90,000 characters per paper.
4. In optional full-paper mode, the same free model examines objective, methods, results, design, limitations, reproducibility and practical relevance. Each section contains a claim, source-evidence locator and evidence status. A text-visible claim is **not** independent validation.
5. In optional full-paper mode, unextractable PDFs are clearly marked **abstract only** and excluded from the processed-ID state so a future run can retry them. A malformed or failed model response aborts without changing report or state.
6. Only after successful curation does the program write a Markdown report and seen-state. Each local file replacement is atomic individually, but the pair is not transactional; the gated publication workflow commits both files together after a successful run. Only successfully assessed candidate IDs are marked seen; unassessed papers remain eligible.

Truncated extracted text is always labelled partial-text review; diagrams, equations, tables and figures that do not extract reliably are not independently inspected. A successfully extracted PDF is not equivalent to reproducing results.

## Inference controls

Only these explicit free endpoints can be selected:

- `nvidia/nemotron-3.5-super-vl:free` (alternative; JSON mode available)
- `nvidia/nemotron-3-ultra-550b-a55b:free` (JSON not enforced; strict local validation)
- `google/gemma-4-26b-a4b-it:free` (JSON mode available)

OpenRouter currently advertises zero per-token pricing for these endpoints; free quotas and upstream availability are not guaranteed. One run makes up to eight abstract-screening calls (five abstracts per batch, up to 40 candidates under explicit CLI bounds; the default 24 candidates requires up to five calls) and up to eight optional full-paper calls. With at most one retry on transient transport errors per call, the maximum is 32 attempted HTTP requests under explicit bounds (26 with the default 24 candidates). Each full-paper output is capped at 2,200 tokens; screening output at 2,600 tokens. Usage tokens are reported where available. Requests to non-allowlisted or paid models are rejected locally.

**Data handling:** paper text is sent to OpenRouter and its upstream provider. The free NVIDIA endpoint states that submitted sessions may be logged and used for product improvement. Only public arXiv research should be submitted. Do not transmit private files or account data.

## Local setup and tests

```sh
python -m pip install 'pypdf>=5,<7'
python -m unittest discover -s tests -v
```

For a live, non-publishing local pilot configure the secret in the execution environment, not in chat or Git:

```sh
OPENROUTER_API_KEY=... python curate.py --reports /tmp/folio-reports --state /tmp/folio-state.json
```

Optional: set `OPENROUTER_MODEL` to an allowlisted free model. For GitHub Actions, configure repository secret `OPENROUTER_API_KEY` and optional variable `QUANT_FOLIO_MODEL`. Use a manual non-publishing workflow dispatch and inspect the uploaded report artefact.

## Weekly activation procedure (owner approval required)

Operational acceptance is recorded in merged PR #3 and Actions run 40183211150; do not repeat its three-run exercise.

Before activation, independently confirm repository **Settings → Actions → General → Workflow permissions** permits the publish job's `contents: write` token, and confirm the effective rules governing `main` permit `github-actions[bot]` to push (without disabling any protection). The GitHub integration could read that the branch is reported unprotected and repository rulesets are empty, but its direct branch-protection check returned HTTP 403; an actual write has not been tested. Where bot pushes are prohibited, use a separate PR-based publication mechanism only with further owner authorisation; do not bypass review.

After independent merge authorisation for this activation PR, the owner must separately authorise enabling publication. For activation, set repository Actions variable `QUANT_FOLIO_ENABLED=true`, ensure the existing `OPENROUTER_API_KEY` secret is available, and confirm the effective permissions and next scheduled run. The weekly schedule triggers only from the default branch. Do not run the `publish=true` manual dispatch until separately authorised.

Successful runs produce `reports/YYYY-MM-DD.md` and update `data/seen.json` together in one Git commit pushed to `main`. A single concurrency group serialises manual and scheduled publication. If the run fails validation or publication, the workflow fails rather than recording successful publication; failed pushes leave no published digest/state. No paid fallback is configured.

To pause future publication, set `QUANT_FOLIO_ENABLED=false`. The cron still triggers a skipped publication job; it performs no research or publication.

## Cost estimate

Model requests to the allowlisted free endpoints are advertised at **USD 0 per token**. For a full eight-paper weekly run, the theoretical endpoint charge is **USD 0**, subject to free capacity and account limits; this is not a guaranteed service-level commitment. Extraction runs on existing GitHub Actions infrastructure. No paid fallback is configured.

No changes to `8ft0-ai/arxiv-quant-radar` or additional hosting are required.

## Autonomous v1 default

The manual pilot and eventual weekly digest use abstract-only curation by default. Full-paper assessment is opt-in (`python curate.py --full-paper`), not required for a useful digest. Provider responses must finish normally and contain strict JSON matching the recommendation schema. Failure diagnostics print finish reason, response length and reported token usage, never the model output or credentials.

## Historical backfill V1 (Issue #7)

The fixed-window, manually invoked backfill is independent of normal publication:

```sh
OPENROUTER_API_KEY=... python historical.py --output /tmp/quant-folio-history/2026-10-18.md
```

It searches arXiv `submittedDate:[202610120000 TO 202610182359]` (UTC) across the existing q-fin.TR/PM/ST/CP/MF categories, paginates in ascending submission order (100 per page, capped at 2,000 results), refuses incomplete retrieval and deduplicates the response by arXiv ID. It assesses up to 24 relevance-ranked abstracts via the normal five-paper/three-recommendation free Nemotron batching and recommends at most eight. It does **not** read or write `data/seen.json` or invoke the weekly publication workflow; the output is an explicit caller-supplied path. A later arXiv query is not a contemporaneous snapshot: indexed versions, withdrawals and category assignments may change. The included report is a bounded retrospective research briefing, not an independently verified performance study. Never point `--output` at an existing publication.

## Historical backfill V2 — manual repeatable procedure (Issue #9)

Run a completed UTC Sunday-ending week from a clean checkout or a new report output directory:

```sh
python -m unittest discover -s tests -v
python historical.py --week-ending 2026-10-11
```

Set `OPENROUTER_API_KEY` in your environment before running live inference; do not put
credentials in commands, repository files or the manifest. The fixed, approved model
is Nemotron 3 Ultra free. The report and provenance file are written as
`reports/YYYY-MM-DD.md` and `reports/YYYY-MM-DD.provenance.json`.
An existing output, including a symlink or manifest, is refused. To regenerate,
use a new directory with `--output /tmp/new-directory/YYYY-MM-DD.md`, retaining
the earlier pair for review. Both outputs are non-published drafts.

On GitHub select **Actions → Historical research backfill (manual) → Run workflow**,
enter a completed Sunday under `week-ending`, and select **Run workflow**.
The workflow runs tests and the same CLI, and uploads review artefacts for 30
days. It has read-only permissions, no schedule, no commit/push step, and never
reads or writes production `data/seen.json` or invokes the weekly publication
workflow. GitHub-hosted inference consumes Actions minutes and the configured
free-model quota; use Voyager if these resources are constrained.

The manifest records UTC retrieval time, the exact submittedDate query, pagination
caps, retrieved and filtered counts, normalised abstract SHA-256, canonically
serialised source metadata SHA-256, model limits, candidate identities and the
UTF-8 report SHA-256. Paper ordering is sorted by ID; eligibility lists are
sorted and assessment order preserves ranked candidate order. Repeated executions
are not byte-identical: live index revisions, withdrawals, model responses and
the retrieval timestamp may differ. It is *not* an immutable source snapshot and
does not establish what arXiv showed during the historical reporting week.
A failed inference must not produce a report or update production state.


## ChatGPT editorial research briefing (Issue #11)

The read-only, version-controlled [Research Briefing V1 skill](skills/research-briefing/SKILL.md) turns an **existing** report into a ChatGPT editorial briefing. This is not a research pipeline, scheduler or automatically registered ChatGPT slash command.

For a **fresh ChatGPT session**, paste the complete [standalone prompt](skills/research-briefing/PROMPT.md) and, if desired, change the date and project focus. Use natural language such as "Brief Quant Folio's latest non-draft edition, focusing on TradeLab". Connect GitHub or use public GitHub retrieval to inspect the actual report first. A repository skill file is documentation until explicitly installed/registered on a supporting client.

The optional no-dependency source validator pins the `main` commit and produces a validated, read-only input manifest:

```sh
python briefing_source.py
python briefing_source.py --date 2026-10-25 --focus TradeLab
python -m unittest discover -s tests -v
```

It requires read access to the public GitHub API, never retrieves papers from arXiv and does not write repo files or execute model inference. Reports marked historical/non-published draft are skipped when requesting "latest"; a date can explicitly select one with a visible draft warning. A report more than eight days old is marked stale. Unrecorded counts remain unknown; GitHub source or content-integrity failures block the briefing. Main-branch presence alone does not establish that a scheduled publication ran.

[Verified 25 October 2026 editorial example](skills/research-briefing/example-2026-10-25.md) — the sample report was retrospectively formatted, with eight abstract-only recommendations and no recorded retrieved count.
