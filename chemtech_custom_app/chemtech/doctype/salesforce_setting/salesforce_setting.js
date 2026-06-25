// Copyright (c) 2025, abc and contributors
// For license information, please see license.txt

frappe.ui.form.on('Salesforce Setting', {
	get_access_token: function (frm) {
		frappe.call({
			method: "chemtech_custom_app.chemtech.doctype.salesforce_setting.salesforce_setting.get_access_token",
			freeze: true,
			freeze_message: __("Fetching Access Token..."),
			callback: function (r) {
				if (r.message) {
					frm.reload_doc();
					frappe.msgprint(__("Access token fetched and saved successfully."));
				}
			}
		});
	}
});
