frappe.ui.form.on("Batch", {
    validate: function(frm) {
        (frm.doc.custom_parameters || []).forEach(row => {
            if (row.specification && row.result) {
                const spec = parseFloat(row.specification);
                const res = parseFloat(row.result);

                if (res < spec) {
                    frappe.throw(
                        `Result should be greater than or equal to Specification (${spec}) for parameter: ${row.parameter}`
                    );
                }
            }
        });
    }
});
