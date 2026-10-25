frappe.ui.form.on("Demo Link", {
	refresh(frm) {
		if (frm.doc.__islocal || frm.doc.status !== "Active") return;
		frm.add_custom_button(__("Copy Link"), () => frappe.utils.copy_to_clipboard(frm.doc.login_link));
		frm.add_custom_button(__("Revoke Now"), () => {
			frappe.confirm(__("Stop this demo link now?"), () => {
				frappe.call({
					method: "commercial_erp.commercial_erp.doctype.demo_link.demo_link.revoke",
					args: { name: frm.doc.name },
					callback: () => frm.reload_doc(),
				});
			});
		});
	},
});
