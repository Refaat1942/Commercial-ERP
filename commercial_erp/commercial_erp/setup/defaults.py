"""Egypt / Arabic defaults. Everything here is idempotent and uses native settings only."""

import frappe

# Upstream stores the ambiguous "£ or ج.م" here.
EGP_SYMBOL = "ج.م"

SYSTEM_SETTINGS = {
	"language": "ar",
	"country": "Egypt",
	"time_zone": "Africa/Cairo",
	"date_format": "dd-mm-yyyy",
	"time_format": "HH:mm:ss",
	# Verify the preferred separators with the client's accountant.
	"number_format": "#,###.##",
	"first_day_of_the_week": "Saturday",
}

# Doctypes whose changes should leave an audit trail (native "Track Changes").
TRACKED_DOCTYPES = [
	"Item",
	"Customer",
	"Supplier",
	"Sales Invoice",
	"Purchase Invoice",
	"Payment Entry",
	"Journal Entry",
	"Stock Entry",
	"Stock Reconciliation",
	"Purchase Receipt",
	"Delivery Note",
	"Warehouse",
	"Account",
]


def apply_system_defaults():
	frappe.db.set_single_value(
		"System Settings", {k: v for k, v in SYSTEM_SETTINGS.items() if k != "country"}
	)
	if frappe.db.exists("Country", "Egypt"):
		frappe.db.set_single_value("System Settings", "country", "Egypt")
	if frappe.db.exists("Language", "ar"):
		frappe.db.set_value("Language", "ar", "enabled", 1)
	if frappe.db.exists("Language", "en"):
		frappe.db.set_value("Language", "en", "enabled", 1)
	if frappe.db.exists("Currency", "EGP"):
		frappe.db.set_value("Currency", "EGP", {"enabled": 1, "symbol": EGP_SYMBOL})


def apply_stock_defaults():
	"""Conservative controls: no negative stock."""
	if frappe.db.exists("DocType", "Stock Settings"):
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 0)


def enable_audit_trail():
	for doctype in TRACKED_DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			frappe.make_property_setter(
				{
					"doctype": doctype,
					"doctype_or_field": "DocType",
					"property": "track_changes",
					"value": "1",
					"property_type": "Check",
				},
				validate_fields_for_doctype=False,
			)
