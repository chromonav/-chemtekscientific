const PRICEBOOK_SYNC_DONE_EVENT = "pricebook_sync_done";

// The sync runs in a background job and reports back over realtime. Register
// one listener for the whole desk session, not one per form refresh.
let pricebook_sync_listener_registered = false;

function register_pricebook_sync_listener() {
	if (pricebook_sync_listener_registered) return;
	pricebook_sync_listener_registered = true;

	frappe.realtime.on(PRICEBOOK_SYNC_DONE_EVENT, (data) => {
		if (data.success) {
			frappe.show_alert(
				{
					message:
						data.message ||
						__("{0}: {1} Item Price(s) synced to Salesforce", [
							data.price_list,
							data.synced,
						]),
					indicator: "green",
				},
				10
			);
		} else {
			frappe.msgprint({
				title: __("Salesforce sync failed for {0}", [data.price_list]),
				message: data.error || __("See the Error Log for details."),
				indicator: "red",
			});
		}
	});
}

frappe.ui.form.on("Price List", {
	refresh(frm) {
		register_pricebook_sync_listener();

		// Only selling Price Lists are synced to Salesforce.
		if (frm.is_new() || !frm.doc.selling) return;

		frm.add_custom_button(__("Sync to Salesforce"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Sync to Salesforce"),
				fields: [
					{
						fieldname: "from_date",
						fieldtype: "Date",
						label: __("From Date"),
						reqd: 1,
						default: frappe.datetime.get_today(),
						description: __("Only Item Prices modified on or after this date are sent."),
					},
					{
						fieldname: "to_date",
						fieldtype: "Date",
						label: __("To Date"),
						reqd: 1,
						default: frappe.datetime.get_today(),
						description: __("Only Item Prices modified on or before this date are sent."),
					},
				],
				primary_action_label: __("Sync"),
				primary_action(values) {
					if (values.from_date > values.to_date) {
						frappe.msgprint({
							title: __("Invalid dates"),
							message: __("From Date cannot be after To Date."),
							indicator: "red",
						});
						return;
					}

					dialog.hide();
					frappe.call({
						method: "chemtech_custom_app.chemtech.custom_script.salesforce_pricebook_sync.sync_price_list",
						args: {
							name: frm.doc.name,
							from_date: values.from_date,
							to_date: values.to_date,
						},
						// No freeze: the request only queues the job and returns.
						callback: (r) => {
							if (r.message && r.message.queued) {
								frappe.show_alert(
									{
										message: __(
											"Salesforce sync started in the background. You will be notified when it finishes."
										),
										indicator: "blue",
									},
									7
								);
							} else {
								frappe.msgprint({
									title: __("Sync not started"),
									message:
										(r.message && r.message.error) ||
										__("See the Error Log for details."),
									indicator: "red",
								});
							}
						},
					});
				},
			});
			dialog.show();
		});
	},
});
