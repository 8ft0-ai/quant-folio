# Research Analysis V1 — bounded editorial pilot (#16)

Three static, ChatGPT-assisted editorial drafts for the selected papers in the
**pinned 25 October 2026 report**. These are **not** independently verified
paper reviews or an executed provider inference batch. Only the pinned report's
abstract-level summaries were used; the arXiv PDFs, paper versions and results
were not independently inspected. Do not claim empirical replication.

The JSON records contain explicit source scope, author claims, interpretation,
limitations, falsification criteria, source commit, report digest, prompt version,
generation method and honest token/cost unknowns. External provider calls: **0**.
No secrets, inference endpoint or dynamic client requests are involved.

Reviewers should reconcile method and claim fields with the pinned report,
assess limitations for unsupported specificity, and decide separately whether
a future batch-inference experiment is worth its cost. The rendering pipeline
displays only schema-validated assessments, otherwise silently retains the
original briefing and its Copy research prompt actions.

This pilot does **not** trigger weekly automation, change source reports, deploy
the Cloudflare Worker or replace the current private live journal.

## Pilot disposition and validation

The three analyses were drafted from the immutable report summaries in a
bounded ChatGPT session. No external model endpoint was called, so there is no
reliable inference token or monetary-cost measurement to claim. A later
automation decision should first measure provider usage on a separately
approved controlled run.

Reproduction:
- `python3 journal/build.py`
- `python3 -m unittest discover -s tests -v`
- `node --check journal/assets/app.js`

The rendered sections are native HTML `details/summary` disclosures: accessible
with keyboard, unenhanced by JavaScript, and styled for narrow viewports. The
existing three-paper priority layout and all eight copy buttons remain intact.
No browser screenshots were captured in this pilot environment; visual/browser
zoom acceptance remains a separate review qualification.

**Decision gate:** inspect source claims and desktop/mobile behaviour, accept or
reject the three drafts, and only then consider future provider inference and
publication automation. The private live journal remains unchanged.

## Research Analysis V2 — bounded full-paper pilot (Issue #18)

One deeper source-linked assessment is authored in `2610.25802v2-deep.md`, with
pinned arXiv PDF bytes/version, editorial generation disclosure and the Markdown
SHA-256 recorded in `2610.25802v2-deep.json`. This is **not** an automatically
inferred assessment, a verified replication or a replacement for V1 snapshots.

`python3 -m journal.build` checks the local Markdown against the manifest, then
writes `journal/site/assessments/2610.25802.html` and a single same-origin link
in the existing journal. Missing or invalid metadata fails closed: the existing
journal and eight copy-prompt interactions remain functional, but no full-page
link is shown and any stale deep page is removed. No network requests or third-
party Markdown parser are required at build time. The generated site and preview
screenshots are deliberately committed for an offline review; deploying remains
separately governed and is **not** authorised by this PR.

Validation: `python3 -m unittest discover -s tests -v`; optional local Chrome and
Playwright acceptance: `node journal/testing/deep_smoke.cjs` (with Playwright
available on `NODE_PATH`). Screenshots: `journal/previews/deep-desktop.png` and
`journal/previews/deep-mobile.png`. The browser's effective-width 640/320 px
reflow checks approximate 200/400% zoom and are **not** a screen-reader audit.
