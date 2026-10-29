# Private journal hosting — non-deploying candidate (Issue #13)

**NOT DEPLOYED. NOT AUTHORISED FOR DEPLOYMENT.** This directory contains
an offline Workers Static Assets candidate. No deployment workflow or API
credentials are included. Production research, scheduled curation, report
publication and `data/seen.json` are outside this change.

## Design

- Serve the existing immutable offline edition from `journal/site/`.
- Use Workers Static Assets, with `workers_dev: false` and
  `preview_urls: false`; no routes or custom domains are configured.
- Do **not** enable any public Workers route, `workers.dev` hostname,
  preview/version URL, Pages project or custom domain during preparation.
- Access is an **external edge control**, not an authentication mechanism
  implemented by this static site. The Wrangler file alone **does not**
  establish privacy. Only attach a reachable hostname once a matching
  Cloudflare Access application and deny-by-default policy are independently
  verified. Prefer the Cloudflare Worker-wide Access protection option so
  aliases and future Worker URLs are covered.
- The allowlist must be a separately owner-approved identity (Cloudflare
  account-member IdP with MFA where suitable). No email, user ID, shared
  secret, token or Access policy ID is committed to Git. Never use a
  wildcard Include, Everyone, Bypass or Service Auth rule for browsers.
- The site remains static. No database, inference, research dispatch or
  additional billable Cloudflare services are required.

## Offline validation

`python3 journal/hosting/preflight.py`
`python3 -m unittest tests.test_journal_hosting -v`

The preflight verifies only the **candidate configuration**. It cannot prove
that a live Access policy or domain is safe.

## Separate owner-authorised live gate — do not execute yet

1. Confirm Zero Trust Free entitlement and authorised identity/IdP/MFA.
   Obtain a written owner-approved exact allowlist; verify no Everyone,
   Bypass or unintended policy precedence. Do not record identity in Git.
2. Confirm that all routes for this Worker are absent. Keep `workers_dev`,
   `preview_urls`, version URLs, and any Pages previews **disabled**.
   Explicitly inventory existing and newly introduced routes, aliases,
   custom domains, workers.dev and version/preview addresses.
3. Create and independently inspect the **Access application and policy**
   before binding any live public hostname. Confirm coverage for every
   HTML, JS, CSS, image, source and deep-link path, not just the landing page.
   Verify Cloudflare's Worker-wide Access setting where available.
4. With separate authorisation, provision a private-only deployment in
   stages; do not combine unprotected hostname activation with publication.
   Stop if Access protection cannot be established before exposure.
5. Run real negative tests from an unauthenticated browser and an explicitly
   unapproved identity against **every** production/preview/version/alias
   URL and direct asset path. Expect login/deny, never journal content.
   Verify approved identity can load all assets. Test expired session,
   policy revocation, redirects and cache behaviour.
6. Verify Access audit logs, fail-closed limits, no unprotected alternative
   endpoint and a rollback path that removes the route if any test fails.
   Capture evidence, then seek separate owner acceptance before sharing URL.

**Stop/rollback:** Any unauthorised 200 response, unprotected alias,
ambiguous billing or policy scope, or inability to prove protection is
BLOCKED: disable the route and preserve evidence. Never rely on noindex.

References:
- https://developers.cloudflare.com/workers/static-assets/
- https://developers.cloudflare.com/workers/configuration/cloudflare-access/
- https://developers.cloudflare.com/workers/previews/custom-domains/
- https://developers.cloudflare.com/workers/versions-and-deployments/version-urls/
- https://developers.cloudflare.com/workers/platform/limits/
