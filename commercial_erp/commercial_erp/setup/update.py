"""One idempotent entry point for existing sites:

bench --site SITE execute commercial_erp.setup.update.run
"""

import frappe


def run():
	from commercial_erp.setup import arrange, brand, defaults, install, masters_egypt

	defaults.apply_system_defaults()
	defaults.apply_stock_defaults()
	defaults.enable_audit_trail()
	install.create_roles_and_formats()
	brand.apply()
	masters_egypt.apply()
	arrange.apply()
	frappe.db.commit()
	frappe.clear_cache()
	return "ok"


def after_migrate():
	from commercial_erp.setup import arrange

	arrange.after_migrate()
