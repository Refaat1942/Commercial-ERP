app_name = "commercial_erp"
app_title = "FES"
app_publisher = "Commercial ERP"
app_description = "Arabic-first commercial ERP configuration for small Egyptian shops and warehouses"
app_email = "admin@example.com"
app_license = "GPL-3.0-or-later"

required_apps = ["erpnext"]

app_logo_url = "/assets/commercial_erp/images/logo.svg"
app_include_css = "/assets/commercial_erp/css/commercial_erp.css"
app_include_js = "/assets/commercial_erp/js/commercial_erp.js"
web_include_css = "/assets/commercial_erp/css/commercial_erp.css"
web_include_js = "/assets/commercial_erp/js/login.js"

after_install = "commercial_erp.setup.install.after_install"

# Adds Egypt-specific accounts and (zero-rate, to-be-configured) tax templates
# after ERPNext has created a company's chart of accounts.
doc_events = {
	"Company": {
		"on_update": "commercial_erp.setup.company.on_company_update",
	},
	"User": {
		"after_insert": "commercial_erp.setup.arrange.on_user_created",
	},
}

after_migrate = "commercial_erp.setup.update.after_migrate"
