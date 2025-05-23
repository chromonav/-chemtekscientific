// Copyright (c) 2025, abc and contributors
// For license information, please see license.txt





// frappe.ui.form.on('COGS CT', {
//     item_code: function (frm, cdt, cdn) {
//         let row = locals[cdt][cdn];
//         if (!row.item_code) return;

//         frappe.call({
//             method: "frappe.client.get_value",
//             args: {
//                 doctype: "Item Price",
//                 filters: {
//                     item_code: row.item_code,
//                     price_list: "GSP"
//                 },
//                 fieldname: "price_list_rate"
//             },
//             callback: function (r) {
//                 if (r.message) {
//                     frappe.model.set_value(cdt, cdn, "rate", r.message.price_list_rate);
//                     frappe.model.set_value(cdt, cdn, "amount", r.message.price_list_rate * (row.qty || 0));
//                     update_total_amount(frm);
//                 }
//             }
//         });
//     },

//     qty: function (frm, cdt, cdn) {
//         calculate_amount_and_update_total(frm, cdt, cdn);
//     },

//     rate: function (frm, cdt, cdn) {
//         calculate_amount_and_update_total(frm, cdt, cdn);
//     },

//     amount: function (frm) {
//         update_total_amount(frm);
//     },

//     raw_materials_remove: function (frm) {
//         update_total_amount(frm);
//     }
// });

// function calculate_amount_and_update_total(frm, cdt, cdn) {
//     let row = locals[cdt][cdn];
//     let amount = (row.qty || 0) * (row.rate || 0);
//     frappe.model.set_value(cdt, cdn, "amount", amount);
//     update_total_amount(frm);
// }

// function update_total_amount(frm) {
//     let total = 0;
//     frm.doc.raw_materials.forEach(row => {
//         total += row.amount || 0;
//     });
//     frm.set_value('total', total);
// }



frappe.ui.form.on('COGS CT', {
    item_code: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.item_code) return;

        frappe.call({
            method: "chemtech_custom_app.chemtech.doctype.cogs.cogs.get_valuation_rate",
            args: {
                item_code: row.item_code
            },
            callback: function (r) {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, "rate", r.message);
                    frappe.model.set_value(cdt, cdn, "amount", r.message * (row.qty || 0));
                    update_total_amount(frm);
                }
            }
        });
    },

    qty: function (frm, cdt, cdn) {
        calculate_amount_and_update_total(frm, cdt, cdn);
    },

    rate: function (frm, cdt, cdn) {
        calculate_amount_and_update_total(frm, cdt, cdn);
    },

    amount: function (frm) {
        update_total_amount(frm);
    },

    raw_materials_remove: function (frm) {
        update_total_amount(frm);
    }
});

function calculate_amount_and_update_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let amount = (row.qty || 0) * (row.rate || 0);
    frappe.model.set_value(cdt, cdn, "amount", amount);
    update_total_amount(frm);
}

function update_total_amount(frm) {
    let total = 0;
    (frm.doc.raw_materials || []).forEach(row => {
        total += row.amount || 0;
    });
    frm.set_value('total', total);
}
