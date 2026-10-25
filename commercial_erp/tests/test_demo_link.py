import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

from commercial_erp.api import expire_demo_links
from commercial_erp.commercial_erp.doctype.demo_link.demo_link import revoke, token_digest


class TestDemoLink(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.local.conf.allow_demo_links = 1

	def tearDown(self):
		frappe.local.conf.pop("allow_demo_links", None)

	def _make(self, hours=2, role="Cashier"):
		return frappe.get_doc(
			{
				"doctype": "Demo Link",
				"customer_name": "Test Customer",
				"role_profile": role,
				"valid_hours": hours,
			}
		).insert()

	def test_refused_on_a_site_without_the_demo_flag(self):
		frappe.local.conf.pop("allow_demo_links", None)
		with self.assertRaises(frappe.ValidationError):
			self._make()

	def test_creates_user_link_and_expiry(self):
		doc = self._make(hours=3)
		self.assertEqual(doc.status, "Active")
		self.assertTrue(doc.demo_user.startswith("demo-link-"))
		self.assertIn("demo_login?token=", doc.login_link)
		token = doc.login_link.split("token=")[1]
		self.assertEqual(doc.token_hash, token_digest(token))
		self.assertNotIn(token, doc.token_hash)  # only the hash is stored in the field
		self.assertGreater(doc.valid_until, add_to_date(now_datetime(), hours=2))
		self.assertEqual(frappe.db.get_value("User", doc.demo_user, "enabled"), 1)

	def test_owner_demo_is_not_system_manager(self):
		doc = self._make(role="Owner")
		roles = set(frappe.get_roles(doc.demo_user))
		self.assertNotIn("System Manager", roles)
		self.assertIn("Accounts Manager", roles)

	def test_cashier_demo_cannot_touch_accounting(self):
		doc = self._make(role="Cashier")
		self.assertFalse(frappe.has_permission("Journal Entry", "read", user=doc.demo_user))

	def test_revoke_disables_user(self):
		doc = self._make()
		revoke(doc.name)
		self.assertEqual(frappe.db.get_value("Demo Link", doc.name, "status"), "Revoked")
		self.assertEqual(frappe.db.get_value("User", doc.demo_user, "enabled"), 0)

	def test_hourly_job_expires_old_links(self):
		doc = self._make()
		frappe.db.set_value("Demo Link", doc.name, "valid_until", add_to_date(now_datetime(), hours=-1))
		expire_demo_links()
		self.assertEqual(frappe.db.get_value("Demo Link", doc.name, "status"), "Expired")
		self.assertEqual(frappe.db.get_value("User", doc.demo_user, "enabled"), 0)

	def test_valid_hours_range(self):
		with self.assertRaises(frappe.ValidationError):
			self._make(hours=0)
		with self.assertRaises(frappe.ValidationError):
			self._make(hours=1000)
