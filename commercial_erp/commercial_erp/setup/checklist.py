"""Customer onboarding checklist: what to set up for THIS customer's package, and what is already done."""

import frappe
from frappe import _

SALES, PURCHASES, STOCK, ACCOUNTS = "sales", "purchases", "stock", "accounts"
PACKAGE_AREAS = {
	"Full Business": {SALES, PURCHASES, STOCK, ACCOUNTS},
	"Accounts and Stock": {STOCK, ACCOUNTS},
	"Accounts Only": {ACCOUNTS},
	"Stock Only": {STOCK},
}


def _count(doctype, filters=None):
	return frappe.db.count(doctype, filters or {})


def _steps():
	"""(key, area, label, hint, route, done_callable, optional)"""
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	return [
		(
			"package",
			None,
			_("Choose the customer package"),
			_("Open FES Settings, choose what the customer bought, save. Only those modules appear."),
			"/desk/fes-settings",
			lambda: bool(frappe.db.get_single_value("FES Settings", "applied_on")),
			False,
		),
		(
			"company",
			None,
			_("Company details"),
			_(
				"Name, tax ID (if registered), currency EGP, fiscal year. Created by the setup wizard; review it."
			),
			f"/desk/company/{company}" if company else "/desk/company",
			lambda: bool(company),
			False,
		),
		(
			"users",
			None,
			_("Create users and roles"),
			_("One user per person; role profile: Shop Owner, Cashier, Storekeeper or Accountant."),
			"/desk/user",
			lambda: _count("User", {"enabled": 1, "name": ["not in", ["Administrator", "Guest"]]}) > 0,
			False,
		),
		(
			"warehouse",
			STOCK,
			_("Warehouses"),
			_("Name the shop warehouse (and the depot if there is one)."),
			"/desk/warehouse",
			lambda: _count("Warehouse", {"is_group": 0}) > 0,
			False,
		),
		(
			"items",
			STOCK,
			_("Items"),
			_(
				"Item groups, units, then items: code, name, barcode, selling price, reorder level. Use Data Import for a spreadsheet."
			),
			"/desk/item",
			lambda: _count("Item") > 0,
			False,
		),
		(
			"opening_stock",
			STOCK,
			_("Opening stock"),
			_("Stock Reconciliation, purpose Opening Stock: quantity and cost per item, then Submit."),
			"/desk/stock-reconciliation/new",
			lambda: _count("Stock Reconciliation", {"docstatus": 1, "purpose": "Opening Stock"}) > 0,
			False,
		),
		(
			"customers",
			SALES,
			_("Customers"),
			_("Add or import customers (group, governorate, credit limit if needed)."),
			"/desk/customer",
			lambda: _count("Customer") > 0,
			False,
		),
		(
			"suppliers",
			PURCHASES,
			_("Suppliers"),
			_("Add or import suppliers."),
			"/desk/supplier",
			lambda: _count("Supplier") > 0,
			False,
		),
		(
			"payment_modes",
			ACCOUNTS,
			_("Payment methods"),
			_("Cash, Vodafone Cash, InstaPay, cheque, bank transfer: each linked to an account."),
			"/desk/mode-of-payment",
			lambda: _count("Mode of Payment Account") >= 2,
			False,
		),
		(
			"opening_balances",
			ACCOUNTS,
			_("Opening balances"),
			_(
				"Cash, bank, customers and suppliers at the start date: Journal Entry of type Opening Entry (ask the accountant)."
			),
			"/desk/journal-entry/new",
			lambda: _count("Journal Entry", {"docstatus": 1, "voucher_type": "Opening Entry"}) > 0,
			False,
		),
		(
			"vat",
			ACCOUNTS,
			_("VAT (optional)"),
			_(
				"If the customer is VAT-registered pick the 14% template on invoices; otherwise leave the template empty."
			),
			"/desk/sales-taxes-and-charges-template",
			lambda: _count("Sales Taxes and Charges Template", {"disabled": 0}) > 0,
			True,
		),
		(
			"test_sale",
			SALES,
			_("Test: sell and collect"),
			_(
				"Sales invoice (Update Stock on) -> Submit -> Payment Entry. Check stock went down and cash went up."
			),
			"/desk/sales-invoice/new",
			lambda: _count("Sales Invoice", {"docstatus": 1}) > 0,
			False,
		),
		(
			"test_purchase",
			PURCHASES,
			_("Test: buy and pay"),
			_("Purchase invoice (Update Stock on) -> Submit -> Payment Entry. Check stock went up."),
			"/desk/purchase-invoice/new",
			lambda: _count("Purchase Invoice", {"docstatus": 1}) > 0,
			False,
		),
		(
			"test_journal",
			ACCOUNTS,
			_("Test: a manual entry"),
			_("Record an expense (rent, electricity) as a Journal Entry and see it in Profit and Loss."),
			"/desk/journal-entry/new",
			lambda: _count("Journal Entry", {"docstatus": 1}) > 0,
			False,
		),
		(
			"go_live",
			None,
			_("Before handing over"),
			_(
				"Delete demo data, set a domain with HTTPS, confirm the daily backup is copied off the server, train each user."
			),
			"/desk/guide",
			lambda: False,
			False,
		),
	]


@frappe.whitelist()
def status():
	frappe.only_for(["System Manager", "Accounts Manager", "Shop Owner"])
	package = frappe.db.get_single_value("FES Settings", "package") or "Full Business"
	areas = PACKAGE_AREAS.get(package, PACKAGE_AREAS["Full Business"])
	out = []
	for key, area, label, hint, route, done, optional in _steps():
		if area and area not in areas:
			continue
		try:
			is_done = bool(done())
		except Exception:
			is_done = False
		out.append(
			{
				"key": key,
				"label": label,
				"hint": hint,
				"route": route,
				"done": is_done,
				"optional": optional,
				"manual": key == "go_live",
			}
		)
	return {"package": _(package), "steps": out}
