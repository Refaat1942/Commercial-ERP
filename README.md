# commercial_erp

Arabic-first, Egypt-oriented configuration layer for small shops, warehouses and trading businesses,
built as a separate Frappe app on top of **ERPNext v16** (it does not modify ERPNext core).

License: GPL-3.0-or-later (see `license.txt`). ERPNext and Frappe are © Frappe Technologies Pvt. Ltd.
and are used unmodified under their own licenses.

## What it does
- On install: Arabic (RTL) + English enabled, country Egypt, timezone Africa/Cairo, EGP enabled,
  `dd-mm-yyyy` dates, Saturday week start, negative stock disabled, audit trail ("Track Changes")
  on key accounting/stock doctypes.
- Role Profiles built from native roles: `Shop Owner`, `Cashier`, `Storekeeper`, `Accountant`.
- When a company with country Egypt is created: VAT output/input accounts and **zero-rate** tax
  templates (rates must be configured by the owner/accountant — none are hardcoded).
- Arabic RTL print format for Sales Invoice (`فاتورة مبيعات - عربي`).
- Scripted setup wizard: `bench --site SITE execute commercial_erp.setup.wizard.run --kwargs '{"company_name": "...", "company_abbr": "..."}'`

See `../docs/` in the repository root for installation, deployment, backup and limitations.
