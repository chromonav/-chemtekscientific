// Copyright (c) 2022, abc and contributors
// For license information, please see license.txt

frappe.ui.form.on('Chemtek Appointment Letter', {
	onload: function (frm) {
		frm.set_query("select_terms", function() {
			return { filters: { hr: 1 } };
		});
	},


	select_terms: function (frm) {
		console.log("hi");
		erpnext.utils.get_terms(frm.doc.select_terms, frm.doc, function (r) {
			if (!r.exc) {
				frm.set_value("terms", r.message);
			}
		});
	},
	
});
