# Quant Folio — Private Research Journal V1

**Issue:** [#13](https://github.com/8ft0-ai/quant-folio/issues/13)
**Status:** offline static reading experience ready for PR review; **private deployment BLOCKED** until separate authorisation and verified controls.

## The experience

A bespoke, responsive editorial reading room for the actual 25 October 2026 edition, with:

- Opening research letter, 60-second overview and visual research landscape.
- **Actual evidence counts:** 31 new unique, 24 AI-assessed, eight shortlisted, raw retrieved **not recorded**.
- Three deliberately chosen editorial priority papers (arXiv 2610.27100, 2610.25802, 2610.24544), each with specific limitations.
- Five remaining shortlist entries, thematic filtering and direct arXiv links. All eight exactly match the existing research report.
- Cross-paper synthesis identified as editorial, and one expressly *unexecuted* proposed experiment.
- Reading-progress indicator, accessible navigation, copyable per-paper ChatGPT prompts with a manual-copy fallback, and a visible provenance section.
- Hand-built CSS and SVG with no runtime libraries, external fonts, images, analytics, cookies, or storage.

The first edition is deliberately a **pinned editorial fixture**, not a live publishing engine. It is a retrospective formatting of abstract-only recommendations and not a new source assessment. The author-reported evidence is **not independently validated**.

### Visual acceptance

![Desktop reading room](previews/desktop.png)

![Mobile reading room](previews/mobile.png)

## Local preview only

From the repository root:

    python3 journal/build.py
    python3 -m unittest discover -s tests -v
    node --check journal/assets/app.js

To view locally, without listening on public interfaces:

    cd journal/site
    python3 -m http.server --bind 127.0.0.1 8765

Visit http://127.0.0.1:8765/ from the same machine. The HTML can also be opened locally from disk.

The reproducible build reads the exact on-disk report, checks its SHA-256 against the reviewed value in editorial.json, then invokes the existing briefing_source.inspect_report for date, category, source-link, ID and count reconciliation. The editorial record pins commit 4b68dd5c36138bb49942f5078e0814bbb56c5a55, which contains the report and merged briefing skill. If the source changes, the build **fails closed** pending a new editorial review; it will not silently substitute a different report or a historical draft.

The committed journal/site files are **static build output**, not a connected Cloudflare/GitHub Pages service. CI's existing Python test discovery includes tests/test_journal.py; tests check source identity, all eight paper IDs, missing counts, duplicate priorities, historical-draft refusal, category mismatch, link and dependency integrity, and byte-for-byte build repeatability. No new GitHub Actions workflows were added.

## Focused independent-review remediation (EVD-01, A11Y-01, UX-01)

- **EVD-01:** The build now proves the configured commit-to-report relationship using Git's actual commit/tree/blob objects. GitHub's Validate checkout fetches history so this check is mandatory in CI. If the commit or blob differs, the build fails closed.
- All eight papers display their original source finding and open question. For the three priority papers, a source record is expandable beside the separately labelled editorial paraphrase and paper-specific limitation.
- The evidence_review.json file records source-text anchors and reviewed editorial summary/limitation fingerprints for all three priorities, plus the commit and blob. The builder rejects unreviewed changes. Each editorial selection has a paper-specific review note. This is traceability against the source report, **not semantic fact verification, independent arXiv research or replication**.
- **A11Y-01:** Section links and filters operate with a keyboard, dialog close restores focus to its trigger, and navigation/reading progress expose accessible roles and labels. Browser reflow has been inspected at 1440, 640, 390 and 320 CSS pixels, approximating the layout demands of 200% and 400% zoom on a 1280-pixel reference viewport. These tests do not substitute for a complete assistive-technology audit.
- **UX-01:** A visible More arrow exposes additional mobile section links and is keyboard operable.
- Optional browser acceptance test: install Puppeteer in a disposable directory and set NODE_PATH to its node_modules, then run node journal/testing/accessibility_smoke.cjs on a machine with Chrome. No Puppeteer dependency is needed to build the site or run CI.

## Private hosting — decision record (not deployed)

**Preferred candidate:** Cloudflare Pages plus Cloudflare Access *only if complete coverage is demonstrable*. Alternative: a Cloudflare Worker with static assets plus Access, if it offers a simpler single protected application boundary. A localhost-only reading room is acceptable until deployment can meet the privacy gate. Ordinary GitHub Pages is not private hosting.

**Important Cloudflare Pages nuance:** Pages preview URLs are public by default. Its built-in preview Access setting protects preview deployment URLs **but does not automatically protect the main pages.dev hostname or custom domains**. The documented multi-host setup requires separate, carefully verified Access configuration. Do not create a Pages project connected to the public source repository until the access strategy is approved and safe exposure of a first deployment is controlled.

Provider documentation:
- [Cloudflare Pages preview deployments](https://developers.cloudflare.com/pages/configuration/preview-deployments/)
- [Pages: protecting the pages.dev hostname](https://developers.cloudflare.com/pages/platform/known-issues/)
- [Workers: Access coverage for preview and production](https://developers.cloudflare.com/workers/configuration/cloudflare-access/)

### Mandatory GO / NO-GO gate before any remote deployment

1. **Separate owner authorisation:** approve provider, account, intended domains, cost exposure and authentication method. Do not infer approval from this PR or from a passing offline build.
2. **Access coverage inventory:** enumerate production, pages.dev, configured custom domains, PR/branch aliases and every immutable hash-preview hostname. Protect **all** independently addressable paths; no public backup route.
3. **Negative tests:** as an unauthenticated user test /, /index.html, /assets/styles.css, /assets/app.js, all hostnames and several historical preview URLs. Expect authentication or deny responses **without HTML/asset content**. Test from a separate unauthenticated session and network. A 200 returning site content is an unequivocal NO-GO.
4. **Positive tests:** the expressly allowed owner's identity reaches the same URLs; a non-allowlisted identity cannot. Check token/session expiry and logout.
5. **Content review:** confirm static output has only already-public paper references and approved editorial copy. No credentials, private notes, identifiers, session values or provider secrets in builds or logs.
6. **Cloud build integration:** confirm PR preview automation is disabled until coverage is verified; prevent accidental new alias/preview exposure. Existing research Actions workflow and data/seen.json must remain unchanged.
7. **Evidence:** record exact URLs, dated tests, Access policy state and owner sign-off. If not proven, mark **BLOCKED** and preserve the local preview; do not switch to a public fallback.

**Privacy boundary:** the Quant Folio GitHub repository and its research report are already public. The proposed private reader will protect *access to the reader*, not retroactively make source papers or existing GitHub materials confidential. Future private notes must use a separate access-controlled store; they are deliberately not present in V1.

## Later extensions (not in V1)

- Accepted-edition archive and reading state.
- Saturday notification using the latest accepted edition (without changing the Monday research publication job).
- Curated, sanitised public editions via a separate opt-in sharing process. Never publish an entire private journal by toggling its visibility.
- Automated editorial generation only after source and approval gates are defined.

## Explicit non-actions

No GitHub Pages or Cloudflare deployment, DNS changes, Access policies, infrastructure, IAM, secrets, inference, data state, production workflow, public release, email, scheduled job or trading activity is performed or authorised by this candidate. The local preview is **not private authentication**; do not describe it as a deployed secure service.
