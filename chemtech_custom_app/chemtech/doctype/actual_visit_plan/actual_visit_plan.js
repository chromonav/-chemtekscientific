// Copyright (c) 2022, abc and contributors
// For license information, please see license.txt

// frappe.ui.form.on('Actual Visit Plan', {
// 	// refresh: function(frm) {

// 	// }
// });

frappe.ui.form.on('Visit Plan', {
    visit_date: function(frm, cdt, cdn){
    	var d = locals[cdt][cdn];
        console.log("************",d)
        if (!d.visit_date) return;
        // put any logic here
        var a = new Date(d.visit_date);
        var weekdays=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
        // update the field
	frappe.model.set_value(cdt, cdn, 'visit_day', weekdays[a.getDay()]);
    }
});

