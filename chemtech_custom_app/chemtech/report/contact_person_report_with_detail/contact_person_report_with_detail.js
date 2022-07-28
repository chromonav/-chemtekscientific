// Copyright (c) 2022, abc and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Contact Person Report With Detail"] = {
	"filters": [
		
		{
				"fieldname":"customer_name",
				"label": __("Customer Name"),
				"fieldtype": "Link",
				"options":'Customer',
				"width": "80",
				"reqd": 0,
				
		},
		{
				"fieldname":"sales_person_name",
				"label": __("Sales Person Name"),
				"fieldtype": "Link",
				"options":'Sales Person',
				"width": "80",
				"reqd": 0,
				
		},
		{
				"fieldname":"status",
				"label": __("Status"),
				"fieldtype": "Select",
				"options": "Passive\nOpen\nReplied",
				"width": "80",
				"reqd": 0,
				
		}
	]
};
