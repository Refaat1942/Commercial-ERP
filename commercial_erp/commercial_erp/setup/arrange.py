"""Simplify and re-arrange the desk for a small shop, using Frappe's own layered customisation
(site-level Dock and Custom Sidebar). Nothing in ERPNext core is edited; resetting the layers in
the UI returns the standard navigation. Idempotent."""

import json

import frappe
from frappe.desk.doctype.custom_sidebar.custom_sidebar import (
	get_customization,
	get_site_sidebar_layer,
	save_site_sidebar,
)
from frappe.desk.doctype.dock.dock import get_app_dock, get_site_dock, save_site_dock

APP = "erpnext"
SHOP_WORKSPACE = "Shop"
DOCK_ORDER = ["Selling", "Buying", "Stock", "Accounts", "Setup"]
DOCK_HIDDEN = ["Manufacturing", "Projects", "Assets", "Quality", "CRM", "Support", "Portal"]

# Per module sidebar: labels (as in the base sidebar) to hide, advanced for a one-shop business.
SIDEBAR_HIDE = {
	"Selling": {"Sales Person", "POS Invoice"},
	"Buying": {
		"Request for Quotation",
		"Supplier Quotation",
		"Supplier Quotation Comparison",
		"Supplier Scorecard",
	},
	"Stock": {
		"Pick List",
		"Landed Cost Voucher",
		"Quality Inspection",
		"Packing Slip",
		"Serial & Batch",
		"Serial No",
		"Batch No",
		"Serial and Batch Bundle",
		"Inventory Dimension",
		"Item Attribute",
		"Tools",
	},
	"Accounts": {
		"Consolidated Report",
		"Banking",
		"Bank Clearance",
		"Tax Rule",
		"Tax Withholding Category",
		"Budgeting",
		"Budget",
		"Cost Center Allocation",
		"Monthly Distribution",
		"Budget Variance",
		"Accounting Dimension",
		"Account Category",
		"Financial Report Template",
		"Chart of Cost Centers",
		"Currency Exchange",
	},
	"Setup": {
		"Organization",
		"Branch",
		"Department",
		"Designation",
		"Holiday List",
		"Authorization Rule",
		"Integrations",
		"Incoming Call Settings",
		"Voice Call Settings",
		"Call Log",
		"Telephony Call Type",
		"Communication Medium",
		"Code List",
		"Common Code",
		"Bulk Transaction Log",
		"Transaction Deletion Record",
		"Manufacturing",
		"Projects",
		"CRM",
		"Support",
		"Subscription",
		"Item Variant",
		"Delivery",
		"Appointment Booking",
		"Stock Reposting",
		"Currency Exchange",
	},
}


def apply():
	remove_onboarding()
	clean_navbar()
	arrange_dock()
	for module in SIDEBAR_HIDE:
		arrange_sidebar(module)
	ensure_shop_workspace()
	set_default_workspace()


def after_migrate():
	"""Standard sync can bring back onboarding/help links; the layered arrangements persist."""
	remove_onboarding()
	clean_navbar()


# --- upstream content that does not belong in a branded product -------------------------------


def remove_onboarding():
	for name in frappe.get_all("Workspace", pluck="name"):
		row = frappe.db.get_value("Workspace", name, ["content", "module_onboarding"], as_dict=True)
		changed = {}
		if row.module_onboarding:
			changed["module_onboarding"] = None
		try:
			blocks = json.loads(row.content or "[]")
		except ValueError:
			blocks = []
		kept = [b for b in blocks if b.get("type") != "onboarding"]
		if len(kept) != len(blocks):
			changed["content"] = json.dumps(kept)
		if changed:
			frappe.db.set_value("Workspace", name, changed, update_modified=False)
	frappe.clear_cache()


def clean_navbar():
	"""Drop the links to the framework vendor's support/about pages and the ERPNext demo-data helper."""
	if not frappe.db.exists("DocType", "Navbar Settings"):
		return
	doc = frappe.get_single("Navbar Settings")
	drop_labels = {
		"About",
		"Frappe Support",
		"Documentation",
		"User Forum",
		"Report an Issue",
		"Frappe School",
	}
	for table in ("help_dropdown", "settings_dropdown"):
		rows = doc.get(table) or []
		kept = [
			r
			for r in rows
			if r.item_label not in drop_labels
			and "frappe.io" not in (r.route or "")
			and "clear_demo" not in (r.action or "")
		]
		if len(kept) != len(rows):
			doc.set(table, kept)
	doc.save(ignore_permissions=True)


# --- dock (module rail) ------------------------------------------------------------------------


def arrange_dock():
	if get_site_dock(APP):
		return  # already arranged; leave later manual changes alone
	base = get_app_dock(APP)  # the app's own entries, the starting point of the arrangement
	by_target = {(r.get("link_type"), r.get("link_to")): r for r in base}
	rows = []
	shop = {
		"link_type": "Workspace",
		"link_to": SHOP_WORKSPACE,
		"icon": "home",
		"title": "Shop",
		"added": 1,
		"hidden": 0,
	}
	rows.append(shop)
	for name in DOCK_ORDER:
		row = by_target.get(("Sidebar", name))
		if row:
			rows.append({**row, "hidden": 0})
	for name in DOCK_HIDDEN:
		row = by_target.get(("Sidebar", name))
		if row:
			rows.append({**row, "hidden": 1})
	save_site_dock(APP, rows)


# --- sidebars ------------------------------------------------------------------------------------


def arrange_sidebar(module):
	if get_customization(module, None):
		return
	hide = SIDEBAR_HIDE[module]
	rows = [dict(r) for r in get_site_sidebar_layer(module)]
	section_hidden = False
	out = []
	for row in rows:
		is_section = row.get("type") == "Section Break"
		label = row.get("label")
		if is_section:
			section_hidden = label in hide
			row["hidden"] = 1 if section_hidden else 0
		elif label in hide or (section_hidden and row.get("child")):
			row["hidden"] = 1
		else:
			row["hidden"] = 0
			if not row.get("child"):
				section_hidden = False
		out.append(row)
	save_site_sidebar(module, out)


# --- shop home workspace ------------------------------------------------------------------------

NUMBER_CARDS = [
	# label, doctype, function, field, dynamic filter (JS evaluated by the desk), color
	(
		"Sales Today",
		"Sales Invoice",
		"Sum",
		"base_grand_total",
		[["Sales Invoice", "posting_date", "=", "frappe.datetime.get_today()"]],
		"#1E8E5A",
	),
	(
		"Sales This Month",
		"Sales Invoice",
		"Sum",
		"base_grand_total",
		[
			[
				"Sales Invoice",
				"posting_date",
				"Between",
				"[frappe.datetime.month_start(), frappe.datetime.month_end()]",
			]
		],
		"#1E8E5A",
	),
	(
		"Purchases This Month",
		"Purchase Invoice",
		"Sum",
		"base_grand_total",
		[
			[
				"Purchase Invoice",
				"posting_date",
				"Between",
				"[frappe.datetime.month_start(), frappe.datetime.month_end()]",
			]
		],
		"#D9822B",
	),
	("Customer Receivables", "Sales Invoice", "Sum", "outstanding_amount", [], "#C8962E"),
	("Supplier Payables", "Purchase Invoice", "Sum", "outstanding_amount", [], "#B5473A"),
]

SHORTCUTS = [
	("New Sales Invoice", "DocType", "Sales Invoice", "New", "Green"),
	("New Purchase Invoice", "DocType", "Purchase Invoice", "New", "Orange"),
	("Payment Receipt / Voucher", "DocType", "Payment Entry", "New", "Purple"),
	("Items", "DocType", "Item", "List", "Blue"),
	("Customers", "DocType", "Customer", "List", "Green"),
	("Suppliers", "DocType", "Supplier", "List", "Orange"),
	("Stock Balance", "Report", "Stock Balance", "", "Blue"),
	("Low Stock Items", "Report", "Stock Projected Qty", "", "Red"),
	("Customer Balances", "Report", "Accounts Receivable", "", "Yellow"),
	("Supplier Balances", "Report", "Accounts Payable", "", "Yellow"),
	("Profit and Loss", "Report", "Profit and Loss Statement", "", "Purple"),
	("Sales Register", "Report", "Sales Register", "", "Green"),
]


def ensure_shop_workspace():
	for label, dt, fn, field, dyn, color in NUMBER_CARDS:
		if frappe.db.exists("Number Card", label):
			continue
		filters = [[dt, "docstatus", "=", 1]]
		frappe.get_doc(
			{
				"doctype": "Number Card",
				"label": label,
				"type": "Document Type",
				"document_type": dt,
				"function": fn,
				"aggregate_function_based_on": field,
				"filters_json": json.dumps(filters),
				"dynamic_filters_json": json.dumps(dyn),
				"is_public": 1,
				"show_percentage_stats": 0,
				"color": color,
				"module": "Commercial ERP",
			}
		).insert(ignore_permissions=True)
	if not frappe.db.exists("Dashboard Chart", "Sales - Last 30 Days"):
		frappe.get_doc(
			{
				"doctype": "Dashboard Chart",
				"chart_name": "Sales - Last 30 Days",
				"chart_type": "Sum",
				"document_type": "Sales Invoice",
				"based_on": "posting_date",
				"value_based_on": "base_grand_total",
				"timeseries": 1,
				"time_interval": "Daily",
				"timespan": "Last Month",
				"type": "Bar",
				"filters_json": json.dumps([["Sales Invoice", "docstatus", "=", 1]]),
				"is_public": 1,
				"module": "Commercial ERP",
			}
		).insert(ignore_permissions=True)

	if frappe.db.exists("Workspace", SHOP_WORKSPACE):
		return
	blocks = [
		{
			"id": "hdr1",
			"type": "header",
			"data": {"text": '<span class="h4">ملخص اليوم / Today\'s Summary</span>', "col": 12},
		}
	]
	for i, (label, *_rest) in enumerate(NUMBER_CARDS):
		blocks.append({"id": f"nc{i}", "type": "number_card", "data": {"number_card_name": label, "col": 4}})
	blocks.append({"id": "ch1", "type": "chart", "data": {"chart_name": "Sales - Last 30 Days", "col": 12}})
	blocks.append(
		{
			"id": "hdr2",
			"type": "header",
			"data": {"text": '<span class="h4">اختصارات سريعة / Quick Shortcuts</span>', "col": 12},
		}
	)
	for i, (label, *_rest) in enumerate(SHORTCUTS):
		blocks.append({"id": f"sc{i}", "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
	ws = frappe.get_doc(
		{
			"doctype": "Workspace",
			"name": SHOP_WORKSPACE,
			"label": SHOP_WORKSPACE,
			"title": "Shop",
			"module": "Setup",
			"public": 1,
			"type": "Workspace",
			"icon": "home",
			"sequence_id": 0.5,
			"content": json.dumps(blocks),
			"number_cards": [{"number_card_name": c[0], "label": c[0]} for c in NUMBER_CARDS],
			"charts": [{"chart_name": "Sales - Last 30 Days", "label": "Sales - Last 30 Days"}],
			"shortcuts": [
				{
					"label": label,
					"type": type_,
					"link_to": link,
					"doc_view": view,
					"color": color,
				}
				for label, type_, link, view, color in SHORTCUTS
			],
		}
	)
	ws.insert(ignore_permissions=True)


def set_default_workspace(user=None):
	"""Make the shop dashboard the landing page for users who have not chosen another."""
	if not frappe.db.exists("Workspace", SHOP_WORKSPACE):
		return
	filters = {"enabled": 1, "name": ["not in", ["Guest"]], "default_workspace": ["in", ["", None]]}
	if user:
		filters["name"] = user
	for name in frappe.get_all("User", filters=filters, pluck="name"):
		frappe.db.set_value("User", name, "default_workspace", SHOP_WORKSPACE, update_modified=False)


def on_user_created(doc, method=None):
	set_default_workspace(doc.name)
