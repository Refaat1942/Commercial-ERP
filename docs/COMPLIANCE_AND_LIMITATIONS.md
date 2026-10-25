# Compliance items needing verification, and known limitations

## Must be verified by an Egyptian accountant / official sources (NOT implemented or claimed)
- **VAT rates and rules**: the app creates VAT output/input accounts and *zero-rate* templates "حدد النسبة". No rate is hardcoded. ERPNext itself ships an unverified "Egypt Tax" placeholder (10%, account "GST"): this app **disables** it on new Egypt companies (only if still factory/unused).
- **Egyptian Tax Authority (ETA) e-invoicing / e-receipt**: no integration exists. Requirements (digital signing, JSON schema, UUID, API onboarding) must be checked against the official ETA technical specifications.
- **Chart of accounts**: ERPNext's native "Standard with Numbers" chart, created in Arabic. It is **not** an official Egyptian Uniform Chart of Accounts. Have an accountant review/adapt it (use ERPNext's Chart of Accounts Importer before posting any transaction).
- Invoice legal content/numbering, withholding tax, table tax, stamp duty, payroll/social insurance, fiscal-year rules, data-retention rules: not implemented.
- Arabic terms: some ERPNext Arabic translations are machine-quality (e.g. "Stock In Hand"); a few are overridden in `translations/ar.csv`; the rest need a native-speaker review.
- Number format `#,###.##` and Saturday week start are assumptions to confirm.

## Known limitations
- **Not yet deployed or tested on the real VPS**; `install.sh` is untested there (validated with `bash -n` and shellcheck only). HTTPS/domain, firewall and nginx-on-15161 behaviour are unverified.
- **MariaDB**: tests ran on MariaDB 10.11 (the only version reachable in the build sandbox); production pins 11.8 per Frappe v16 docs. Re-run `bench run-tests --app commercial_erp` on the VPS.
- Cashier role: custom DocPerms on `Sales Invoice` and `Payment Entry` (copies that doctype's standard perms into Custom DocPerm, so upstream permission changes for those two doctypes won't flow automatically). No POS screen customisation; the native POS is available but untested here.
- Navigation: native workspaces are kept; no simplified Arabic workspace yet (next step).
- Reorder alerts: set item reorder levels natively; use "Stock Projected Qty" report / auto Material Request. No custom notification.
- Reports (P&L, stock ledger, receivables/payables, sales analytics) are native; verified to exist, not content-audited here.
- Multi-warehouse works natively; only one default warehouse set up.
- Print format: one Arabic Sales Invoice format; rendering verified, not printed on paper/PDF (wkhtmltopdf fonts untested).
- Restore verified into a second site on the same host, not onto a different server.
