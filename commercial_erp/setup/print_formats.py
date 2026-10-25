import frappe

SALES_INVOICE_HTML = """
<div dir="rtl" style="direction: rtl; text-align: right; font-size: 13px;">
	{% if letter_head and not no_letterhead %}{{ letter_head }}{% endif %}
	<h2 style="text-align:center;">{{ _("Sales Invoice") }} {{ doc.name }}</h2>
	<table style="width:100%; margin-bottom:10px;">
		<tr>
			<td><b>{{ _("Customer") }}:</b> {{ doc.customer_name }}</td>
			<td><b>{{ _("Date") }}:</b> {{ frappe.format(doc.posting_date, {"fieldtype": "Date"}) }}</td>
		</tr>
		<tr>
			<td><b>{{ _("Company") }}:</b> {{ doc.company }}</td>
			<td><b>{{ _("Status") }}:</b> {{ _(doc.status) }}</td>
		</tr>
	</table>
	<table class="table table-bordered" style="width:100%;">
		<thead><tr>
			<th>#</th><th>{{ _("Item") }}</th><th>{{ _("Qty") }}</th><th>{{ _("UOM") }}</th>
			<th>{{ _("Rate") }}</th><th>{{ _("Amount") }}</th>
		</tr></thead>
		<tbody>
		{% for row in doc.items %}
			<tr>
				<td>{{ row.idx }}</td><td>{{ row.item_name }}</td><td>{{ row.get_formatted("qty") }}</td>
				<td>{{ row.uom }}</td><td>{{ row.get_formatted("rate", doc) }}</td>
				<td>{{ row.get_formatted("amount", doc) }}</td>
			</tr>
		{% endfor %}
		</tbody>
	</table>
	<table style="width:50%; margin-right:0; margin-left:auto;">
		<tr><td>{{ _("Net Total") }}</td><td>{{ doc.get_formatted("net_total") }}</td></tr>
		{% for tax in doc.taxes %}
		<tr><td>{{ tax.description }}</td><td>{{ tax.get_formatted("tax_amount", doc) }}</td></tr>
		{% endfor %}
		<tr><td><b>{{ _("Grand Total") }}</b></td><td><b>{{ doc.get_formatted("grand_total") }}</b></td></tr>
		<tr><td>{{ _("Outstanding Amount") }}</td><td>{{ doc.get_formatted("outstanding_amount") }}</td></tr>
	</table>
</div>
"""

FORMATS = [
	{"name": "فاتورة مبيعات - عربي", "doc_type": "Sales Invoice", "html": SALES_INVOICE_HTML},
]


def create_print_formats():
	for fmt in FORMATS:
		if frappe.db.exists("Print Format", fmt["name"]):
			# older sites: add the letter head once (a format the shop edited itself is left alone)
			if "letter_head" not in (frappe.db.get_value("Print Format", fmt["name"], "html") or ""):
				frappe.db.set_value("Print Format", fmt["name"], "html", fmt["html"])
			continue
		frappe.get_doc(
			{
				"doctype": "Print Format",
				"name": fmt["name"],
				"doc_type": fmt["doc_type"],
				"module": "Commercial ERP",
				"standard": "No",
				"custom_format": 1,
				"print_format_type": "Jinja",
				"html": fmt["html"],
				"default_print_language": "ar",
			}
		).insert(ignore_permissions=True)


SHOP_LETTER_HEAD = "ترويسة المحل"
SHOP_LETTER_HEAD_HTML = """
<div dir="rtl" style="text-align:center; border-bottom:2px solid #0B6B63; padding-bottom:8px; margin-bottom:8px;">
	{% set company = frappe.get_cached_doc("Company", doc.company) if doc.company else None %}
	{% if company and company.company_logo %}<img src="{{ company.company_logo }}" style="max-height:60px;"><br>{% endif %}
	<b style="font-size:20px;">{{ doc.company or "" }}</b>
	{% if company and (company.phone_no or company.tax_id) %}
	<div style="font-size:12px; color:#555;">
		{% if company.phone_no %}{{ _("Phone") }}: {{ company.phone_no }}{% endif %}
		{% if company.tax_id %} &nbsp; {{ _("Tax ID") }}: {{ company.tax_id }}{% endif %}
	</div>
	{% endif %}
</div>
"""
# ERPNext's English print styles; together with its template letter heads they also pop up an
# "Enter Company Details" dialog (logo, email, address ...) on every print preview until filled in
UPSTREAM_STYLES = ("Bordered", "Classic", "Modern", "Modern with Images")
UPSTREAM_DOCTYPES = (
	"Sales Order", "Sales Invoice", "Delivery Note", "Purchase Order", "Purchase Invoice", "POS Invoice",
	"Quotation", "Request for Quotation",
)  # fmt: skip
UPSTREAM_LETTER_HEADS = ("Company Letterhead", "Company Letterhead - Grey")


def simplify_printing():
	"""One clear way to print: the Arabic invoice format, a plain letter head with the shop's name,
	and no English template formats."""
	create_print_formats()
	if not frappe.db.exists("Letter Head", SHOP_LETTER_HEAD):
		frappe.get_doc(
			{
				"doctype": "Letter Head",
				"letter_head_name": SHOP_LETTER_HEAD,
				"source": "HTML",
				"content": SHOP_LETTER_HEAD_HTML,
				"is_default": 1,
			}
		).insert(ignore_permissions=True)
	for name in UPSTREAM_LETTER_HEADS:
		if frappe.db.exists("Letter Head", name):
			frappe.db.set_value("Letter Head", name, {"disabled": 1, "is_default": 0}, update_modified=False)
	if not frappe.db.get_value("Letter Head", {"is_default": 1, "disabled": 0}):
		frappe.db.set_value("Letter Head", SHOP_LETTER_HEAD, "is_default", 1, update_modified=False)
	frappe.db.set_default("letter_head", frappe.db.get_value("Letter Head", {"is_default": 1}))

	styled = [f"{dt} {style}" for dt in UPSTREAM_DOCTYPES for style in UPSTREAM_STYLES]
	for name in frappe.get_all("Print Format", filters={"name": ["in", styled], "disabled": 0}, pluck="name"):
		frappe.db.set_value("Print Format", name, "disabled", 1, update_modified=False)
	for fmt in FORMATS:
		frappe.make_property_setter(
			{
				"doctype": fmt["doc_type"],
				"doctype_or_field": "DocType",
				"property": "default_print_format",
				"value": fmt["name"],
				"property_type": "Data",
			},
			validate_fields_for_doctype=False,
		)
	for dt in UPSTREAM_DOCTYPES:
		if dt in {f["doc_type"] for f in FORMATS}:
			continue
		# their ERPNext default was one of the styles just retired; fall back to the standard format
		frappe.db.delete(
			"Property Setter",
			{"doc_type": dt, "property": "default_print_format", "value": ["in", styled]},
		)
	frappe.clear_cache()
