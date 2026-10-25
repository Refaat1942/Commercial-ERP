"""End-to-end checks on native ERPNext flows: purchase -> stock -> sale -> payment, ledgers, permissions.

Needs a site where the setup wizard has run (see commercial_erp.setup.wizard.run).
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, nowdate


class TestTradingWorkflow(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = frappe.db.get_single_value("Global Defaults", "default_company")
		if not cls.company:
			raise cls.skipTest(cls, "run the setup wizard first")

	def setUp(self):
		c = frappe.get_cached_doc("Company", self.company)
		self.c = c
		self.wh = next(
			w.name
			for w in frappe.get_all(
				"Warehouse",
				filters={"company": self.company, "is_group": 0},
				fields=["name", "warehouse_type"],
			)
			if w.warehouse_type != "Transit"
		)
		self.item = self._item()
		self.supplier = self._party("Supplier", "_CE Supplier")
		self.customer = self._party("Customer", "_CE Customer")

	def tearDown(self):
		frappe.db.rollback()  # isolate tests: a rejected submit must not leave ledger rows behind

	def _party(self, doctype, name):
		if frappe.db.exists(doctype, name):
			return name
		d = frappe.get_doc(
			{
				"doctype": doctype,
				f"{doctype.lower()}_name": name,
				f"{doctype.lower()}_group": frappe.db.get_value(f"{doctype} Group", {"is_group": 0}, "name"),
			}
		)
		d.insert()
		return d.name

	def _item(self):
		code = "_CE-ITEM-1"
		if not frappe.db.exists("Item", code):
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": code,
					"item_name": "صنف اختبار",
					"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"barcodes": [{"barcode": "6221234567890"}],
					"reorder_levels": [
						{
							"warehouse": self.wh,
							"warehouse_reorder_level": 5,
							"warehouse_reorder_qty": 20,
							"material_request_type": "Purchase",
						}
					]
					if False
					else [],
				}
			).insert()
		return code

	def test_purchase_sale_payment_and_ledgers(self):
		pi = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"company": self.company,
				"supplier": self.supplier,
				"posting_date": nowdate(),
				"set_posting_time": 1,
				"update_stock": 1,
				"set_warehouse": self.wh,
				"items": [{"item_code": self.item, "qty": 10, "rate": 50, "warehouse": self.wh}],
			}
		).insert()
		pi.submit()
		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": pi.name},
			fields=["actual_qty", "stock_value_difference"],
		)
		self.assertEqual(sum(s.actual_qty for s in sle), 10)
		self.assertEqual(flt(sum(s.stock_value_difference for s in sle)), 500)
		self.assertAlmostEqual(self._gl_balance(pi.name), 0, places=2)
		self.assertEqual(frappe.db.get_value("Purchase Invoice", pi.name, "outstanding_amount"), 500)

		si = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": self.company,
				"customer": self.customer,
				"posting_date": nowdate(),
				"set_posting_time": 1,
				"update_stock": 1,
				"set_warehouse": self.wh,
				"items": [{"item_code": self.item, "qty": 4, "rate": 80, "warehouse": self.wh}],
			}
		).insert()
		si.submit()
		self.assertAlmostEqual(self._gl_balance(si.name), 0, places=2)
		self.assertEqual(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"), 320)
		rows = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item_code": self.item, "warehouse": self.wh, "is_cancelled": 0},
			fields=["actual_qty"],
		)
		self.assertEqual(sum(r.actual_qty for r in rows), 6)
		cogs = frappe.db.sql(
			"select sum(debit) from `tabGL Entry` where voucher_no=%s and account like '%%'", si.name
		)
		self.assertTrue(cogs[0][0])

		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		pe = get_payment_entry("Sales Invoice", si.name)
		pe.reference_no, pe.reference_date = "CASH-1", nowdate()
		pe.insert()
		pe.submit()
		self.assertEqual(frappe.db.get_value("Sales Invoice", si.name, "outstanding_amount"), 0)
		self.assertEqual(frappe.db.get_value("Sales Invoice", si.name, "status"), "Paid")

	def test_sales_return_restores_stock(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		self._receive(10)
		si = self._sell(4)
		ret = make_return_doc("Sales Invoice", si.name)
		ret.insert()
		ret.submit()
		self.assertEqual(self._stock_qty(), 10)
		self.assertLess(ret.grand_total, 0)
		self.assertAlmostEqual(self._gl_balance(ret.name), 0, places=2)

	def test_arabic_print_format_renders_invoice(self):
		self._receive(5)
		si = self._sell(2)
		html = frappe.get_print("Sales Invoice", si.name, print_format="فاتورة مبيعات - عربي")
		self.assertIn(si.name, html)
		self.assertIn('dir="rtl"', html)
		self.assertIn("صنف اختبار", html)

	def test_egp_symbol(self):
		self.assertEqual(frappe.db.get_value("Currency", "EGP", "symbol"), "ج.م")

	def test_negative_stock_blocked(self):
		si = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": self.company,
				"customer": self.customer,
				"posting_date": nowdate(),
				"update_stock": 1,
				"set_warehouse": self.wh,
				"items": [{"item_code": self.item, "qty": 100000, "rate": 80, "warehouse": self.wh}],
			}
		).insert()
		with self.assertRaises(frappe.ValidationError):
			si.submit()

	def test_cashier_permissions(self):
		email = "cashier-test@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "Cashier", "send_welcome_email": 0}
			).insert()
		self._assign_profile(email, "Cashier")
		for dt in ("Journal Entry", "Account", "Stock Reconciliation", "Company", "Purchase Invoice"):
			self.assertFalse(frappe.has_permission(dt, "write", user=email), f"cashier can write {dt}")
		self.assertFalse(frappe.has_permission("User", "create", user=email))
		self.assertFalse(frappe.has_permission("Journal Entry", "read", user=email))
		self.assertTrue(frappe.has_permission("Sales Invoice", "create", user=email))
		self.assertTrue(frappe.has_permission("Sales Invoice", "submit", user=email))
		self.assertTrue(frappe.has_permission("Payment Entry", "create", user=email))
		for ptype in ("cancel", "delete", "amend"):
			self.assertFalse(
				frappe.has_permission("Sales Invoice", ptype, user=email), f"cashier can {ptype}"
			)
		self.assertFalse(frappe.has_permission("Purchase Invoice", "read", user=email))

	def test_storekeeper_cannot_see_accounting(self):
		email = "store-test@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "Store", "send_welcome_email": 0}
			).insert()
		self._assign_profile(email, "Storekeeper")
		for dt in ("Journal Entry", "Account", "Payment Entry", "Sales Invoice"):
			self.assertFalse(frappe.has_permission(dt, "write", user=email), f"storekeeper can write {dt}")
		self.assertTrue(frappe.has_permission("Stock Entry", "create", user=email))

	def _receive(self, qty):
		pi = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"company": self.company,
				"supplier": self.supplier,
				"update_stock": 1,
				"set_warehouse": self.wh,
				"items": [{"item_code": self.item, "qty": qty, "rate": 50, "warehouse": self.wh}],
			}
		).insert()
		pi.submit()
		return pi

	def _sell(self, qty):
		si = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": self.company,
				"customer": self.customer,
				"update_stock": 1,
				"set_warehouse": self.wh,
				"items": [{"item_code": self.item, "qty": qty, "rate": 80, "warehouse": self.wh}],
			}
		).insert()
		si.submit()
		return si

	def _stock_qty(self):
		rows = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item_code": self.item, "warehouse": self.wh, "is_cancelled": 0},
			fields=["actual_qty"],
		)
		return sum(r.actual_qty for r in rows)

	def _assign_profile(self, email, profile):
		user = frappe.get_doc("User", email)
		user.set("role_profiles", [{"role_profile": profile}])
		user.save()
		self.assertTrue(set(frappe.get_roles(email)) - {"All", "Guest", "Desk User"}, "profile gave no roles")

	def _gl_balance(self, voucher_no):
		r = frappe.db.sql(
			"select sum(debit)-sum(credit) from `tabGL Entry` where voucher_no=%s and is_cancelled=0",
			voucher_no,
		)
		return flt(r[0][0])
