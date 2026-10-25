"""Egypt-specific additions applied after ERPNext creates a company's chart of accounts.

VAT is OPTIONAL per document: the 14% templates are never set as default, so an invoice carries no tax
unless the user picks the template. 14% is Egypt's general VAT rate; table tax, exemptions, reduced rates
and any rate change must be confirmed by the company's accountant / the Egyptian Tax Authority.
"""

import frappe
from frappe import _

VAT_OUTPUT = "ضريبة القيمة المضافة - مبيعات"
VAT_INPUT = "ضريبة القيمة المضافة - مشتريات"
VAT_RATE = 14
SALES_TEMPLATE = "ضريبة القيمة المضافة 14% - مبيعات"
PURCHASE_TEMPLATE = "ضريبة القيمة المضافة 14% - مشتريات"
LEGACY_ZERO_RATE_TEMPLATES = (
	("Sales Taxes and Charges Template", "ضريبة القيمة المضافة - مبيعات (حدد النسبة)"),
	("Purchase Taxes and Charges Template", "ضريبة القيمة المضافة - مشتريات (حدد النسبة)"),
)


def on_company_update(doc, method=None):
	if doc.country != "Egypt" or not doc.flags.in_insert:
		return
	setup_egypt_company(doc.name)


def setup_egypt_company(company):
	parent = frappe.db.get_value(
		"Account", {"company": company, "account_type": "Tax", "is_group": 1}, "name"
	)
	if not parent:
		# Chart not created yet (or a custom chart without a tax group): nothing to attach to.
		return
	output = _ensure_account(company, parent, VAT_OUTPUT)
	input_ = _ensure_account(company, parent, VAT_INPUT)
	_ensure_template("Sales Taxes and Charges Template", SALES_TEMPLATE, company, output, "Add")
	_ensure_template("Purchase Taxes and Charges Template", PURCHASE_TEMPLATE, company, input_, "Add")
	_retire_zero_rate_templates(company)
	disable_unverified_default_taxes(company)


def _retire_zero_rate_templates(company):
	"""Earlier versions created 0% placeholders; hide them (they are replaced by the 14% ones)."""
	for doctype, title in LEGACY_ZERO_RATE_TEMPLATES:
		name = frappe.db.get_value(doctype, {"title": title, "company": company})
		if name:
			frappe.db.set_value(doctype, name, {"disabled": 1, "is_default": 0})


def disable_unverified_default_taxes(company):
	"""ERPNext ships an "Egypt Tax" placeholder (10% booked to a "GST" account) that is not
	verified against Egyptian law. Disable it, unless it was already used or edited."""
	abbr = frappe.db.get_value("Company", company, "abbr")
	for doctype, child in (
		("Sales Taxes and Charges Template", "Sales Taxes and Charges"),
		("Purchase Taxes and Charges Template", "Purchase Taxes and Charges"),
	):
		name = f"Egypt Tax - {abbr}"
		if not frappe.db.exists(doctype, name):
			continue
		rows = frappe.get_all(
			child, filters={"parent": name, "parenttype": doctype}, fields=["rate", "account_head"]
		)
		factory = len(rows) == 1 and rows[0].rate == 10 and (rows[0].account_head or "").startswith("GST")
		if factory:
			frappe.db.set_value(doctype, name, {"disabled": 1, "is_default": 0})
	name = f"Egypt Tax - {abbr}"
	if frappe.db.exists("Item Tax Template", name):
		frappe.db.set_value("Item Tax Template", name, "disabled", 1)


def _ensure_account(company, parent, account_name):
	existing = frappe.db.get_value("Account", {"company": company, "account_name": account_name})
	if existing:
		return existing
	account = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": account_name,
			"company": company,
			"parent_account": parent,
			"account_type": "Tax",
			"is_group": 0,
		}
	)
	account.insert(ignore_permissions=True)
	return account.name


def _ensure_template(doctype, title, company, account_head, add_deduct):
	if frappe.db.exists(doctype, {"title": title, "company": company}):
		return  # never overwrite: the accountant may have changed it
	frappe.get_doc(
		{
			"doctype": doctype,
			"title": title,
			"company": company,
			"taxes": [
				{
					"category": "Total",
					"add_deduct_tax": add_deduct,
					"charge_type": "On Net Total",
					"account_head": account_head,
					"description": _("VAT 14%"),
					"rate": VAT_RATE,
				}
			],
		}
	).insert(ignore_permissions=True)
