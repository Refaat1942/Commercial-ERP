"""Least-privilege role for the cashier/salesperson.

ERPNext only lets 'Accounts User' create Sales Invoices / Payment Entries, which would also expose
journal entries and the ledger. 'Shop Cashier' gets Custom DocPerms limited to selling + taking
payment: no cancel, no delete, no amend, no accounting masters, no journal entries.
"""

import frappe
from frappe.permissions import add_permission, update_permission_property

CASHIER_ROLE = "Shop Cashier"

CASHIER_PERMISSIONS = {
	"Sales Invoice": ["read", "write", "create", "submit", "print", "email"],
	"Payment Entry": ["read", "write", "create", "submit", "print"],
}


def create_roles():
	if not frappe.db.exists("Role", CASHIER_ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": CASHIER_ROLE, "desk_access": 1}).insert(
			ignore_permissions=True
		)


def apply_cashier_permissions():
	for doctype, ptypes in CASHIER_PERMISSIONS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		add_permission(doctype, CASHIER_ROLE, 0)
		for ptype in ptypes:
			update_permission_property(doctype, CASHIER_ROLE, 0, ptype, 1)
