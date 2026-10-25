"""Accounting & stock integrity checks ("فحص سلامة الحسابات").

Read-only. Each check returns (key, ok, message) so an owner/accountant can see in one screen that the ledgers
agree with each other: general ledger, stock ledger, receivables/payables and VAT."""

import frappe
from frappe import _
from frappe.utils import flt


def _m(x):
	return f"{flt(x):,.2f}"


TOLERANCE = 1.0  # EGP / unit; rounding differences below this are not reported


def _scalar(sql, args=None):
	rows = frappe.db.sql(sql, args or ())
	return flt(rows[0][0]) if rows and rows[0][0] is not None else 0.0


def _company():
	return frappe.db.get_single_value("Global Defaults", "default_company")


def checks():
	company = _company()
	results = []

	def add(key, ok, message):
		results.append({"key": key, "ok": bool(ok), "message": message})

	# 1. double entry
	diff = _scalar("select sum(debit) - sum(credit) from `tabGL Entry` where is_cancelled = 0")
	add(
		"gl_balanced",
		abs(diff) < 0.01,
		_("Total debit equals total credit (difference {0})").format(_m(diff)),
	)

	bad = frappe.db.sql(
		"""select voucher_type, voucher_no from `tabGL Entry` where is_cancelled = 0
		group by voucher_type, voucher_no having abs(sum(debit) - sum(credit)) > 0.01 limit 5"""
	)
	add(
		"vouchers_balanced",
		not bad,
		_("Every document balances on its own")
		if not bad
		else _("Unbalanced documents: {0}").format(", ".join(b[1] for b in bad)),
	)

	# 2. every submitted invoice / payment posted to the general ledger
	missing = []
	for doctype in ("Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry"):
		table = f"tab{doctype}"
		n = frappe.db.sql(
			f"""select count(*) from `{table}` t where t.docstatus = 1 and not exists
			(select 1 from `tabGL Entry` g where g.voucher_type = %s and g.voucher_no = t.name and g.is_cancelled = 0)""",
			doctype,
		)[0][0]
		if n:
			missing.append(f"{doctype}: {n}")
	add(
		"posted",
		not missing,
		_("All submitted documents are posted to the ledger")
		if not missing
		else _("Not posted: {0}").format("; ".join(missing)),
	)

	# 3. stock ledger agrees with the stock balance (Bin)
	drift = frappe.db.sql(
		"""select b.item_code, b.warehouse from `tabBin` b
		left join (select item_code, warehouse, sum(actual_qty) q from `tabStock Ledger Entry`
			where is_cancelled = 0 group by item_code, warehouse) s
			on s.item_code = b.item_code and s.warehouse = b.warehouse
		where abs(b.actual_qty - ifnull(s.q, 0)) > 0.001 limit 5"""
	)
	add(
		"bin_vs_sle",
		not drift,
		_("Item balances equal the sum of stock movements")
		if not drift
		else _("Balance differs from movements for: {0}").format(", ".join(d[0] for d in drift)),
	)

	neg = _scalar("select count(*) from `tabBin` where actual_qty < 0")
	add(
		"no_negative_stock",
		neg == 0,
		_("No item has a negative balance")
		if neg == 0
		else _("{0} items have negative balances").format(int(neg)),
	)

	# 4. stock value equals the Stock accounts in the general ledger (perpetual inventory)
	perpetual = frappe.db.get_value("Company", company, "enable_perpetual_inventory") if company else 0
	if perpetual:
		stock_value = _scalar("select sum(stock_value) from `tabBin`")
		stock_gl = _scalar(
			"""select sum(g.debit) - sum(g.credit) from `tabGL Entry` g join `tabAccount` a on a.name = g.account
			where g.is_cancelled = 0 and a.account_type = 'Stock' and a.is_group = 0"""
		)
		add(
			"stock_vs_gl",
			abs(stock_value - stock_gl) <= TOLERANCE,
			_("Stock value ({0}) equals the stock account in the ledger ({1})").format(
				_m(stock_value), _m(stock_gl)
			),
		)
	else:
		add(
			"perpetual",
			False,
			_("Perpetual inventory is off: stock is not posted to the ledger automatically"),
		)

	# 5. customers / suppliers: invoices vs ledger
	for party_type, account_type, key, label in (
		("Customer", "Receivable", "receivables", _("Customer balances")),
		("Supplier", "Payable", "payables", _("Supplier balances")),
	):
		ple = _scalar(
			"""select sum(amount) from `tabPayment Ledger Entry` where delinked = 0 and party_type = %s""",
			party_type,
		)
		gl = _scalar(
			"""select sum(g.debit) - sum(g.credit) from `tabGL Entry` g join `tabAccount` a on a.name = g.account
			where g.is_cancelled = 0 and a.account_type = %s and g.party_type = %s""",
			(account_type, party_type),
		)
		gl = gl if party_type == "Customer" else -gl
		add(
			key,
			abs(ple - gl) <= TOLERANCE,
			_("{0}: ledger {1} equals open items {2}").format(label, _m(gl), _m(ple)),
		)

	# 6. VAT accounts equal the tax on documents (only if used)
	if company:
		out_acc = frappe.db.get_value(
			"Account", {"company": company, "account_name": "ضريبة القيمة المضافة - مبيعات"}
		)
		in_acc = frappe.db.get_value(
			"Account", {"company": company, "account_name": "ضريبة القيمة المضافة - مشتريات"}
		)
		if out_acc:
			gl = _scalar(
				"select sum(credit) - sum(debit) from `tabGL Entry` where account = %s and is_cancelled = 0",
				out_acc,
			)
			docs = _scalar(
				"select sum(total_taxes_and_charges) from `tabSales Invoice` where docstatus = 1 and total_taxes_and_charges != 0"
			)
			add(
				"vat_output",
				abs(gl - docs) <= TOLERANCE,
				_("VAT collected: ledger {0} equals invoices {1}").format(_m(gl), _m(docs)),
			)
		if in_acc:
			gl = _scalar(
				"select sum(debit) - sum(credit) from `tabGL Entry` where account = %s and is_cancelled = 0",
				in_acc,
			)
			docs = _scalar(
				"select sum(total_taxes_and_charges) from `tabPurchase Invoice` where docstatus = 1 and total_taxes_and_charges != 0"
			)
			add(
				"vat_input",
				abs(gl - docs) <= TOLERANCE,
				_("VAT paid: ledger {0} equals invoices {1}").format(_m(gl), _m(docs)),
			)

	# 7. company is wired to the right accounts
	if company:
		needed = (
			"default_receivable_account", "default_payable_account", "default_income_account", "default_expense_account",
			"default_cash_account", "stock_adjustment_account", "stock_received_but_not_billed", "round_off_account",
		)  # fmt: skip
		row = frappe.db.get_value("Company", company, list(needed), as_dict=True) or {}
		empty = [f for f in needed if not row.get(f)]
		add(
			"company_accounts",
			not empty,
			_("The company is linked to its default accounts")
			if not empty
			else _("Missing default accounts: {0}").format(", ".join(empty)),
		)
		currency = frappe.db.get_value("Company", company, "default_currency")
		add(
			"currency",
			currency == "EGP",
			_("Company currency is the Egyptian pound")
			if currency == "EGP"
			else _("Company currency is {0}").format(currency),
		)

	# 8. documents with a different currency than the company
	foreign = _scalar(
		"select count(*) from `tabSales Invoice` where docstatus = 1 and currency != 'EGP'"
	) + _scalar("select count(*) from `tabPurchase Invoice` where docstatus = 1 and currency != 'EGP'")
	add(
		"all_egp",
		foreign == 0,
		_("All invoices are in Egyptian pounds")
		if foreign == 0
		else _("{0} invoices are not in EGP").format(int(foreign)),
	)
	return results


@frappe.whitelist()
def run():
	frappe.only_for(["System Manager", "Accounts Manager", "Shop Owner"])
	results = checks()
	return {
		"ok": all(r["ok"] for r in results),
		"passed": sum(r["ok"] for r in results),
		"total": len(results),
		"checks": results,
	}
