"""Role Profiles for a small shop. Built only from native ERPNext roles (least privilege, no new permissions)."""

import frappe

# profile -> native roles. Roles that do not exist on the site are skipped.
ROLE_PROFILES = {
	"Shop Owner": [
		"System Manager",
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
	],
	"Cashier": ["Sales User", "Shop Cashier"],
	"Storekeeper": ["Stock User", "Item Manager", "Purchase User"],
	"Accountant": ["Accounts Manager", "Accounts User", "Sales User", "Purchase User", "Report Manager"],
}


def create_role_profiles():
	from commercial_erp.setup.permissions import apply_cashier_permissions, create_roles

	create_roles()
	apply_cashier_permissions()
	for profile, roles in ROLE_PROFILES.items():
		if frappe.db.exists("Role Profile", profile):
			continue
		doc = frappe.new_doc("Role Profile")
		doc.role_profile = profile
		for role in roles:
			if frappe.db.exists("Role", role):
				doc.append("roles", {"role": role})
		doc.insert(ignore_permissions=True)
