import frappe
from frappe.tests import IntegrationTestCase

from commercial_erp.setup.company import (
	PURCHASE_TEMPLATE,
	SALES_TEMPLATE,
	VAT_INPUT,
	VAT_OUTPUT,
	setup_egypt_company,
)
from commercial_erp.setup.defaults import TRACKED_DOCTYPES
from commercial_erp.setup.roles import ROLE_PROFILES


class TestCommercialERPInstall(IntegrationTestCase):
	def test_system_defaults(self):
		settings = frappe.get_single("System Settings")
		self.assertEqual(settings.country, "Egypt")
		self.assertEqual(settings.time_zone, "Africa/Cairo")
		self.assertEqual(settings.date_format, "dd-mm-yyyy")
		self.assertEqual(settings.first_day_of_the_week, "Saturday")
		self.assertEqual(frappe.db.get_value("Language", "ar", "enabled"), 1)
		self.assertEqual(frappe.db.get_value("Language", "en", "enabled"), 1)
		self.assertEqual(frappe.db.get_value("Currency", "EGP", "enabled"), 1)

	def test_negative_stock_disabled(self):
		self.assertEqual(frappe.db.get_single_value("Stock Settings", "allow_negative_stock"), 0)

	def test_role_profiles(self):
		for profile, roles in ROLE_PROFILES.items():
			doc = frappe.get_doc("Role Profile", profile)
			self.assertEqual({r.role for r in doc.roles}, {r for r in roles if frappe.db.exists("Role", r)})

	def test_cashier_cannot_do_accounting(self):
		roles = {r.role for r in frappe.get_doc("Role Profile", "Cashier").roles}
		self.assertFalse(roles & {"Accounts Manager", "Accounts User", "System Manager"})

	def test_audit_trail_enabled(self):
		for doctype in TRACKED_DOCTYPES:
			self.assertTrue(frappe.get_meta(doctype).track_changes, doctype)

	def test_arabic_print_format_renders(self):
		self.assertTrue(frappe.db.exists("Print Format", "فاتورة مبيعات - عربي"))
		html = frappe.db.get_value("Print Format", "فاتورة مبيعات - عربي", "html")
		self.assertIn('dir="rtl"', html)


class TestEgyptCompany(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Company", "_Test Egypt Co"):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": "_Test Egypt Co",
					"abbr": "_TEC",
					"country": "Egypt",
					"default_currency": "EGP",
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard with Numbers",
				}
			).insert()

	def test_vat_accounts_and_optional_14_percent_templates(self):
		for name in (VAT_OUTPUT, VAT_INPUT):
			self.assertTrue(frappe.db.exists("Account", {"company": "_Test Egypt Co", "account_name": name}))
		for dt, title in (
			("Sales Taxes and Charges Template", SALES_TEMPLATE),
			("Purchase Taxes and Charges Template", PURCHASE_TEMPLATE),
		):
			tpl = frappe.get_doc(dt, {"title": title, "company": "_Test Egypt Co"})
			self.assertEqual([t.rate for t in tpl.taxes], [14])
			self.assertFalse(tpl.is_default)  # VAT stays optional

	def test_setup_is_idempotent(self):
		before = frappe.db.count("Account", {"company": "_Test Egypt Co"})
		setup_egypt_company("_Test Egypt Co")
		self.assertEqual(frappe.db.count("Account", {"company": "_Test Egypt Co"}), before)
