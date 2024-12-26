
frappe.ui.form.on('Purchase Invoice', {
    refresh: function(frm) {
        $.each(frm.doc.items, function(index, item) {
            let exists = frm.doc.custom_additional_duties_and_charges.some(function(row) {
                return row.item === item.item_name;
            });

            if (!exists) {
                let row = frm.add_child("custom_additional_duties_and_charges");
                row.item = item.item_name;  
                row.duty_charges = 0;  
                row.freight_charges = 0;  
                row.other_charges = 0;  
            }
        });

        frm.refresh_field("custom_additional_duties_and_charges");
    }
});
