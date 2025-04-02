// Copyright (c) 2025, abc and contributors
// For license information, please see license.txt

// frappe.query_reports["Data Tracker"] = {
// 	"filters": [

// 	]
// };



frappe.query_reports["Data Tracker"] = {
    "filters": [
        {
            "fieldname": "start_date",
            "label": __("Start Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_days(frappe.datetime.get_today(), -30)
        },
        {
            "fieldname": "end_date",
            "label": __("End Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today()
        },
    ]
};