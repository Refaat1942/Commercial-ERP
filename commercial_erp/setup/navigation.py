"""Declarative sidebars for a one-shop business: a few clear sections per module, all open.

Each entry: (label, link_type, link_to, icon). Labels are English source strings; the Arabic comes from
translations/_glossary_ar.csv. Every base (upstream) sidebar row is kept but hidden, so resetting the site
layer in the UI brings the standard navigation back."""

SHOP = ("Shop Dashboard", "Workspace", "Shop", "layout-dashboard")
GUIDE = ("Terms Guide", "Workspace", "Guide", "book-open")
SETUP_GUIDE = ("Customer Setup Guide", "Workspace", "Setup Guide", "list-checks")
HEALTH = ("Accounting Health Check", "Workspace", "Health Check", "shield-check")

SIDEBARS = {
	"Selling": [
		(
			"Sales Documents",
			[
				("Sales Invoice", "DocType", "Sales Invoice", "receipt"),
				("Sales Order", "DocType", "Sales Order", "clipboard-list"),
				("Quotation", "DocType", "Quotation", "file-text"),
				("Delivery Note", "DocType", "Delivery Note", "truck"),
				("POS", "Page", "point-of-sale", "store"),
			],
		),
		(
			"Customers",
			[
				("Customer", "DocType", "Customer", "users"),
				("Customer Group", "DocType", "Customer Group", "layers"),
				("Territory", "DocType", "Territory", "map-pin"),
			],
		),
		(
			"Prices & Discounts",
			[
				("Price List", "DocType", "Price List", "tag"),
				("Item Price", "DocType", "Item Price", "banknote"),
				("Pricing Rule", "DocType", "Pricing Rule", "percent"),
			],
		),
		(
			"Sales Reports",
			[
				("Sales Register", "Report", "Sales Register", "list"),
				("Sales Analytics", "Report", "Sales Analytics", "chart-line"),
				("Gross Profit", "Report", "Gross Profit", "trending-up"),
				("Customer Balances", "Report", "Accounts Receivable", "wallet"),
			],
		),
	],
	"Buying": [
		(
			"Purchase Documents",
			[
				("Purchase Invoice", "DocType", "Purchase Invoice", "receipt"),
				("Purchase Order", "DocType", "Purchase Order", "clipboard-list"),
				("Purchase Receipt", "DocType", "Purchase Receipt", "package"),
				("Material Request", "DocType", "Material Request", "file-text"),
			],
		),
		(
			"Suppliers",
			[
				("Supplier", "DocType", "Supplier", "users"),
				("Supplier Group", "DocType", "Supplier Group", "layers"),
			],
		),
		(
			"Purchase Reports",
			[
				("Purchase Register", "Report", "Purchase Register", "list"),
				("Purchase Analytics", "Report", "Purchase Analytics", "chart-line"),
				("Supplier Balances", "Report", "Accounts Payable", "wallet"),
				("Low Stock Items", "Report", "Stock Projected Qty", "triangle-alert"),
			],
		),
	],
	"Stock": [
		(
			"Items",
			[
				("Item", "DocType", "Item", "package"),
				("Item Group", "DocType", "Item Group", "layers"),
				("Unit of Measure (UOM)", "DocType", "UOM", "ruler"),
				("Brand", "DocType", "Brand", "tag"),
			],
		),
		(
			"Stock Movements",
			[
				("Stock Entry", "DocType", "Stock Entry", "arrow-left-right"),
				("Stock Reconciliation", "DocType", "Stock Reconciliation", "clipboard-check"),
				("Purchase Receipt", "DocType", "Purchase Receipt", "package"),
				("Delivery Note", "DocType", "Delivery Note", "truck"),
				("Material Request", "DocType", "Material Request", "file-text"),
			],
		),
		("Warehouses", [("Warehouse", "DocType", "Warehouse", "warehouse")]),
		(
			"Stock Reports",
			[
				("Stock Balance", "Report", "Stock Balance", "list"),
				("Stock Ledger", "Report", "Stock Ledger", "book-open"),
				("Low Stock Items", "Report", "Stock Projected Qty", "triangle-alert"),
				("Stock Ageing", "Report", "Stock Ageing", "hourglass"),
			],
		),
		("Stock Setup", [("Stock Settings", "DocType", "Stock Settings", "settings")]),
	],
	"Accounts": [
		(
			"Daily Money",
			[
				("Sales Invoice", "DocType", "Sales Invoice", "receipt"),
				("Purchase Invoice", "DocType", "Purchase Invoice", "receipt"),
				("Payment Entry", "DocType", "Payment Entry", "credit-card"),
				("Journal Entry", "DocType", "Journal Entry", "book-open"),
			],
		),
		(
			"Financial Reports",
			[
				("Profit and Loss Statement", "Report", "Profit and Loss Statement", "trending-up"),
				("Balance Sheet", "Report", "Balance Sheet", "scale"),
				("Trial Balance", "Report", "Trial Balance", "list"),
				("General Ledger", "Report", "General Ledger", "book-open"),
				("Cash Flow", "Report", "Cash Flow", "banknote"),
			],
		),
		(
			"Customer & Supplier Balances",
			[
				("Customer Balances", "Report", "Accounts Receivable", "wallet"),
				("Supplier Balances", "Report", "Accounts Payable", "wallet"),
			],
		),
		(
			"Taxes",
			[
				("Sales Tax Template", "DocType", "Sales Taxes and Charges Template", "percent"),
				("Purchase Tax Template", "DocType", "Purchase Taxes and Charges Template", "percent"),
				("Item Tax Template", "DocType", "Item Tax Template", "percent"),
			],
		),
		(
			"Accounting Setup",
			[
				("Chart of Accounts", "DocType", "Account", "list-tree"),
				("Mode of Payment", "DocType", "Mode of Payment", "credit-card"),
				("Bank Account", "DocType", "Bank Account", "landmark"),
				("Fiscal Year", "DocType", "Fiscal Year", "calendar"),
				("Cost Center", "DocType", "Cost Center", "layers"),
				("Accounts Settings", "DocType", "Accounts Settings", "settings"),
			],
		),
	],
	"Setup": [
		(
			"Company & Users",
			[
				("Company", "DocType", "Company", "building-2"),
				("Users", "DocType", "User", "users"),
				("Role Permissions", "Page", "permission-manager", "shield-check"),
				("Demo Links", "DocType", "Demo Link", "link"),
				("FES Settings", "DocType", "FES Settings", "package-check"),
			],
		),
		(
			"Printing & Email",
			[
				("Print Format", "DocType", "Print Format", "printer"),
				("Letter Head", "DocType", "Letter Head", "file-text"),
				("Print Settings", "DocType", "Print Settings", "settings"),
				("Email Account", "DocType", "Email Account", "mail"),
			],
		),
		(
			"Data",
			[
				("Data Import", "DocType", "Data Import", "upload"),
				("Rename Tool", "DocType", "Rename Tool", "pencil"),
			],
		),
		(
			"Advanced (administrator)",
			[
				("Customize Form", "DocType", "Customize Form", "sliders-horizontal"),
				("Custom Field", "DocType", "Custom Field", "plus-square"),
				("Reports List", "DocType", "Report", "list"),
				("Notification", "DocType", "Notification", "bell"),
				("Workflow", "DocType", "Workflow", "git-branch"),
				("Error Log", "DocType", "Error Log", "bug"),
				("Scheduled Job Log", "DocType", "Scheduled Job Log", "clock"),
				("Global Search Settings", "DocType", "Global Search Settings", "search"),
			],
		),
		(
			"System Settings",
			[
				("System", "DocType", "System Settings", "settings"),
				("Global Defaults", "DocType", "Global Defaults", "settings"),
				("Selling Settings", "DocType", "Selling Settings", "settings"),
				("Buying Settings", "DocType", "Buying Settings", "settings"),
				("Stock Settings", "DocType", "Stock Settings", "settings"),
				("Accounts Settings", "DocType", "Accounts Settings", "settings"),
				("POS Profile", "DocType", "POS Profile", "store"),
			],
		),
	],
}


def build_rows(module, key_prefix=None):
	"""Added rows for one module, in display order."""
	rows = []
	n = 0
	for entry in SIDEBARS[module]:
		if isinstance(entry[1], list):  # section
			label, items = entry
			n += 1
			rows.append(
				{
					"type": "Section Break",
					"label": label,
					"icon": None,
					"child": 0,
					"indent": 1,
					"collapsible": 1,
					"keep_closed": 0,
					"added": 1,
					"hidden": 0,
					"key": f"ce|{key_prefix or module}|section|{n}",
				}
			)
			for item in items:
				n += 1
				rows.append(_link(key_prefix or module, n, item, child=1))
		else:
			n += 1
			rows.append(_link(key_prefix or module, n, entry, child=0))
	return rows


def _link(module, n, item, child):
	label, link_type, link_to, icon = item
	return {
		"type": "Link",
		"label": label,
		"link_type": link_type,
		"link_to": link_to,
		"icon": icon,
		"child": child,
		"indent": 0,
		"added": 1,
		"hidden": 0,
		"key": f"ce|{module}|link|{n}",
	}


# The "Shop" shell (rail icon next to the modules): dashboard, guide, daily actions, key reports.
SHOP_SIDEBAR = [
	SHOP,
	SETUP_GUIDE,
	HEALTH,
	GUIDE,
	(
		"Daily Work",
		[
			("Sales Invoice", "DocType", "Sales Invoice", "receipt"),
			("Purchase Invoice", "DocType", "Purchase Invoice", "receipt"),
			("Payment Entry", "DocType", "Payment Entry", "credit-card"),
			("Stock Entry", "DocType", "Stock Entry", "arrow-left-right"),
		],
	),
	(
		"Quick Reports",
		[
			("Stock Balance", "Report", "Stock Balance", "list"),
			("Low Stock Items", "Report", "Stock Projected Qty", "triangle-alert"),
			("Customer Balances", "Report", "Accounts Receivable", "wallet"),
			("Supplier Balances", "Report", "Accounts Payable", "wallet"),
			("Profit and Loss Statement", "Report", "Profit and Loss Statement", "trending-up"),
		],
	),
]


def rows_for(structure, key_prefix):
	"""Added rows for any structure of links and sections (used by the custom Shop sidebar)."""
	SIDEBARS["__tmp__"] = structure
	try:
		return build_rows("__tmp__", key_prefix)
	finally:
		del SIDEBARS["__tmp__"]
