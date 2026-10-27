frappe.listview_settings["Item"] = frappe.listview_settings["Item"] || {};

const salesforceItemBulkSyncComplete = (listview, result) => {
	if (frappe.get_route_str() !== listview.page_name) return;

	listview.clear_checked_items();
	listview.refresh();

	const failures = result.failed || [];
	if (failures.length) {
		const rows = failures
			.map((f) => `<li><b>${frappe.utils.escape_html(f.item)}</b>: ${frappe.utils.escape_html(f.error)}</li>`)
			.join("");
		const synced = result.synced
			? `<p>${__("{0} item(s) synced successfully.", [result.synced])}</p>`
			: "";
		frappe.msgprint({
			title: __("Salesforce sync: {0} item(s) failed", [failures.length]),
			message: `${synced}<ul>${rows}</ul><p>${__("Full response is in the Error Log.")}</p>`,
			indicator: "red",
		});
		return;
	}

	const message = [];
	if (result.synced) message.push(__("{0} item(s) synced to Salesforce.", [result.synced]));
	if (result.skipped) message.push(__("{0} NPD item(s) skipped.", [result.skipped]));
	frappe.show_alert({ message: message.join(" "), indicator: "green" }, 7);
};

frappe.listview_settings["Item"].onload = function (listview) {
	frappe.realtime.off("salesforce_item_bulk_sync_complete");
	frappe.realtime.on("salesforce_item_bulk_sync_complete", (result) => {
		salesforceItemBulkSyncComplete(listview, result);
	});

	listview.page.add_action_item(__("Sync to Salesforce"), () => {
		const itemNames = listview.get_checked_items(true);
		if (!itemNames.length) {
			frappe.show_alert({ message: __("Select at least one Item to sync."), indicator: "orange" });
			return;
		}

		frappe.call({
			method: "chemtech_custom_app.chemtech.custom_script.salesforce_item_sync.enqueue_bulk_item_sync",
			args: { item_names: itemNames },
			callback: (r) => {
				if (r.message && r.message.queued) {
					frappe.show_alert({
						message: __("Salesforce sync queued for {0} item(s).", [r.message.queued]),
						indicator: "blue",
					});
				}
			},
		});
	});
};
