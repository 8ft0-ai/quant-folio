# Quant Folio

Bounded arXiv discovery, abstract-based AI triage and evidence-labelled recommendations using direct OpenRouter requests. Optional full-PDF assessment is available via `--full-paper`.

## Activation status

**Not activated.** The workflow is manual-only. There is no weekly cron. Publication requires both manual `publish` selection and `QUANT_FOLIO_ENABLED=true`; neither should be enabled until separate owner approval.

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

## Acceptance still required

1. Confirm a functioning OpenRouter credential in the execution environment; do not put keys in a pull request or conversation.
2. Read three representative quantitative-finance PDFs and compare the three free models against a human-reviewed evidence checklist, including leakage, costs and baselines. No benchmark-quality claims are made by model listings.
3. Run manual non-publishing live-service verification and exact-head CI; inspect full-paper recommendations for unsupported claims and extraction omissions.
4. Check Actions write permissions and actual branch protection without weakening protections. Publication might require a protected-branch-compatible alternative.
5. Obtain separate owner authorisation before merging PR #2, enabling the weekly schedule or activating publication.

## Cost estimate

Model requests to the allowlisted free endpoints are advertised at **USD 0 per token**. For a full eight-paper weekly run, the theoretical endpoint charge is **USD 0**, subject to free capacity and account limits; this is not a guaranteed service-level commitment. Extraction runs on existing GitHub Actions infrastructure. No paid fallback is configured.

No changes to `8ft0-ai/arxiv-quant-radar` or additional hosting are required.

## Autonomous v1 default

The manual pilot and eventual weekly digest use abstract-only curation by default. Full-paper assessment is opt-in (`python curate.py --full-paper`), not required for a useful digest. Provider responses must finish normally and contain strict JSON matching the recommendation schema. Failure diagnostics print finish reason, response length and reported token usage, never the model output or credentials.
