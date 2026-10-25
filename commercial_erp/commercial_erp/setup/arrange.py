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

ARRANGE_VERSION = "8"  # bump to re-apply the site-level navigation layers on existing sites


def apply():
	remove_onboarding()
	clean_navbar()
	full_numbers()
	fast_reports()
	simplify_forms()
	ensure_shop_workspace()  # the dock pins it, so it must exist first
	from commercial_erp.setup import guide

	guide.ensure()
	guide.ensure_setup_guide()
	guide.ensure_health_check()
	ensure_shop_sidebar()
	if frappe.db.get_default("ce_arrange_version") != ARRANGE_VERSION:
		_reset_layers()
		frappe.db.set_default("ce_arrange_version", ARRANGE_VERSION)
	arrange_dock()
	hide_framework_dock()
	trim_global_search()
	for module in SIDEBAR_MODULES:
		arrange_sidebar(module)
	simplify_workspaces()
	set_default_workspace()
	package = (
		frappe.db.get_single_value("FES Settings", "package")
		if frappe.db.exists("DocType", "FES Settings")
		else None
	)
	if package and package != "Full Business":
		apply_package(package)  # keep the customer's package across layout updates


SHOP_SIDEBAR_NAME = "Shop"


def ensure_shop_sidebar():
	"""A sidebar of its own for the dashboard, so opening it does not switch to some module's navigation."""
	from commercial_erp.setup.navigation import SHOP_SIDEBAR, rows_for

	rows = rows_for(SHOP_SIDEBAR, "shop")
	if not frappe.db.exists("Module Def", SHOP_SIDEBAR_NAME):  # sidebars are keyed by module
		frappe.get_doc(
			{
				"doctype": "Module Def",
				"module_name": SHOP_SIDEBAR_NAME,
				"app_name": "commercial_erp",
				"custom": 1,
			}
		).insert(ignore_permissions=True)
	doc = (
		frappe.get_doc("Sidebar", SHOP_SIDEBAR_NAME)
		if frappe.db.exists("Sidebar", SHOP_SIDEBAR_NAME)
		else frappe.new_doc("Sidebar")
	)
	doc.title = SHOP_SIDEBAR_NAME
	doc.module = SHOP_SIDEBAR_NAME
	doc.app = APP
	doc.header_icon = "layout-dashboard"
	doc.set("items", [])
	for row in rows:
		doc.append("items", {k: v for k, v in row.items() if k not in ("added", "hidden")})
	doc.flags.ignore_permissions = True
	# the app is placing its own navigation on the site: Frappe allows that under its system-write flags
	previous = frappe.flags.in_patch
	frappe.flags.in_patch = True
	try:
		doc.save()
	finally:
		frappe.flags.in_patch = previous


PACKAGES = {
	# package -> modules shown in the rail (Setup and the Shop dashboard are always shown)
	"Full Business": {"Selling", "Buying", "Stock", "Accounts"},
	"Accounts and Stock": {"Stock", "Accounts"},
	"Accounts Only": {"Accounts"},
	"Stock Only": {"Stock"},
}
ALWAYS_SHOWN = {"Setup", SHOP_SIDEBAR_NAME}
OPTIONAL_MODULES = {"Selling", "Buying", "Stock", "Accounts"}


def apply_package(package):
	"""Show only the modules a customer bought. Nothing is deleted; re-saving with another package restores them."""
	from frappe.desk.doctype.dock.dock import _save_layer

	visible = PACKAGES.get(package, PACKAGES["Full Business"])
	rows = [dict(r) for r in get_site_dock(APP)]
	if not rows:
		arrange_dock()
		rows = [dict(r) for r in get_site_dock(APP)]
	for row in rows:
		if row.get("link_type") != "Sidebar":
			continue
		name = row.get("link_to")
		if name in OPTIONAL_MODULES:
			row["hidden"] = 0 if name in visible else 1
		elif name in ALWAYS_SHOWN:
			row["hidden"] = 0
	_save_layer(APP, rows, user=None, require_visible=False)
	frappe.clear_cache()


# Business-relevant documents for the Ctrl+K search (upstream also indexes leads, projects, web pages ...).
GLOBAL_SEARCH_DOCTYPES = [
	"Customer", "Supplier", "Item", "Item Group", "Sales Invoice", "Purchase Invoice", "Sales Order",
	"Purchase Order", "Quotation", "Delivery Note", "Purchase Receipt", "Payment Entry", "Journal Entry",
	"Material Request", "Stock Entry", "Stock Reconciliation", "Serial No", "Batch", "Warehouse", "Account",
	"Contact", "Address", "Letter Head",
]  # fmt: skip


def hide_framework_dock():
	"""The "Framework" app (developer tools: Build, Website, Integrations, Automation ...) is not for shop staff.
	Its entries are hidden from the rail; what a shop administrator needs lives under Setup."""
	from frappe.desk.doctype.dock.dock import _save_layer, get_app_dock

	if get_site_dock("frappe"):
		return
	rows = [{**dict(r), "hidden": 1} for r in get_app_dock("frappe")]
	if rows:
		_save_layer("frappe", rows, user=None, require_visible=False)


def trim_global_search():
	"""Limit what Ctrl+K searches to documents a shop uses."""
	if not frappe.db.exists("DocType", "Global Search Settings"):
		return
	doc = frappe.get_single("Global Search Settings")
	wanted = [d for d in GLOBAL_SEARCH_DOCTYPES if frappe.db.exists("DocType", d)]
	if [r.document_type for r in doc.allowed_in_global_search] == wanted:
		return
	doc.set("allowed_in_global_search", [{"document_type": d} for d in wanted])
	doc.flags.ignore_permissions = True
	doc.save()


def _reset_layers():
	"""Drop the site layers this app created earlier (never user-level layers)."""
	for name in frappe.get_all(
		"Dock", filters={"app": ["in", [APP, "frappe"]], "user": "", "standard": 0}, pluck="name"
	):
		frappe.delete_doc("Dock", name, force=1, ignore_permissions=True)
	for name in frappe.get_all(
		"Custom Sidebar", filters={"user": "", "module": ["in", list(SIDEBAR_MODULES)]}, pluck="name"
	):
		frappe.delete_doc("Custom Sidebar", name, force=1, ignore_permissions=True)
	frappe.clear_cache()


def full_numbers():
	"""Show real accounting numbers (64,880.00), never "64.88K"/"ك": number cards in full, charts without
	shortened axes."""
	frappe.db.sql("update `tabNumber Card` set show_full_number = 1 where ifnull(show_full_number, 0) = 0")
	for name, options in frappe.get_all("Dashboard Chart", fields=["name", "custom_options"], as_list=True):
		try:
			opts = json.loads(options) if options else {}
		except ValueError:
			opts = {}
		axis = opts.setdefault("axisOptions", {})
		if axis.get("shortenYAxisNumbers") != 0:
			axis["shortenYAxisNumbers"] = 0
			frappe.db.set_value(
				"Dashboard Chart", name, "custom_options", json.dumps(opts), update_modified=False
			)


KEEP_WORKSPACES = {
	"Selling",
	"Buying",
	"Stock",
	"Accounting",
	"Home",
	"Shop",
	"Guide",
	"Setup Guide",
	"Health Check",
}
MODULE_HOMES = ["Selling", "Buying", "Stock", "Accounting", "Home"]

# Tabs/sections of the daily forms a one-shop business never uses (hidden, not deleted: Customize Form brings them back)
HIDDEN_FORM_PARTS = {
	"Item": ["manufacturing", "quality_tab", "variants_section"],
	"Customer": ["portal_users_tab", "sales_team_tab"],
	"Supplier": ["portal_users_tab"],
	"Stock Entry": ["supplier_info_tab"],
	"Journal Entry": ["tax_withholding_tab"],
	"Purchase Order": ["drop_ship"],
}


def simplify_workspaces():
	"""Module landing pages keep their charts/number cards; the long link cards are replaced by the sidebar.
	Workspaces of modules a shop does not use are hidden."""
	for name in MODULE_HOMES:
		if not frappe.db.exists("Workspace", name):
			continue
		try:
			blocks = json.loads(frappe.db.get_value("Workspace", name, "content") or "[]")
		except ValueError:
			continue
		kept = [b for b in blocks if b.get("type") not in ("card", "onboarding", "quick_list")]
		if len(kept) != len(blocks):
			frappe.db.set_value("Workspace", name, "content", json.dumps(kept), update_modified=False)
	for name in frappe.get_all("Workspace", filters={"public": 1}, pluck="name"):
		hide = 0 if name in KEEP_WORKSPACES else 1
		if frappe.db.get_value("Workspace", name, "is_hidden") != hide:
			frappe.db.set_value("Workspace", name, "is_hidden", hide, update_modified=False)


def simplify_forms():
	for doctype, fieldnames in HIDDEN_FORM_PARTS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		for fieldname in fieldnames:
			if meta.has_field(fieldname) and not meta.get_field(fieldname).hidden:
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


def fast_reports():
	"""Upstream generates some reports in the background ("Generate New Report"), which needs workers and extra
	clicks; a one-shop database is small, so run them instantly."""
	if frappe.get_meta("Report").has_field("prepared_report"):
		frappe.db.sql("update `tabReport` set prepared_report = 0 where prepared_report = 1")


def after_migrate():
	"""Standard sync can bring back onboarding/help links; the layered arrangements persist."""
	remove_onboarding()
	clean_navbar()
	full_numbers()
	fast_reports()
	simplify_workspaces()


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
		"link_type": "Sidebar",
		"link_to": SHOP_SIDEBAR_NAME,
		"icon": "layout-dashboard",
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

	blocks = [
		{
			"id": "hdr1",
			"type": "header",
			"data": {"text": '<span class="h4">ملخص اليوم</span>', "col": 12},
		}
	]
	for i, (label, *_rest) in enumerate(NUMBER_CARDS):
		blocks.append({"id": f"nc{i}", "type": "number_card", "data": {"number_card_name": label, "col": 4}})
	blocks.append({"id": "ch1", "type": "chart", "data": {"chart_name": "Sales - Last 30 Days", "col": 12}})
	blocks.append(
		{
			"id": "hdr2",
			"type": "header",
			"data": {"text": '<span class="h4">اختصارات سريعة</span>', "col": 12},
		}
	)
	for i, (label, *_rest) in enumerate(SHORTCUTS):
		blocks.append({"id": f"sc{i}", "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
	if frappe.db.exists("Workspace", SHOP_WORKSPACE):
		if frappe.db.get_default("ce_arrange_version") != ARRANGE_VERSION:  # new layout: refresh what we own
			frappe.db.set_value(
				"Workspace", SHOP_WORKSPACE, "content", json.dumps(blocks), update_modified=False
			)
		return
	ws = frappe.get_doc(
		{
			"doctype": "Workspace",
			"name": SHOP_WORKSPACE,
			"label": SHOP_WORKSPACE,
			"title": "Shop",
			"module": SHOP_SIDEBAR_NAME,
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
