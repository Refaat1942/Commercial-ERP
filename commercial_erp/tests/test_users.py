import frappe
from frappe.tests import IntegrationTestCase

from commercial_erp.setup import print_formats, users


class FakeLoginManager:
	def fail(self, message, user=None):
		raise frappe.AuthenticationError(message)


class TestUserNameLogin(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		users.configure()
		self.username = "Shop" + frappe.generate_hash(length=6)
		self.user = frappe.get_doc(
			{"doctype": "User", "first_name": "Cashier", "username": self.username, "send_welcome_email": 1}
		)
		self.user.append("roles", {"role": "Sales User"})
		self.user.insert(ignore_permissions=True)

	def tearDown(self):
		frappe.form_dict.pop("usr", None)

	def test_user_without_email_gets_an_internal_one_and_no_welcome_mail(self):
		self.assertTrue(users.is_internal(self.user.name))
		self.assertEqual(self.user.username, self.username)
		self.assertEqual(self.user.send_welcome_email, 0)
		self.assertTrue(frappe.get_system_settings("allow_login_using_user_name"))

	def test_login_name_is_case_sensitive(self):
		frappe.form_dict.usr = self.username
		users.before_login(FakeLoginManager())  # exact case passes
		for wrong in (self.username.lower(), self.username.upper()):
			frappe.form_dict.usr = wrong
			self.assertRaises(frappe.AuthenticationError, users.before_login, FakeLoginManager())

	def test_duplicate_user_name_is_refused(self):
		dup = frappe.get_doc({"doctype": "User", "first_name": "Other", "username": self.username.lower()})
		self.assertRaises(frappe.ValidationError, dup.insert, ignore_permissions=True)


class TestPrinting(IntegrationTestCase):
	def test_one_arabic_format_and_shop_letter_head(self):
		frappe.set_user("Administrator")
		print_formats.simplify_printing()
		self.assertEqual(frappe.get_meta("Sales Invoice").default_print_format, "فاتورة مبيعات - عربي")
		self.assertEqual(frappe.db.get_value("Letter Head", {"is_default": 1}), print_formats.SHOP_LETTER_HEAD)
		self.assertTrue(frappe.db.get_value("Print Format", "Sales Invoice Classic", "disabled"))
