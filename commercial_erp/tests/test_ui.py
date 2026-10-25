import frappe
from frappe.tests import IntegrationTestCase

from commercial_erp.api import set_language
from commercial_erp.setup import arrange, brand


class TestBrandingAndNavigation(IntegrationTestCase):
	def test_brand_applied(self):
		brand.apply()
		self.assertEqual(frappe.db.get_single_value("Website Settings", "app_name"), "FES ERP")

	def test_no_onboarding_blocks_left(self):
		arrange.remove_onboarding()
		for name in frappe.get_all("Workspace", pluck="name"):
			content = frappe.db.get_value("Workspace", name, "content") or ""
			self.assertNotIn('"type": "onboarding"', content)
			self.assertFalse(frappe.db.get_value("Workspace", name, "module_onboarding"))

	def test_unwanted_navbar_links_removed(self):
		arrange.clean_navbar()
		doc = frappe.get_single("Navbar Settings")
		for row in list(doc.help_dropdown) + list(doc.settings_dropdown):
			self.assertNotIn("frappe.io", row.route or "")
			self.assertNotIn("clear_demo", row.action or "")

	def test_arrange_is_idempotent(self):
		arrange.apply()
		before = frappe.db.count("Custom Sidebar"), frappe.db.count("Dock")
		arrange.apply()
		self.assertEqual((frappe.db.count("Custom Sidebar"), frappe.db.count("Dock")), before)

	def test_shop_home_exists_with_cards(self):
		arrange.apply()
		ws = frappe.get_doc("Workspace", "Shop")
		self.assertGreaterEqual(len(ws.number_cards), 5)
		self.assertGreaterEqual(len(ws.shortcuts), 10)

	def test_language_switch_validates_input(self):
		with self.assertRaises(frappe.ValidationError):
			set_language("fr")
		frappe.set_user("Administrator")
		self.assertEqual(set_language("en"), "en")
		self.assertEqual(frappe.db.get_value("User", "Administrator", "language"), "en")
		set_language("ar")

	def test_egp_formatting(self):
		cur = frappe.db.get_value("Currency", "EGP", ["symbol", "symbol_on_right", "enabled"], as_dict=True)
		self.assertEqual((cur.symbol, cur.symbol_on_right, cur.enabled), ("ج.م", 1, 1))

	def test_email_footer_has_no_upstream_branding(self):
		from frappe.email.email_body import get_footer

		brand.apply()
		self.assertNotIn("ERPNext", get_footer(None))

	def test_numbers_are_shown_in_full(self):
		arrange.full_numbers()
		self.assertFalse(frappe.db.count("Number Card", {"show_full_number": 0}))

	def test_shop_has_its_own_sidebar(self):
		arrange.apply()
		self.assertTrue(frappe.db.exists("Sidebar", "Shop"))
		self.assertEqual(frappe.db.get_value("Workspace", "Shop", "module"), "Shop")
