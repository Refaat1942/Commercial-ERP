import frappe

from commercial_erp.setup.defaults import (
	apply_stock_defaults,
	apply_system_defaults,
	enable_audit_trail,
)
from commercial_erp.setup.print_formats import create_print_formats
from commercial_erp.setup.roles import create_role_profiles


def create_roles_and_formats():
	create_role_profiles()
	create_print_formats()


def after_install():
	apply_system_defaults()
	apply_stock_defaults()
	enable_audit_trail()
	create_roles_and_formats()
	frappe.db.commit()
