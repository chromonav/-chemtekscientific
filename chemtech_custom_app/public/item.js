frappe.ui.form.on("Item", {
	refresh(frm) {
		if (frm.is_new()) return;

		// Don't show the button for NPD items
		if (frm.doc.custom_product_group === "NPD") return;

		frm.add_custom_button(__("Sync to Salesforce"), () => {
			frappe.call({
				method: "chemtech_custom_app.chemtech.custom_script.salesforce_item_sync.sync_item",
				args: {
					name: frm.doc.name
				},
				freeze: true,
				freeze_message: __("Pushing to Salesforce..."),
				callback: (r) => {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __("Item synced"),
							indicator: "green"
						});
					} else {
						frappe.msgprint({
							title: __("Sync failed"),
							message: (r.message && r.message.error) || __("See the Error Log for details."),
							indicator: "red",
						});
					}
				},
			});
		});
	},
});