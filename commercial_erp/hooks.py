app_name = "commercial_erp"
app_title = "Commercial ERP"
app_publisher = "Commercial ERP"
app_description = "Arabic-first commercial ERP configuration for small Egyptian shops and warehouses"
app_email = "admin@example.com"
app_license = "GPL-3.0-or-later"

required_apps = ["erpnext"]

after_install = "commercial_erp.setup.install.after_install"

# Adds Egypt-specific accounts and (zero-rate, to-be-configured) tax templates
# after ERPNext has created a company's chart of accounts.
doc_events = {
	"Company": {
		"on_update": "commercial_erp.setup.company.on_company_update",
	},
}
