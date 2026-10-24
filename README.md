# Quant Folio

Autonomous discovery and curation of quantitative-finance research.

## Purpose

Find a small number of worthwhile papers and explain why they deserve attention. Prefer useful recommendations to exhaustive per-paper reporting.

## Intended operating model

- Run weekly without routine human intervention.
- Collect new arXiv papers and deduplicate against previously seen IDs.
- Triage for relevance to systematic trading, forecasting, execution, portfolio construction and applied AI.
- Produce a concise Markdown reading list with source links, reasons to read, and explicit evidence-depth limitations. An empty list is valid.
- Publish automatically after deterministic checks; report genuine failures for investigation.

## Development principles

Keep the implementation small: one Python entry point, one scheduled GitHub Actions workflow, minimal state and focused tests. Use pull requests for software changes, but no routine PRs or approvals for scheduled reading-list runs. Never present abstract-only claims as independently validated research.

## Status

Repository initialised. No research pipeline, credentials, scheduled workflow or live runs have been implemented or activated. The existing arxiv-quant-radar repository is unchanged and is not a dependency.

## Licence

MIT. See [LICENSE](LICENSE).
