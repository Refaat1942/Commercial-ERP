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


def _remaining_session(valid_until):
	from frappe.utils import get_datetime, now_datetime

	seconds = max(int((get_datetime(valid_until) - now_datetime()).total_seconds()), 60)
	return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


@frappe.whitelist(allow_guest=True)
def demo_login(token: str = ""):
	"""One-click sign-in for a Demo Link. Everything is checked server-side; failures give a generic message."""
	from commercial_erp.commercial_erp.doctype.demo_link.demo_link import end_access, token_digest

	row = None
	if token and frappe.conf.get("allow_demo_links"):
		row = frappe.db.get_value(
			"Demo Link",
			{"token_hash": token_digest(token)},
			["name", "status", "valid_until", "demo_user"],
			as_dict=True,
		)
	from frappe.utils import get_datetime, now_datetime

	if not row or row.status != "Active" or get_datetime(row.valid_until) <= now_datetime():
		if row and row.status == "Active":
			end_access(row.name, "Expired")
			frappe.db.commit()
		frappe.respond_as_web_page(
			frappe._("Demo link not valid"),
			frappe._("This demo link has expired or is not valid. Please contact us for a new one."),
			http_status_code=403,
		)
		return
	frappe.db.set_value("User", row.demo_user, "enabled", 1)
	frappe.local.login_manager.login_as(row.demo_user, session_end=_remaining_session(row.valid_until))
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = "/desk/shop"


def expire_demo_links():
	"""Hourly: disable users and end sessions of demo links that ran out (also run on every demo request)."""
	from commercial_erp.commercial_erp.doctype.demo_link.demo_link import end_access

	for name in frappe.get_all(
		"Demo Link",
		filters={"status": "Active", "valid_until": ["<=", frappe.utils.now_datetime()]},
		pluck="name",
	):
		end_access(name, "Expired")


def check_demo_session():
	"""before_request: a demo user whose link expired is signed out immediately, not at the next hourly job."""
	user = frappe.session.user
	if not user or not user.startswith("demo-link-"):
		return
	valid_until = frappe.db.get_value("Demo Link", {"demo_user": user, "status": "Active"}, "valid_until")
	from frappe.utils import get_datetime, now_datetime

	if not valid_until or get_datetime(valid_until) <= now_datetime():
		expire_demo_links()
		frappe.local.login_manager.logout()
		frappe.throw(frappe._("Your demo has ended."), frappe.AuthenticationError)


@frappe.whitelist()
def setup_status():
	from commercial_erp.setup.checklist import status

	return status()


@frappe.whitelist()
def health_check():
	from commercial_erp.setup.audit import run

	return run()


def boot_session(bootinfo):
	"""The "Framework" app (developer tools) is not offered on the apps screen or the app switcher, and
	there is no outgoing email in a shop setup, so the desk never offers to send one."""
	for app in bootinfo.get("app_data") or []:
		if app.get("app_name") == "frappe":
			app["on_apps_screen"] = False
	if bootinfo.get("user"):
		bootinfo.user.can_email = []
