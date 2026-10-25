"""Simple mode: hide the fields and sections of the daily forms that a one-shop business never fills.

Nothing is deleted. Fields are hidden with Property Setters (the same thing "Customize Form" does), so
`restore()` brings every one of them back. Modules the shop does not use are blocked per user, so their
pages cannot be opened even by URL (System Manager can unblock a module on the user form)."""

import frappe

TAG = "commercial_erp simple mode"

HIDE = {
	"Sales Invoice": [
		"naming_series", "company_tax_id", "tax_id", "is_consolidated", "update_outstanding_for_self",
		"update_billed_amount_in_sales_order", "update_billed_amount_in_delivery_note", "is_debit_note", "apply_tds",
		"cost_center", "project", "currency", "conversion_rate", "price_list_currency", "plc_conversion_rate",
		"ignore_pricing_rule", "last_scanned_warehouse", "set_target_warehouse", "total_net_weight", "base_total",
		"base_net_total", "tax_category", "shipping_rule", "incoterm", "named_place", "base_total_taxes_and_charges",
		"use_company_roundoff_cost_center", "base_totals_section", "section_tax_withholding_entry",
		"is_cash_or_non_trade_discount", "coupon_code", "base_discount_amount", "sec_tax_breakup", "pricing_rule_details",
		"packing_list", "time_sheet_list", "section_break_104", "base_paid_amount", "base_change_amount",
		"write_off_section", "redeem_loyalty_points", "loyalty_points", "loyalty_amount", "loyalty_program",
		"dont_create_loyalty_points", "loyalty_redemption_account", "loyalty_redemption_cost_center",
		"company_address_section", "dispatch_address_name", "dispatch_address", "shipping_address_section",
		"unrealized_profit_loss_account", "commission_section", "sales_team_section", "subscription_section",
		"automation_section", "utm_analytics_section", "is_internal_customer", "represents_company",
		"inter_company_invoice_reference", "is_discounted",
	],
	"Purchase Invoice": [
		"naming_series", "update_outstanding_for_self", "update_billed_amount_in_purchase_order",
		"update_billed_amount_in_purchase_receipt", "apply_tds", "cost_center", "project", "currency", "conversion_rate",
		"use_transaction_date_exchange_rate", "price_list_currency", "plc_conversion_rate", "ignore_pricing_rule",
		"last_scanned_warehouse", "set_from_warehouse", "is_subcontracted", "rejected_warehouse", "supplier_warehouse",
		"total_net_weight", "base_total", "base_net_total", "claimed_landed_cost_amount", "tax_category", "shipping_rule",
		"incoterm", "named_place", "base_taxes_and_charges_added", "base_taxes_and_charges_deducted",
		"base_total_taxes_and_charges", "use_company_roundoff_cost_center", "base_totals_section",
		"section_tax_withholding_entry", "base_discount_amount", "sec_tax_breakup", "pricing_rule_details",
		"raw_materials_supplied", "base_paid_amount", "write_off", "company_shipping_address_section",
		"unrealized_profit_loss_account", "subscription_section", "automation_section", "sb_14",
		"is_internal_supplier", "represents_company", "inter_company_invoice_reference", "sender",
	],
	"Payment Entry": [
		"naming_series", "book_advance_payments_in_separate_party_account", "apply_tds", "tax_withholding_category",
		"party_bank_account", "paid_from_account_currency", "paid_to_account_currency", "source_exchange_rate",
		"base_paid_amount", "target_exchange_rate", "base_received_amount", "base_total_allocated_amount",
		"get_outstanding_orders", "taxes_and_charges_section", "section_break_60", "section_tax_withholding_entry",
		"project", "cost_center", "base_in_words", "letter_head", "print_heading", "payment_order", "auto_repeat_section",
	],
	"Customer": [
		"alias", "gender", "loyalty_points_tab", "internal_customer_section", "section_break_nrvh",
		"tax_withholding_group", "tax_withholding_category", "so_required", "dn_required", "account_manager",
		"default_sales_partner", "default_commission_rate", "references_section", "market_segment", "industry",
		"customer_pos_id", "supplier_numbers_section",
	],
	"Supplier": [
		"alias", "gender", "internal_supplier_section", "section_break_pgad", "tax_withholding_category",
		"tax_withholding_group", "is_transporter", "block_supplier_section", "section_break_jqla",
	],
	"Item": [
		"is_fixed_asset", "auto_create_assets", "is_grouped_asset", "asset_category", "asset_naming_series",
		"allow_alternative_item", "is_customer_provided_item", "section_break_znra", "deferred_accounting_section",
		"section_break_fxqz", "end_of_life", "warranty_period", "weight_per_unit", "weight_uom",
		"serial_nos_and_batches", "supplier_details", "foreign_trade_details", "grant_commission", "customer_details",
		"section_break_xili",
	],
}  # fmt: skip

# required fields that the form/server fill in by themselves, so hiding them is safe
AUTO_FILLED = {
	"naming_series", "currency", "conversion_rate", "price_list_currency", "plc_conversion_rate",
	"paid_from_account_currency", "paid_to_account_currency", "source_exchange_rate", "target_exchange_rate",
	"base_paid_amount", "base_received_amount", "base_net_total",
}  # fmt: skip

BLOCKED_MODULES = [
	"Assets", "CRM", "Maintenance", "Manufacturing", "Portal", "Projects", "Quality Management", "Subcontracting",
	"Support", "Telephony", "EDI", "ERPNext Integrations", "Communication", "Website",
]  # fmt: skip


def apply():
	hide_fields()
	block_modules()


def hide_fields():
	for doctype, fieldnames in HIDE.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		for fieldname in fieldnames:
			df = meta.get_field(fieldname)
			if not df or df.hidden:
				continue
			if df.reqd and fieldname not in AUTO_FILLED and not df.default:
				continue  # never hide something the user must fill in
			frappe.make_property_setter(
				{
					"doctype": doctype,
					"doctype_or_field": "DocField",
					"fieldname": fieldname,
					"property": "hidden",
					"value": "1",
					"property_type": "Check",
				},
				validate_fields_for_doctype=False,
			)
	frappe.clear_cache()


def restore():
	"""Bring back every field simple mode hid (bench --site SITE execute commercial_erp.setup.simplify.restore)."""
	for doctype, fieldnames in HIDE.items():
		frappe.db.delete(
			"Property Setter",
			{"doc_type": doctype, "field_name": ["in", fieldnames], "property": "hidden", "value": "1"},
		)
	frappe.clear_cache()
	return "restored"


def _existing_modules():
	return [m for m in BLOCKED_MODULES if frappe.db.exists("Module Def", m)]


def block_modules(user=None):
	"""Block the unused modules once per user. Done once only, so a System Manager can later unblock a
	module on the user form and it stays unblocked."""
	modules = _existing_modules()
	users = (
		[user]
		if user
		else frappe.get_all("User", filters={"user_type": "System User", "enabled": 1}, pluck="name")
	)
	for name in users:
		if name in ("Administrator", "Guest") or frappe.db.get_default("ce_modules_blocked", parent=name):
			continue
		have = set(
			frappe.get_all("Block Module", filters={"parent": name, "parenttype": "User"}, pluck="module")
		)
		for m in modules:
			if m in have:
				continue
			# direct child-row insert: no second save of the User document in the middle of its own save
			frappe.get_doc(
				{
					"doctype": "Block Module",
					"parent": name,
					"parenttype": "User",
					"parentfield": "block_modules",
					"module": m,
				}
			).db_insert()
		frappe.db.set_default("ce_modules_blocked", 1, parent=name)
		frappe.clear_cache(user=name)


def on_user_update(doc, method=None):
	if doc.user_type == "System User":
		block_modules(doc.name)
