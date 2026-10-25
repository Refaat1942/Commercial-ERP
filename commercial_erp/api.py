import frappe

SUPPORTED_LANGUAGES = ("ar", "en")


@frappe.whitelist()
def set_language(lang: str):
	"""Let a user switch their own UI language between Arabic and English."""
	if lang not in SUPPORTED_LANGUAGES:
		frappe.throw(frappe._("Unsupported language"))
	if frappe.session.user == "Guest":
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)
	frappe.db.set_value("User", frappe.session.user, "language", lang)
	frappe.clear_cache(user=frappe.session.user)
	return lang
