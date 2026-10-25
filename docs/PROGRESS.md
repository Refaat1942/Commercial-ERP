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

## UI / demo round (verified on the test bench)
- Theme (teal/gold, Cairo font bundled, module colours), FES ERP branding, new login page (AR/EN toggle, mobile), shop dashboard (number cards + chart + shortcuts), simplified module rail and sidebars, Egypt masters (27 governorates, UOMs, price lists, wallet accounts), in-app language switch, EGP formatting (`ج.م` after the number).
- Tests: 30/30 pass (`bench run-tests --app commercial_erp`). Demo seed -> 336 sales invoices, 10 purchase invoices, GL balanced; `demo.clear` leaves zero residue (checked).
- Not yet run on the VPS: `deploy/update.sh`, `deploy/create_demo_site.sh`.

## Round 3 (verified on the test bench)
- Optional VAT 14% templates (sales/purchase, never default), legacy 0% placeholders retired; demo data shows VAT (output 6,129 / input 7,735, GL balanced).
- Sidebars rebuilt as clear open sections per module (Selling, Buying, Stock, Accounts, Setup); dock versioned reset (`ARRANGE_VERSION`); shop dashboard is the landing page.
- ~380 Arabic term overrides + in-app searchable "دليل المصطلحات"; dock tooltips translated.
- EGP-only: other currencies disabled, price lists in EGP.
- Fratelanza 2026 branding (login footer, website copyright, e-mail footer, NOTICE).
- In-app time-limited Demo Links (demo site only), 30/30 tests.

## Next
1. Run `deploy/vps_discovery.sh` on the VPS, then `deploy/install.sh` (docs/DEPLOYMENT.md).
2. Re-run tests on the VPS; accountant review of chart/tax; Arabic translation review.
3. Simplified Arabic workspace per role; POS evaluation; domain + HTTPS.
