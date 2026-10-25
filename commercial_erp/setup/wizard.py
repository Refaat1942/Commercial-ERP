"""Non-interactive replacement for the ERPNext setup wizard (for scripted installs).

    bench --site SITE execute commercial_erp.setup.wizard.run \
        --kwargs '{"company_name": "My Shop", "company_abbr": "MS"}'

Uses Frappe's own setup_complete so every native wizard step still runs.
"""

import frappe
from frappe.utils import add_days, add_months, getdate, nowdate


def run(company_name, company_abbr, full_name="Administrator", email=None, fy_start_month=1):
	if frappe.db.get_single_value("System Settings", "setup_complete"):
		return "already complete"
	today = getdate(nowdate())
	start = today.replace(month=int(fy_start_month), day=1)
	if start > today:
		start = add_months(start, -12)
	args = {
		"language": "العربية",
		"country": "Egypt",
		"timezone": "Africa/Cairo",
		"currency": "EGP",
		"full_name": full_name,
		"email": email or "admin@example.com",
		"company_name": company_name,
		"company_abbr": company_abbr,
		"chart_of_accounts": "Standard with Numbers",
		"fy_start_date": str(start),
		"fy_end_date": str(add_days(add_months(start, 12), -1)),
		"domains": ["Distribution"],
	}
	frappe.flags.in_setup_wizard = True
	frappe.local.lang = "ar"  # chart of accounts / fixtures are created in Arabic
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	setup_complete(args)

	# Frappe applies language/timezone partly through background jobs; make it deterministic.
	from commercial_erp.setup.company import disable_unverified_default_taxes
	from commercial_erp.setup.defaults import apply_system_defaults

	apply_system_defaults()
	frappe.db.set_value(
		"User", {"name": ("in", frappe.STANDARD_USERS)}, {"language": "ar", "time_zone": "Africa/Cairo"}
	)
	disable_unverified_default_taxes(company_name)
	from commercial_erp.setup import brand as brand_setup

	brand_setup.apply()
	from commercial_erp.setup import update

	update.run()
	frappe.db.commit()
	return "ok"
