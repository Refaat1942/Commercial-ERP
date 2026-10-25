"""White-label: product name, logos and footer text shown in the desk, login page and website."""

import frappe

BRAND = "FES ERP"
OWNER = "Fratelanza"
YEAR = "2026"
CREDIT = f"{OWNER} © {YEAR}"
LOGO = "/assets/commercial_erp/images/logo.svg"


def apply():
	values = {
		"app_name": BRAND,
		"app_logo": LOGO,
		"favicon": LOGO,
		"splash_image": LOGO,
		"footer_logo": LOGO,
		"hide_footer_signup": 1,
		"footer_powered": BRAND,
		"copyright": CREDIT,
		"title_prefix": BRAND,
	}
	meta = frappe.get_meta("Website Settings")
	frappe.db.set_single_value("Website Settings", {k: v for k, v in values.items() if meta.has_field(k)})
	if frappe.db.exists("DocType", "Navbar Settings") and frappe.get_meta("Navbar Settings").has_field(
		"app_logo"
	):
		frappe.db.set_single_value("Navbar Settings", "app_logo", LOGO)
	# e-mail footer: no upstream "Sent via ..." line; our own brand line instead
	meta = frappe.get_meta("System Settings")
	if meta.has_field("disable_standard_email_footer"):
		frappe.db.set_single_value("System Settings", "disable_standard_email_footer", 1)
	if meta.has_field("email_footer_address"):
		frappe.db.set_single_value("System Settings", "email_footer_address", f"{BRAND} — {CREDIT}")
	# the e-mail code reads these two from Defaults, not from System Settings
	frappe.db.set_default("disable_standard_email_footer", 1)
	frappe.db.set_default("email_footer_address", f"{BRAND} — {CREDIT}")
	frappe.clear_cache()
