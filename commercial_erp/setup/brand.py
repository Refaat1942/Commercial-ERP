"""White-label: product name, logos and footer text shown in the desk, login page and website."""

import frappe

BRAND = "FES ERP"
LOGO = "/assets/commercial_erp/images/logo.svg"


def apply():
	values = {
		"app_name": BRAND,
		"app_logo": LOGO,
		"favicon": LOGO,
		"splash_image": LOGO,
		"footer_logo": LOGO,
		"hide_footer_signup": 1,
		"footer_powered": "",
		"copyright": BRAND,
		"title_prefix": BRAND,
	}
	meta = frappe.get_meta("Website Settings")
	frappe.db.set_single_value("Website Settings", {k: v for k, v in values.items() if meta.has_field(k)})
	if frappe.db.exists("DocType", "Navbar Settings") and frappe.get_meta("Navbar Settings").has_field(
		"app_logo"
	):
		frappe.db.set_single_value("Navbar Settings", "app_logo", LOGO)
	frappe.clear_cache()
