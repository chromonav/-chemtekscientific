frappe.ui.form.on('Delivery Note Item', {
    batch_no: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.batch_no) {
            frappe.db.get_doc('Batch', row.batch_no).then(batch => {
                if (batch.expiry_date && frappe.datetime.get_diff(batch.expiry_date, frappe.datetime.nowdate()) < 0) {
                    frappe.msgprint(`Batch ${row.batch_no} for item ${row.item_code} has expired on ${batch.expiry_date}`);
                }
            });
        }
    }
});
