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

	def test_framework_tools_are_hidden_from_the_rail(self):
		from frappe.desk.doctype.dock.dock import get_site_dock

		arrange.hide_framework_dock()
		rows = get_site_dock("frappe")
		self.assertTrue(rows)
		self.assertTrue(all(r.get("hidden") for r in rows))

	def test_global_search_is_limited_to_business_documents(self):
		arrange.trim_global_search()
		doctypes = {
			r.document_type for r in frappe.get_single("Global Search Settings").allowed_in_global_search
		}
		self.assertIn("Sales Invoice", doctypes)
		self.assertFalse(doctypes & {"Web Page", "Lead", "Work Order", "Project", "Country"})

	def test_module_landing_pages_have_no_long_link_cards(self):
		arrange.simplify_workspaces()
		for name in arrange.MODULE_HOMES:
			content = frappe.db.get_value("Workspace", name, "content") or ""
			self.assertNotIn('"type": "card"', content)

	def test_unused_module_workspaces_are_hidden(self):
		arrange.simplify_workspaces()
		for name in ("Manufacturing", "Projects", "Assets", "Support", "CRM"):
			if frappe.db.exists("Workspace", name):
				self.assertEqual(frappe.db.get_value("Workspace", name, "is_hidden"), 1)
		self.assertEqual(frappe.db.get_value("Workspace", "Shop", "is_hidden"), 0)

	def test_reports_run_instantly(self):
		arrange.fast_reports()
		self.assertFalse(frappe.db.count("Report", {"prepared_report": 1}))

	def test_unused_form_tabs_are_hidden(self):
		arrange.simplify_forms()
		meta = frappe.get_meta("Item")
		self.assertTrue(meta.get_field("manufacturing").hidden)
