// Copyright (c) 2022, abc and contributors
// For license information, please see license.txt

frappe.ui.form.on('Visit Plan', {
	// refresh: function(frm) {
	// 	var days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
	// 	var d = new Date(dateString);
	// 	var dayName = days[d.getDay()];
	// 	console.log("********************",dayName)
	// }
});

frappe.ui.form.on("Visit Plan", "visit_date", function(frm) {
	alert("***hi**");
   var a = new Date(frm.doc.visit_date);
   var weekdays=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
   frm.set_value("visit_day",weekdays[a.getDay()])
});

// var days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
// var d = new Date(dateString);
// var dayName = days[d.getDay()];