"""Shop users log in with a plain user name (e.g. "ahmed"), not an email address, and the name is
case sensitive ("Ahmed" is not "ahmed"). No email server is needed: a user created without an
email gets an internal address that is never mailed."""

import re

import frappe
from frappe import _

INTERNAL_DOMAIN = "users.fes.local"


def configure():
	ss = frappe.get_single("System Settings")
	changed = False
	for field, value in {
		"allow_login_using_user_name": 1,
		"login_with_email_link": 0,
		"disable_standard_email_footer": 1,
	}.items():
		if ss.meta.has_field(field) and ss.get(field) != value:
			ss.set(field, value)
			changed = True
	if changed:
		ss.flags.ignore_permissions = True
		ss.save()

	tz = frappe.db.get_single_value("System Settings", "time_zone")
	if tz and frappe.db.get_default("time_zone") != tz:
		frappe.db.set_default("time_zone", tz)  # new users start in the shop's time zone

	# the email is optional (filled in from the user name) and no welcome mail is sent
	for fieldname, prop, value, ptype in (
		("email", "reqd", "0", "Check"),
		("username", "bold", "1", "Check"),
		("send_welcome_email", "default", "0", "Text"),
		("time_zone", "default", "Africa/Cairo", "Text"),
		("language", "default", "ar", "Text"),
	):
		frappe.make_property_setter(
			{
				"doctype": "User",
				"doctype_or_field": "DocField",
				"fieldname": fieldname,
				"property": prop,
				"value": value,
				"property_type": ptype,
			},
			validate_fields_for_doctype=False,
		)


def internal_email(username):
	local = re.sub(r"[^a-z0-9._-]", "", (username or "").lower()).strip("._-")
	if not local:
		local = "user-" + frappe.generate_hash(length=8)
	email = f"{local}@{INTERNAL_DOMAIN}"
	if frappe.db.exists("User", email):
		email = f"{local}-{frappe.generate_hash(length=4)}@{INTERNAL_DOMAIN}"
	return email


def before_user_insert(doc, method=None):
	if doc.get("is_admin") or doc.get("is_guest"):
		return
	if doc.username and frappe.db.exists("User", {"username": doc.username.strip(" @")}):
		frappe.throw(_("User name {0} is already taken").format(doc.username), title=_("Duplicate User Name"))
	if not (doc.email or "").strip():
		if not (doc.username or "").strip():
			frappe.throw(_("Enter a user name"), title=_("Missing User Name"))
		doc.email = internal_email(doc.username)
		doc.send_welcome_email = 0
	elif doc.email.lower().endswith("@" + INTERNAL_DOMAIN):
		doc.send_welcome_email = 0


def is_internal(email):
	return (email or "").lower().endswith("@" + INTERNAL_DOMAIN)


def before_login(login_manager=None):
	"""Case-sensitive login: "Ahmed" only logs in the user whose user name is exactly "Ahmed".
	MariaDB compares case-insensitively, so the exact match is checked here before the password."""
	usr = (frappe.form_dict.get("usr") or "").strip()
	if not usr:
		return
	exact = frappe.db.sql(
		"""select name from `tabUser`
		where binary name = %(u)s or binary username = %(u)s or binary mobile_no = %(u)s limit 1""",
		{"u": usr},
	)
	if exact:
		return
	loose = frappe.db.sql(
		"select name from `tabUser` where name = %(u)s or username = %(u)s limit 1", {"u": usr}
	)
	if loose:
		# same message as a wrong password, so it does not reveal which names exist
		login_manager.fail("Invalid login credentials", user=usr)
