import frappe
from frappe.tests import IntegrationTestCase

from commercial_erp.setup.audit import checks


def result(key):
	return next(c for c in checks() if c["key"] == key)


class TestAccountingAudit(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_healthy_site_passes_every_check(self):
		failed = [c for c in checks() if not c["ok"]]
		self.assertFalse(failed, failed)

	def test_detects_stock_balance_that_disagrees_with_movements(self):
		if not frappe.db.count("Bin"):
			self.skipTest("needs stock data (run the demo seed)")
		frappe.db.sql("update `tabBin` set actual_qty = actual_qty + 5 limit 1")
		self.assertFalse(result("bin_vs_sle")["ok"])

	def test_detects_stock_value_that_disagrees_with_the_ledger(self):
		if not frappe.db.count("Bin"):
			self.skipTest("needs stock data (run the demo seed)")
		frappe.db.sql("update `tabBin` set stock_value = stock_value + 500 limit 1")
		self.assertFalse(result("stock_vs_gl")["ok"])

	def test_detects_an_unposted_invoice(self):
		name = frappe.db.get_value("Sales Invoice", {"docstatus": 1})
		if not name:
			self.skipTest("needs invoices (run the demo seed)")
		frappe.db.sql("update `tabGL Entry` set is_cancelled = 1 where voucher_no = %s", name)
		self.assertFalse(result("posted")["ok"])

	def tearDown(self):
		frappe.db.rollback()
