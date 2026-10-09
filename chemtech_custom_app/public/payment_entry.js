frappe.ui.form.on("Payment Entry", {
	refresh(frm) {
		// Pay -> Supplier gets a Receive in the supplier's company; Receive -> Customer
		// gets a Pay in the customer's company. Anything else has no mirror.
		const mirror_type = {
			"Pay|Supplier": "Receive",
			"Receive|Customer": "Pay",
		}[`${frm.doc.payment_type}|${frm.doc.party_type}`];

		if (frm.doc.docstatus !== 1 || !mirror_type || frm.doc.custom_inter_company_payment_entry) {
			return;
		}

		const party_field = frm.doc.party_type === "Supplier" ? "is_internal_supplier" : "is_internal_customer";
		frappe.db.get_value(frm.doc.party_type, frm.doc.party, party_field).then((r) => {
			if (!r.message || !r.message[party_field]) return;

			frm.add_custom_button(
				__("Inter Company Payment Entry"),
				() => {
					frappe.call({
						method: "chemtech_custom_app.chemtech.custom_script.inter_company.make_inter_company_payment_entry",
						args: { source_name: frm.doc.name },
						freeze: true,
						freeze_message: __("Creating draft {0} Payment Entry...", [__(mirror_type)]),
						callback: (r) => {
							if (r.message) frappe.set_route("Form", "Payment Entry", r.message);
						},
					});
				},
				__("Create")
			);
		});
	},
});
