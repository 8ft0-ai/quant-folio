"""Offline, fail-closed deployment candidate validation. Does not contact Cloudflare."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "journal/hosting/wrangler.jsonc"
SITE = ROOT / "journal/site"


def check() -> list[str]:
    errors = []
    raw = CONFIG.read_text()
    config = json.loads(re.sub(r"(?m)^\s*//.*$", "", raw))
    if config.get("workers_dev") is not False:
        errors.append("workers_dev must be explicitly false")
    if config.get("preview_urls") is not False:
        errors.append("preview_urls must be explicitly false")
    if any(key in config for key in ("routes", "route", "triggers", "unsafe", "build", "vars", "secrets", "main")):
        errors.append("unapproved routes, executable worker, or side-effect settings")
    if config.get("assets") != {"directory": "../site"}:
        errors.append("asset directory must be the existing journal/site")
    for path in ("index.html", "assets/app.js", "assets/styles.css"):
        if not (SITE / path).is_file():
            errors.append(f"missing asset: {path}")
    return errors


if __name__ == "__main__":
    errors = check()
    if errors:
        raise SystemExit("BLOCKED: " + "; ".join(errors))
    print("PASS: offline candidate only; Access and hostnames remain UNVERIFIED; deployment BLOCKED")
