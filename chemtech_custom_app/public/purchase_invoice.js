frappe.ui.form.on('Purchase Invoice', {
    refresh: function(frm) {
        // Ensure rows in custom_additional_duties_and_charges match items
        $.each(frm.doc.items, function(index, item) {
            let exists = frm.doc.custom_additional_duties_and_charges.some(function(row) {
                return row.item_code === item.item_code;
            });

            if (!exists) {
                let row = frm.add_child("custom_additional_duties_and_charges");
                row.item_code = item.item_code;  
                row.duty_charges = 0;  
                row.freight_charges = 0;  
                row.other_charges = 0;  
            }
        });

        frm.refresh_field("custom_additional_duties_and_charges");
    },

    validate: function(frm) {
        let total_duty_charges = 0;
        let total_freight_charges = 0;
        let total_other_charges = 0;

        // Calculate totals for all rows in custom_additional_duties_and_charges
        $.each(frm.doc.custom_additional_duties_and_charges, function(index, row) {
            total_duty_charges += row.duty_charges || 0;
            total_freight_charges += row.freight_charges || 0;
            total_other_charges += row.other_charges || 0;
        });

        // Calculate the overall total from custom charges
        let custom_total_with_others_charges = total_duty_charges + total_freight_charges + total_other_charges;

        // Add the custom total to the existing total field (if required)
        let final_total = (frm.doc.total || 0) + custom_total_with_others_charges;

        // Set the calculated total in a new or existing field
        frm.set_value('custom_total_with_others_charges',final_total); // Store the additional charges total
    }
});
