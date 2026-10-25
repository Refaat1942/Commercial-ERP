# Progress / resume notes

Reference repo (ERPNext v17-dev source) is untouched. New, additive directory `commercial_erp/` = the Frappe app plus its `deploy/` and `docs/` (becomes the root of the private repo via `git subtree split`).

## Decisions
- Stable base: ERPNext v16.52.1 + Frappe v16.53.0 (official tags), Python 3.14, Node 24, MariaDB 11.8, Bench 5.31.1.
- Native ERPNext features only; custom app = defaults, role profiles, one least-privilege role, Egypt VAT accounts + zero-rate templates, Arabic print format, audit-trail property setters.
- Shop chart of accounts = ERPNext "Standard with Numbers", created in Arabic (wizard runs with lang `ar`).

## Verified (test bench in the build sandbox: Python 3.14.6, Node 24.22.1, MariaDB 10.11 (not 11.8), Redis)
- `bench init` (Frappe v16.53.0), `get-app` ERPNext v16.52.1 + commercial_erp, `new-site`, scripted wizard: OK.
- `bench run-tests --app commercial_erp`: **15/15 passed** (defaults, roles, permissions, audit trail, Egypt VAT accounts/templates, idempotence, purchase->stock->sale->payment with balanced GL/SLE and zero outstanding, sales return, negative-stock block, Arabic invoice print render).
- Browser (Playwright/Chromium): login + desk + new Sales Invoice render `dir=rtl`, `lang=ar`, Arabic labels.
- Backup -> restore into a second site: identical data. MariaDB restart: data persisted.
- Secrets scan of new files: no credentials.
## Not verified
- Anything on the real VPS (install.sh, nginx 15161, ufw, supervisor, HTTPS), MariaDB 11.8, real-paper PDF, ETA/tax compliance. See `docs/COMPLIANCE_AND_LIMITATIONS.md`.

## Next
1. Run `deploy/vps_discovery.sh` on the VPS, then `deploy/install.sh` (docs/DEPLOYMENT.md).
2. Re-run tests on the VPS; accountant review of chart/tax; Arabic translation review.
3. Simplified Arabic workspace per role; POS evaluation; domain + HTTPS.
