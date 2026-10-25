"""Time-limited demo access for a prospective customer.

Creating a Demo Link creates a temporary demo user and a one-click sign-in link that stops working at
`valid_until`. Only allowed on a dedicated demo site (site_config: "allow_demo_links": 1) so a link can
never open a site that holds real business data."""

import hashlib
import secrets

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, get_url, now_datetime

DEMO_DOMAIN = "demo.example.com"
ROLE_PROFILES = {
	"Owner": None,  # explicit roles, never System Manager
	"Cashier": "Cashier",
	"Storekeeper": "Storekeeper",
	"Accountant": "Accountant",
}


def token_digest(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()


class DemoLink(Document):
	def validate(self):
		if not frappe.conf.get("allow_demo_links"):
			frappe.throw(
				_(
					"Demo links can only be created on a dedicated demo site. "
					"On that site run: bench --site <site> set-config allow_demo_links 1"
				)
			)
		if not 1 <= int(self.valid_hours or 0) <= 720:
			frappe.throw(_("Valid For must be between 1 and 720 hours"))

	def before_insert(self):
		token = secrets.token_urlsafe(24)
		self.token_hash = token_digest(token)
		self.valid_until = add_to_date(now_datetime(), hours=int(self.valid_hours))
		self.status = "Active"
		self.demo_user = self._create_user()
		self.login_link = f"{get_url()}/api/method/commercial_erp.api.demo_login?token={token}"

	def _create_user(self):
		from commercial_erp.setup.demo import DEMO_OWNER_ROLES

		email = f"demo-link-{secrets.token_hex(4)}@{DEMO_DOMAIN}"
		user = frappe.new_doc("User")
		user.update(
			{
				"email": email,
				"first_name": self.customer_name,
				"send_welcome_email": 0,
				"language": "ar",
				"time_zone": "Africa/Cairo",
				"new_password": secrets.token_urlsafe(18),
				"default_workspace": "Shop",
			}
		)
		profile = ROLE_PROFILES[self.role_profile]
		if profile:
			user.set("role_profiles", [{"role_profile": profile}])
		else:
			user.set("roles", [{"role": r} for r in DEMO_OWNER_ROLES if frappe.db.exists("Role", r)])
		user.flags.ignore_permissions = True
		user.insert()
		return user.name

	def on_trash(self):
		if self.demo_user and frappe.db.exists("User", self.demo_user):
			frappe.delete_doc("User", self.demo_user, force=1, ignore_permissions=True)


def end_access(name: str, status: str):
	doc = frappe.get_doc("Demo Link", name)
	if doc.demo_user and frappe.db.exists("User", doc.demo_user):
		frappe.db.set_value("User", doc.demo_user, "enabled", 0)
		from frappe.sessions import clear_sessions

		clear_sessions(doc.demo_user, force=True)
	frappe.db.set_value("Demo Link", name, "status", status)


@frappe.whitelist()
def revoke(name: str):
	frappe.only_for("System Manager")
	end_access(name, "Revoked")
