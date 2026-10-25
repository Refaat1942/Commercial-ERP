"""Egypt-specific master data on top of native doctypes (idempotent, no tax rates, no legal claims)."""

import frappe

GOVERNORATES = [
	"القاهرة", "الجيزة", "الإسكندرية", "القليوبية", "الشرقية", "الدقهلية", "البحيرة", "المنوفية",
	"الغربية", "كفر الشيخ", "دمياط", "بورسعيد", "الإسماعيلية", "السويس", "شمال سيناء", "جنوب سيناء",
	"الفيوم", "بني سويف", "المنيا", "أسيوط", "سوهاج", "قنا", "الأقصر", "أسوان", "البحر الأحمر",
	"الوادي الجديد", "مطروح",
]  # fmt: skip

UOMS = ["كرتونة", "دستة", "علبة", "كيس", "زجاجة", "عبوة", "رزمة"]

CUSTOMER_GROUPS = ["عملاء قطاعي", "عملاء جملة"]
SUPPLIER_GROUPS = ["موردو بضاعة", "موردو خدمات"]
SELLING_PRICE_LISTS = ["سعر القطاعي", "سعر الجملة"]

EXPENSE_ACCOUNTS = [
	"إيجار",
	"كهرباء ومياه وغاز",
	"رواتب وأجور",
	"نقل وشحن",
	"اتصالات وإنترنت",
	"دعاية وإعلان",
	"صيانة وإصلاحات",
	"مصروفات نثرية",
]
WALLET_ACCOUNT = "محافظ إلكترونية"
BANK_ACCOUNT = "حساب بنكي رئيسي"
MODES_OF_PAYMENT = {"فودافون كاش": WALLET_ACCOUNT, "إنستاباي": WALLET_ACCOUNT}


def apply():
	_territories()
	_uoms()
	_groups()
	_price_lists()
	company = frappe.db.get_single_value("Global Defaults", "default_company")
	if company:
		_accounts(company)
		_modes_of_payment(company)


def _territories():
	if not frappe.db.exists("Territory", "Egypt"):
		return
	if not frappe.db.get_value("Territory", "Egypt", "is_group"):
		frappe.db.set_value("Territory", "Egypt", "is_group", 1)
	for name in GOVERNORATES:
		if not frappe.db.exists("Territory", name):
			frappe.get_doc(
				{"doctype": "Territory", "territory_name": name, "parent_territory": "Egypt", "is_group": 0}
			).insert(ignore_permissions=True)


def _uoms():
	for name in UOMS:
		if not frappe.db.exists("UOM", name):
			frappe.get_doc({"doctype": "UOM", "uom_name": name, "must_be_whole_number": 1}).insert(
				ignore_permissions=True
			)


def _groups():
	for doctype, parent_field, root, names in (
		("Customer Group", "parent_customer_group", "All Customer Groups", CUSTOMER_GROUPS),
		("Supplier Group", "parent_supplier_group", "All Supplier Groups", SUPPLIER_GROUPS),
	):
		for name in names:
			if not frappe.db.exists(doctype, name):
				frappe.get_doc(
					{
						"doctype": doctype,
						f"{frappe.scrub(doctype)}_name": name,
						parent_field: root,
						"is_group": 0,
					}
				).insert(ignore_permissions=True)


def _price_lists():
	for name in SELLING_PRICE_LISTS:
		if not frappe.db.exists("Price List", name):
			frappe.get_doc(
				{
					"doctype": "Price List",
					"price_list_name": name,
					"currency": "EGP",
					"selling": 1,
					"enabled": 1,
					"price_not_uom_dependent": 1,
				}
			).insert(ignore_permissions=True)


def _group_account(company, number):
	return frappe.db.get_value("Account", {"company": company, "account_number": number, "is_group": 1})


def _ensure_account(company, parent, name, account_type=None):
	existing = frappe.db.get_value("Account", {"company": company, "account_name": name})
	if existing or not parent:
		return existing
	doc = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": name,
			"company": company,
			"parent_account": parent,
			"is_group": 0,
			**({"account_type": account_type} if account_type else {}),
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _accounts(company):
	"""Typical small-shop expense heads and e-wallet / bank leaves, under the native Arabic chart."""
	expenses = _group_account(company, "5200")  # indirect expenses in "Standard with Numbers"
	for name in EXPENSE_ACCOUNTS:
		_ensure_account(company, expenses, name)
	bank_group = _group_account(company, "1200")
	_ensure_account(company, bank_group, WALLET_ACCOUNT, "Bank")
	_ensure_account(company, bank_group, BANK_ACCOUNT, "Bank")


def _modes_of_payment(company):
	for mode, account_name in MODES_OF_PAYMENT.items():
		account = frappe.db.get_value("Account", {"company": company, "account_name": account_name})
		if not account:
			continue
		if frappe.db.exists("Mode of Payment", mode):
			continue
		frappe.get_doc(
			{
				"doctype": "Mode of Payment",
				"mode_of_payment": mode,
				"type": "Bank",
				"enabled": 1,
				"accounts": [{"company": company, "default_account": account}],
			}
		).insert(ignore_permissions=True)
