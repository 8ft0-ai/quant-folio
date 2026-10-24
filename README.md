# Quant Folio

Autonomous weekly quantitative-finance paper curation, using the existing arXiv scout and one configurable AI model.

## Activation status

**Not activated.** The research workflow is manual-only and non-publishing by default. There is no active weekly cron. Publication requires both a manual `publish` selection and repository variable `QUANT_FOLIO_ENABLED=true`, which must not be set before owner acceptance.

## How it works

`scout.py` preserves the original deterministic pilot. `curate.py` retrieves a bounded set of arXiv papers, filters previously processed IDs, ranks candidates by keywords, and sends at most 24 abstracts (truncated to 1,600 characters each) to one configured AI model. The response must contain a validated JSON shortlist of zero to eight known papers. Recommendations include abstract-based summaries, reasons for reading and explicit evidence limitations. No full text or independent experimental validation is implied.

Following successful assessment, the run writes a Markdown report to `reports/YYYY-MM-DD.md` and updated `data/seen.json`. In GitHub Actions these are **committed together in a single Git commit** after successful processing. Failed assessment makes no state changes; failed pushes are reported as workflow failures. The concurrency group prevents overlapping publication. Not every retrieved paper is assessed: the run is deliberately not exhaustive.

## Tests and pilots

```sh
python -m unittest discover -s tests -v
python scout.py --fixture tests/fixture.atom --today 2026-10-24 --state /tmp/scout-seen.json --reports /tmp/scout-reports
```

The manually dispatched `Quant Folio research` workflow executes a live, non-publishing pilot in a temporary workspace and uploads the report as a short-lived GitHub Actions artifact.

For a local real run without publication:

```sh
OPENAI_API_KEY=... python curate.py --reports /tmp/folio-reports --state /tmp/folio-state.json
```

The credential must be provided securely via the execution environment; do not paste it into chat or commit it. The model defaults to `gpt-4o-mini`, configurable through `OPENAI_MODEL` locally or Actions variable `QUANT_FOLIO_MODEL`. The AI request is bounded to one call (up to three attempts for transient errors), maximum 2,600 completion tokens. Zero eligible candidates means no model call.

## Owner activation checklist

1. Add `OPENAI_API_KEY` as a GitHub Actions repository secret and apply a small API-spending limit at the provider. Do not disclose the key.
2. Run and inspect the manual non-publishing pilot.
3. Verify repository Actions token write permission and actual `main` branch protection rules. No rulesets were visible at implementation time, but classic branch protection was not readable via this connection. Do not weaken protection to allow automation. If the protected branch rejects direct pushes, a separately accepted publication method is required.
4. After separate owner acceptance, enable a weekly UTC `schedule` trigger for the publishing job and set `QUANT_FOLIO_ENABLED=true`. A cron conversion for Sydney must consider daylight saving.

No changes are made to `arxiv-quant-radar`.

## Cost envelope

24 candidate abstracts at up to 1,600 characters plus titles and instructions typically consume approximately 8,000–13,000 input tokens; output is capped at 2,600 tokens. Multiply by the configured provider's current input/output token rates to estimate cost. Transient failures can mean as many as three requests; usage is printed when supplied by the provider.

[executed on device: voyager-rdc (39776536-9592-45e3-9fe6-64ec59327689)]