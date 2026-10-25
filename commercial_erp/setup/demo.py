"""Optional, clearly-labelled demo data so the system can be tried with realistic numbers.

    bench --site SITE execute commercial_erp.setup.demo.seed          # items, parties, 45 days of trade
    bench --site SITE execute commercial_erp.setup.demo.create_users --kwargs '{"password": "..."}'
    bench --site SITE execute commercial_erp.setup.demo.clear         # removes everything seeded

NEVER run on a site that holds real business data. Everything created is tagged (`DEMO-SEED` in
remarks, `DEMO-` item codes, `[تجريبي]` party names) so `clear` can find it. Prices and quantities are
invented for demonstration; no tax is applied.
"""

import random

import frappe
from frappe.utils import add_days, getdate, nowdate

TAG = "DEMO-SEED"
DEMO_SUFFIX = "[تجريبي]"
DEMO_DOMAIN = "demo.example.com"

# code, name, group, uom, cost, retail, wholesale, reorder_level, opening_qty
ITEMS = [
	("DEMO-001", "زيت عباد الشمس 1 لتر", "مواد غذائية", "زجاجة", 62, 72, 68, 30, 120),
	("DEMO-002", "سكر أبيض 1 كجم", "مواد غذائية", "كيس", 32, 38, 35, 40, 200),
	("DEMO-003", "أرز مصري 1 كجم", "مواد غذائية", "كيس", 28, 34, 31, 40, 180),
	("DEMO-004", "مكرونة 400 جم", "مواد غذائية", "كيس", 9, 12, 10.5, 60, 300),
	("DEMO-005", "شاي أسود 100 جم", "مواد غذائية", "علبة", 24, 30, 27, 25, 90),
	("DEMO-006", "معجون طماطم 190 جم", "مواد غذائية", "علبة", 11, 14, 12.5, 40, 150),
	("DEMO-007", "فول مدمس معلب", "مواد غذائية", "علبة", 14, 18, 16, 30, 110),
	("DEMO-008", "عصير فواكه 250 مل", "مشروبات", "علبة", 6, 8.5, 7, 80, 400),
	("DEMO-009", "مياه معدنية 1.5 لتر", "مشروبات", "زجاجة", 5, 7, 6, 100, 500),
	("DEMO-010", "مشروب غازي 1 لتر", "مشروبات", "زجاجة", 13, 17, 15, 60, 240),
	("DEMO-011", "مسحوق غسيل 1 كجم", "منظفات", "كيس", 42, 52, 47, 25, 100),
	("DEMO-012", "سائل أطباق 750 مل", "منظفات", "زجاجة", 21, 27, 24, 30, 120),
	("DEMO-013", "منظف أرضيات 1 لتر", "منظفات", "زجاجة", 18, 24, 21, 25, 100),
	("DEMO-014", "صابون استحمام", "منظفات", "علبة", 7, 10, 8.5, 60, 300),
	("DEMO-015", "مناديل ورقية", "ورقيات", "علبة", 10, 14, 12, 50, 250),
	("DEMO-016", "ورق تواليت 6 رولات", "ورقيات", "رزمة", 36, 45, 40, 30, 140),
	("DEMO-017", "بسكويت سادة", "مواد غذائية", "علبة", 4, 6, 5, 100, 450),
	("DEMO-018", "ملح طعام 700 جم", "مواد غذائية", "كيس", 5, 7, 6, 40, 160),
	("DEMO-019", "دقيق 1 كجم", "مواد غذائية", "كيس", 17, 21, 19, 40, 200),
	("DEMO-020", "عدس أصفر 500 جم", "مواد غذائية", "كيس", 20, 25, 22, 30, 130),
]  # fmt: skip

ITEM_GROUPS = ["مواد غذائية", "مشروبات", "منظفات", "ورقيات"]

CUSTOMERS = [
	("عميل نقدي", "عملاء قطاعي"),
	("سوبر ماركت الأمل", "عملاء جملة"),
	("بقالة النور", "عملاء جملة"),
	("مطعم السلام", "عملاء جملة"),
	("أحمد محمد", "عملاء قطاعي"),
	("منى عبد الله", "عملاء قطاعي"),
	("كافيه الكورنيش", "عملاء جملة"),
	("محمود حسن", "عملاء قطاعي"),
]
SUPPLIERS = [
	("شركة النيل للتوزيع", "موردو بضاعة"),
	("مصنع الدلتا للمواد الغذائية", "موردو بضاعة"),
	("الشركة المتحدة للمنظفات", "موردو بضاعة"),
	("مخازن الصعيد للورقيات", "موردو بضاعة"),
]

DEMO_USERS = {
	"demo-owner": ("Demo Owner", "Demo Owner Profile"),
	"demo-cashier": ("Demo Cashier", "Cashier"),
	"demo-store": ("Demo Storekeeper", "Storekeeper"),
	"demo-accountant": ("Demo Accountant", "Accountant"),
}
# The demo owner must not be a System Manager: demo logins are meant to be shared.
DEMO_OWNER_ROLES = [
	"Accounts Manager",
	"Accounts User",
	"Sales Manager",
	"Sales User",
	"Purchase Manager",
	"Purchase User",
	"Stock Manager",
	"Stock User",
	"Item Manager",
	"Report Manager",
]


def _ean13(prefix12: str) -> str:
	digits = [int(c) for c in prefix12]
	total = sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits))
	return prefix12 + str((10 - total % 10) % 10)


def _company():
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if not company:
		frappe.throw("Run the setup wizard first (no default company).")
	return company


def _warehouse(company):
	rows = frappe.get_all(
		"Warehouse",
		filters={"company": company, "is_group": 0},
		fields=["name", "warehouse_name", "warehouse_type"],
	)
	rows = [w for w in rows if w.warehouse_type != "Transit"]
	for w in rows:
		if w.warehouse_name in ("Stores", "مخازن"):
			return w.name
	if rows:
		return rows[0].name
	frappe.throw("No stock warehouse found.")


def seed(days=45, seed_value=42):
	if frappe.db.exists("Item", "DEMO-001"):
		return "demo data already present (run clear first to rebuild)"
	frappe.flags.in_demo_seed = True
	rnd = random.Random(seed_value)
	company, today = _company(), getdate(nowdate())
	wh = _warehouse(company)
	_masters(wh)

	stock = {}
	# 1) opening purchases, oldest first, so every later sale has stock
	for i, supplier_idx in enumerate([0, 1, 2, 3]):
		supplier = f"{SUPPLIERS[supplier_idx][0]} {DEMO_SUFFIX}"
		picks = [it for k, it in enumerate(ITEMS) if k % 4 == supplier_idx]
		_purchase(
			company,
			wh,
			supplier,
			add_days(today, -days),
			[(it[0], it[8], it[4]) for it in picks],
			stock,
			vat=i % 2 == 0,
		)

	# 2) trading days: sales (cash + credit), periodic restocking, payments, expenses
	customers = [f"{c[0]} {DEMO_SUFFIX}" for c in CUSTOMERS]
	sales_invoices = []
	for d in range(days - 1, -1, -1):
		day = add_days(today, -d)
		for _ in range(rnd.randint(5, 10)):
			cust_idx = rnd.choices(range(len(customers)), weights=[5, 2, 2, 1, 2, 2, 1, 2])[0]
			wholesale = CUSTOMERS[cust_idx][1] == "عملاء جملة"
			lines = []
			for it in rnd.sample(ITEMS, rnd.randint(1, 4)):
				qty = rnd.randint(3, 15) if wholesale else rnd.randint(1, 5)
				if stock.get(it[0], 0) - qty < 0:
					continue
				lines.append((it[0], qty, it[6] if wholesale else it[5]))
			if not lines:
				continue
			cash = (not wholesale) or rnd.random() < 0.3
			si = _sale(
				company, wh, customers[cust_idx], day, lines, stock, vat=wholesale and rnd.random() < 0.7
			)
			sales_invoices.append(si)
			if cash:
				_payment("Receive", "Sales Invoice", si, day, "Cash")
			elif rnd.random() < 0.5:
				_payment("Receive", "Sales Invoice", si, add_days(day, rnd.randint(3, 12)), "Cash", part=0.5)
		if d % 6 == 0 and d:  # restock the items that are getting low
			low = [it for it in ITEMS if stock.get(it[0], 0) < it[7] * 2]
			if low:
				supplier = f"{SUPPLIERS[rnd.randrange(len(SUPPLIERS))][0]} {DEMO_SUFFIX}"
				pi = _purchase(
					company,
					wh,
					supplier,
					day,
					[(it[0], int(it[8] * 0.7), it[4]) for it in low],
					stock,
					vat=rnd.random() < 0.6,
				)
				if rnd.random() < 0.6:
					_payment("Pay", "Purchase Invoice", pi, add_days(day, 5), "Cash")

	# opening-balance suppliers stay partly unpaid on purpose
	for _ in range(2):
		pi = frappe.get_all(
			"Purchase Invoice", {"remarks": TAG, "docstatus": 1, "outstanding_amount": [">", 0]}, pluck="name"
		)
		if pi:
			_payment("Pay", "Purchase Invoice", rnd.choice(pi), today, "Cash", part=0.6)

	_capital(company, add_days(today, -days - 1))
	_expenses(company, today, days)
	_returns(company, wh, sales_invoices[:2], stock)
	# leave a few items below reorder level so the low-stock report has something to show
	_drain(company, wh, customers[0], today, stock)
	frappe.db.commit()
	return {
		"items": len(ITEMS),
		"sales_invoices": frappe.db.count("Sales Invoice", {"remarks": TAG}),
		"purchase_invoices": frappe.db.count("Purchase Invoice", {"remarks": TAG}),
	}


def _masters(wh):
	for g in ITEM_GROUPS:
		if not frappe.db.exists("Item Group", g):
			frappe.get_doc(
				{"doctype": "Item Group", "item_group_name": g, "parent_item_group": "All Item Groups"}
			).insert(ignore_permissions=True)
	for n, (name, group) in enumerate(CUSTOMERS):
		doc = {
			"doctype": "Customer",
			"customer_name": f"{name} {DEMO_SUFFIX}",
			"customer_group": group,
			"territory": "Egypt",
			"customer_type": "Company" if group == "عملاء جملة" else "Individual",
		}
		if not frappe.db.exists("Customer", {"customer_name": doc["customer_name"]}):
			frappe.get_doc(doc).insert(ignore_permissions=True)
	for name, group in SUPPLIERS:
		sname = f"{name} {DEMO_SUFFIX}"
		if not frappe.db.exists("Supplier", {"supplier_name": sname}):
			frappe.get_doc({"doctype": "Supplier", "supplier_name": sname, "supplier_group": group}).insert(
				ignore_permissions=True
			)
	for n, (code, name, group, uom, cost, retail, wholesale, reorder, qty) in enumerate(ITEMS):
		if not frappe.db.exists("UOM", uom):
			uom = "Nos"
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": code,
				"item_name": name,
				"item_group": group,
				"stock_uom": uom,
				"is_stock_item": 1,
				"standard_rate": retail,
				"valuation_rate": cost,
				"description": f"{name} - {DEMO_SUFFIX}",
				"barcodes": [{"barcode": _ean13(f"200000000{n + 1:03d}")}],
				"reorder_levels": [
					{
						"warehouse": wh,
						"warehouse_reorder_level": reorder,
						"warehouse_reorder_qty": reorder * 2,
						"material_request_type": "Purchase",
					}
				],
			}
		).insert(ignore_permissions=True)
		for plist, price in (("سعر القطاعي", retail), ("سعر الجملة", wholesale)):
			if frappe.db.exists("Price List", plist):
				frappe.get_doc(
					{
						"doctype": "Item Price",
						"item_code": code,
						"price_list": plist,
						"price_list_rate": price,
						"currency": "EGP",
					}
				).insert(ignore_permissions=True)


def _add_vat(doc, template_doctype, company):
	"""Apply the optional 14% VAT template (if the company has it) to a demo document."""
	from erpnext.controllers.accounts_controller import get_taxes_and_charges

	title = "ضريبة القيمة المضافة 14% - " + ("مبيعات" if "Sales" in template_doctype else "مشتريات")
	name = frappe.db.get_value(template_doctype, {"title": title, "company": company})
	if not name:
		return
	doc.taxes_and_charges = name
	for row in get_taxes_and_charges(template_doctype, name):
		doc.append("taxes", row)


def _purchase(company, wh, supplier, day, lines, stock, vat=False):
	doc = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"company": company,
			"supplier": frappe.db.get_value("Supplier", {"supplier_name": supplier}),
			"posting_date": day,
			"set_posting_time": 1,
			"bill_date": day,
			"due_date": add_days(day, 15),
			"update_stock": 1,
			"set_warehouse": wh,
			"remarks": TAG,
			"items": [{"item_code": c, "qty": q, "rate": r, "warehouse": wh} for c, q, r in lines],
		}
	)
	if vat:
		_add_vat(doc, "Purchase Taxes and Charges Template", company)
	doc.insert(ignore_permissions=True)
	doc.submit()
	for c, q, _r in lines:
		stock[c] = stock.get(c, 0) + q
	return doc.name


def _sale(company, wh, customer, day, lines, stock, vat=False):
	doc = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": company,
			"customer": frappe.db.get_value("Customer", {"customer_name": customer}),
			"posting_date": day,
			"set_posting_time": 1,
			"due_date": add_days(day, 15) if day else day,
			"update_stock": 1,
			"set_warehouse": wh,
			"remarks": TAG,
			"items": [{"item_code": c, "qty": q, "rate": r, "warehouse": wh} for c, q, r in lines],
		}
	)
	if vat:
		_add_vat(doc, "Sales Taxes and Charges Template", company)
	doc.insert(ignore_permissions=True)
	doc.submit()
	for c, q, _r in lines:
		stock[c] = stock.get(c, 0) - q
	return doc.name


def _payment(kind, ref_type, ref_name, day, mode, part=1.0):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	pe = get_payment_entry(ref_type, ref_name)
	pe.posting_date = day
	pe.reference_date = day
	pe.reference_no = f"DEMO-{ref_name}"
	pe.mode_of_payment = mode
	pe.remarks = TAG
	if part < 1:
		amount = round(pe.paid_amount * part, 2)
		pe.paid_amount = pe.received_amount = amount
		for ref in pe.references:
			ref.allocated_amount = amount
	pe.insert(ignore_permissions=True)
	pe.submit()


def _capital(company, day):
	"""Owner's opening cash so the cash balance is plausible."""
	cash = frappe.db.get_value("Company", company, "default_cash_account")
	equity = frappe.db.get_value("Account", {"company": company, "root_type": "Equity", "is_group": 0})
	if not (cash and equity):
		return
	je = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"company": company,
			"posting_date": day,
			"voucher_type": "Opening Entry",
			"user_remark": TAG,
			"accounts": [
				{"account": cash, "debit_in_account_currency": 80000},
				{"account": equity, "credit_in_account_currency": 80000},
			],
		}
	)
	je.insert(ignore_permissions=True)
	je.submit()


def _expenses(company, today, days):
	cash = frappe.db.get_value("Company", company, "default_cash_account")
	cost_center = frappe.db.get_value("Company", company, "cost_center")
	plan = [("إيجار", 6000), ("كهرباء ومياه وغاز", 850), ("رواتب وأجور", 9000), ("اتصالات وإنترنت", 320)]
	for month_offset in range(0, days, 30):
		day = add_days(today, -month_offset - 1)
		for name, amount in plan:
			account = frappe.db.get_value("Account", {"company": company, "account_name": name})
			if not account or not cash:
				continue
			je = frappe.get_doc(
				{
					"doctype": "Journal Entry",
					"company": company,
					"posting_date": day,
					"voucher_type": "Journal Entry",
					"user_remark": TAG,
					"accounts": [
						{"account": account, "debit_in_account_currency": amount, "cost_center": cost_center},
						{"account": cash, "credit_in_account_currency": amount},
					],
				}
			)
			je.insert(ignore_permissions=True)
			je.submit()


def _returns(company, wh, invoices, stock):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc

	for name in invoices:
		ret = make_return_doc("Sales Invoice", name)
		ret.remarks = TAG
		ret.posting_date = nowdate()
		ret.set_posting_time = 1
		for row in ret.items:
			row.qty = -1 if row.qty < 0 else row.qty
			stock[row.item_code] = stock.get(row.item_code, 0) + abs(row.qty)
		ret.insert(ignore_permissions=True)
		ret.submit()


def _drain(company, wh, customer, today, stock):
	"""Sell down three items below their reorder level."""
	for code in ("DEMO-004", "DEMO-009", "DEMO-017"):
		reorder = next(i[7] for i in ITEMS if i[0] == code)
		qty = int(stock.get(code, 0) - reorder + 5)
		if qty > 0:
			rate = next(i[5] for i in ITEMS if i[0] == code)
			si = _sale(company, wh, customer, today, [(code, qty, rate)], stock)
			_payment("Receive", "Sales Invoice", si, today, "Cash")


def create_users(password=None):
	"""Four role-based demo logins. `password` is required: a demo site is shared, so pick one for it."""
	if not password or len(password) < 8:
		frappe.throw('pass kwargs \'{"password": "<at least 8 characters>"}\'')
	from commercial_erp.setup.roles import ROLE_PROFILES

	assert "Cashier" in ROLE_PROFILES
	made = {}
	for local, (first_name, profile) in DEMO_USERS.items():
		email = f"{local}@{DEMO_DOMAIN}"
		user = frappe.get_doc("User", email) if frappe.db.exists("User", email) else frappe.new_doc("User")
		user.update(
			{
				"email": email,
				"first_name": first_name,
				"send_welcome_email": 0,
				"language": "ar",
				"time_zone": "Africa/Cairo",
				"new_password": password,
			}
		)
		if profile == "Demo Owner Profile":  # explicit roles: no System Manager on a shared demo login
			user.set("role_profiles", [])
			user.set("roles", [{"role": r} for r in DEMO_OWNER_ROLES if frappe.db.exists("Role", r)])
		else:
			user.set("role_profiles", [{"role_profile": profile}])
		user.flags.ignore_permissions = True
		user.save()
		made[email] = profile
	frappe.db.commit()
	return made


def clear():
	"""Cancel and delete everything `seed` and `create_users` created."""
	# delete_doc queues one background job per document; run them inline so a few hundred deletes
	# cannot overflow the queue (and nothing is left half-cleaned if workers are busy).
	previous = frappe.in_test
	frappe.in_test = True
	try:
		return _clear()
	finally:
		frappe.in_test = previous


def _clear():
	order = [
		("Payment Entry", {"reference_no": ["like", "DEMO-%"]}),
		("Journal Entry", {"user_remark": TAG}),
		("Sales Invoice", {"remarks": TAG, "is_return": 1}),
		("Sales Invoice", {"remarks": TAG}),
		("Purchase Invoice", {"remarks": TAG}),
	]
	for doctype, filters in order:
		for name in frappe.get_all(doctype, filters=filters, pluck="name", order_by="creation desc"):
			doc = frappe.get_doc(doctype, name)
			if doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
	_purge_orphan_ledgers()
	for item in frappe.get_all("Item", filters={"item_code": ["like", "DEMO-%"]}, pluck="name"):
		for dt in ("Item Price",):
			for p in frappe.get_all(dt, filters={"item_code": item}, pluck="name"):
				frappe.delete_doc(dt, p, force=1, ignore_permissions=True)
		_purge_stock_rows(item)
		frappe.delete_doc("Item", item, force=1, ignore_permissions=True)
	for dt, field in (("Customer", "customer_name"), ("Supplier", "supplier_name")):
		for name in frappe.get_all(dt, filters={field: ["like", f"%{DEMO_SUFFIX}"]}, pluck="name"):
			frappe.delete_doc(dt, name, force=1, ignore_permissions=True)
	for local in DEMO_USERS:
		email = f"{local}@{DEMO_DOMAIN}"
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=1, ignore_permissions=True)
	frappe.db.commit()
	return "demo data removed"


def _purge_stock_rows(item):
	"""Cancelled vouchers leave reversed ledger rows behind; they only reference demo items."""
	for dt in ("Stock Ledger Entry", "Bin", "Repost Item Valuation"):
		if frappe.db.exists("DocType", dt) and frappe.get_meta(dt).has_field("item_code"):
			frappe.db.delete(dt, {"item_code": item})


def _purge_orphan_ledgers():
	"""Deleting a cancelled voucher leaves its reversed GL / payment-ledger rows; drop those whose voucher is gone."""
	for voucher_type in ("Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry"):
		table = f"tab{voucher_type}"
		for ledger in ("GL Entry", "Payment Ledger Entry"):
			if not frappe.db.exists("DocType", ledger):
				continue
			frappe.db.sql(
				f"delete from `tab{ledger}` where voucher_type = %s and voucher_no not in (select name from `{table}`)",
				voucher_type,
			)
