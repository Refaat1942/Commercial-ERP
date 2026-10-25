app_name = "commercial_erp"
app_title = "FES"
app_publisher = "Fratelanza"
app_description = "Arabic-first commercial ERP configuration for small Egyptian shops and warehouses"
app_email = "admin@example.com"
app_license = "GPL-3.0-or-later"

required_apps = ["erpnext"]

app_logo_url = "/assets/commercial_erp/images/logo.svg"
app_include_css = "commercial_erp.bundle.css"
app_include_js = "commercial_erp.bundle.js"
web_include_css = "commercial_erp.bundle.css"
web_include_js = "login.bundle.js"

after_install = "commercial_erp.setup.install.after_install"

# Adds Egypt-specific accounts and (zero-rate, to-be-configured) tax templates
# after ERPNext has created a company's chart of accounts.
doc_events = {
	"Company": {
		"on_update": "commercial_erp.setup.company.on_company_update",
	},
	"User": {
		"before_insert": "commercial_erp.setup.users.before_user_insert",
		"after_insert": "commercial_erp.setup.arrange.on_user_created",
		"on_update": "commercial_erp.setup.simplify.on_user_update",
	},
}

after_migrate = "commercial_erp.setup.update.after_migrate"

scheduler_events = {"hourly": ["commercial_erp.api.expire_demo_links"]}

before_request = ["commercial_erp.api.check_demo_session"]
before_login = ["commercial_erp.setup.users.before_login"]
boot_session = "commercial_erp.api.boot_session"
