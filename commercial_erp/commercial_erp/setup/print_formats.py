import frappe

SALES_INVOICE_HTML = """
<div dir="rtl" style="direction: rtl; text-align: right; font-size: 13px;">
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
