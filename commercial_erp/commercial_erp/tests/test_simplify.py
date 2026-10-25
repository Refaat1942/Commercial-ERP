import frappe
from frappe.tests import IntegrationTestCase

from commercial_erp.setup import simplify


class TestSimpleMode(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		simplify.hide_fields()

	def test_clutter_is_hidden_but_required_fields_stay(self):
		meta = frappe.get_meta("Sales Invoice")
		for f in ("shipping_rule", "incoterm", "loyalty_program", "project"):
			self.assertTrue(meta.get_field(f).hidden, f)
		for f in ("customer", "items", "posting_date"):
			self.assertFalse(meta.get_field(f).hidden, f)

	def test_restore_brings_fields_back(self):
		simplify.restore()
		self.assertFalse(frappe.get_meta("Sales Invoice").get_field("shipping_rule").hidden)
		simplify.hide_fields()
		self.assertTrue(frappe.get_meta("Sales Invoice").get_field("shipping_rule").hidden)

	def test_new_desk_users_get_unused_modules_blocked(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"simple-mode-{frappe.generate_hash(length=6)}@example.com",
				"first_name": "Simple",
				"send_welcome_email": 0,
			}
		).insert()
		frappe.db.set_value("User", user.name, "user_type", "System User")
		simplify.on_user_update(frappe.get_doc("User", user.name))  # what the User on_update hook calls
		blocked = set(frappe.get_all("Block Module", filters={"parent": user.name}, pluck="module"))
		self.assertIn("Manufacturing", blocked)
		self.assertNotIn("Accounts", blocked)
		self.assertNotIn("Stock", blocked)
		# done once: a module a System Manager unblocks later stays unblocked
		frappe.db.delete("Block Module", {"parent": user.name, "module": "Projects"})
		simplify.on_user_update(frappe.get_doc("User", user.name))
		self.assertFalse(frappe.db.exists("Block Module", {"parent": user.name, "module": "Projects"}))

	def test_administrator_is_never_blocked(self):
		simplify.block_modules()
		self.assertFalse(frappe.db.count("Block Module", {"parent": "Administrator"}))
