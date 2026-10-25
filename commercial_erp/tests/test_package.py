import frappe
from frappe.desk.doctype.dock.dock import get_site_dock
from frappe.tests import IntegrationTestCase

from commercial_erp.setup import arrange
from commercial_erp.setup.checklist import status


def hidden_modules():
	return {
		r["link_to"] for r in get_site_dock("erpnext") if r.get("link_type") == "Sidebar" and r.get("hidden")
	}


class TestPackages(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		arrange.apply()

	def tearDown(self):
		frappe.db.set_single_value("FES Settings", "package", "Full Business")
		arrange.apply_package("Full Business")

	def test_accounts_and_stock_hides_selling_and_buying(self):
		arrange.apply_package("Accounts and Stock")
		hidden = hidden_modules()
		self.assertTrue({"Selling", "Buying"} <= hidden)
		self.assertFalse({"Stock", "Accounts", "Setup", "Shop"} & hidden)

	def test_accounts_only_and_stock_only(self):
		arrange.apply_package("Accounts Only")
		self.assertTrue({"Selling", "Buying", "Stock"} <= hidden_modules())
		arrange.apply_package("Stock Only")
		hidden = hidden_modules()
		self.assertIn("Accounts", hidden)
		self.assertNotIn("Stock", hidden)

	def test_full_business_restores_everything(self):
		arrange.apply_package("Accounts Only")
		arrange.apply_package("Full Business")
		self.assertFalse({"Selling", "Buying", "Stock", "Accounts"} & hidden_modules())

	def test_saving_settings_applies_the_package(self):
		doc = frappe.get_single("FES Settings")
		doc.package = "Stock Only"
		doc.save()
		self.assertIn("Accounts", hidden_modules())
		self.assertTrue(frappe.db.get_single_value("FES Settings", "applied_on"))

	def test_checklist_is_tailored_to_the_package(self):
		frappe.db.set_single_value("FES Settings", "package", "Accounts Only")
		keys = {s["key"] for s in status()["steps"]}
		self.assertIn("opening_balances", keys)
		self.assertNotIn("items", keys)
		self.assertNotIn("test_sale", keys)
		frappe.db.set_single_value("FES Settings", "package", "Full Business")
		keys = {s["key"] for s in status()["steps"]}
		self.assertTrue({"items", "customers", "suppliers", "test_sale", "test_purchase", "go_live"} <= keys)

	def test_vat_step_is_optional(self):
		frappe.db.set_single_value("FES Settings", "package", "Full Business")
		steps = {s["key"]: s for s in status()["steps"]}
		self.assertTrue(steps["vat"]["optional"])
