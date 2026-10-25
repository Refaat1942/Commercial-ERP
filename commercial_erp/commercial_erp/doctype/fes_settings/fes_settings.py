import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class FESSettings(Document):
	def on_update(self):
		from commercial_erp.setup.arrange import apply_package

		apply_package(self.package)
		frappe.db.set_single_value("FES Settings", "applied_on", now_datetime())
