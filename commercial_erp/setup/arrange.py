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

SIDEBAR_MODULES = ["Selling", "Buying", "Stock", "Accounts", "Setup"]

ARRANGE_VERSION = "4"  # bump to re-apply the site-level navigation layers on existing sites


def apply():
	remove_onboarding()
	clean_navbar()
	ensure_shop_workspace()  # the dock pins it, so it must exist first
	from commercial_erp.setup import guide

	guide.ensure()
	if frappe.db.get_default("ce_arrange_version") != ARRANGE_VERSION:
		_reset_layers()
		frappe.db.set_default("ce_arrange_version", ARRANGE_VERSION)
	arrange_dock()
	for module in SIDEBAR_MODULES:
		arrange_sidebar(module)
	set_default_workspace()


def _reset_layers():
	"""Drop the site layers this app created earlier (never user-level layers)."""
	for name in frappe.get_all("Dock", filters={"app": APP, "user": "", "standard": 0}, pluck="name"):
		frappe.delete_doc("Dock", name, force=1, ignore_permissions=True)
	for name in frappe.get_all(
		"Custom Sidebar", filters={"user": "", "module": ["in", list(SIDEBAR_MODULES)]}, pluck="name"
	):
		frappe.delete_doc("Custom Sidebar", name, force=1, ignore_permissions=True)
	frappe.clear_cache()


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
	"""Replace the module's sidebar by our own sections (upstream rows stay, hidden)."""
	if get_customization(module, None):
		return
	from commercial_erp.setup.navigation import SIDEBARS, build_rows

	if module not in SIDEBARS:
		return
	hidden_base = [{**dict(r), "hidden": 1, "added": 0} for r in get_site_sidebar_layer(module)]
	save_site_sidebar(module, build_rows(module) + hidden_base)


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
	if user:
		frappe.db.sql(
			"update `tabUser` set default_workspace = %s where name = %s and ifnull(default_workspace, '') = ''",
			(SHOP_WORKSPACE, user),
		)
	else:
		frappe.db.sql(
			"update `tabUser` set default_workspace = %s where name not in ('Guest') and ifnull(default_workspace, '') = ''",
			(SHOP_WORKSPACE,),
		)


def on_user_created(doc, method=None):
	set_default_workspace(doc.name)
