// Copyright (c) 2022, abc and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Contact Person Report With Detail"] = {
	"filters": [
		
		{
				"fieldname":"first_name",
				"label": __("Contact Person Name"),
				"fieldtype": "Data",
				"options":'Contact',
				"width": "80",
				"reqd": 0,
				
		},
		{
				"fieldname":"status",
				"label": __("Status"),
				"fieldtype": "Select",
				"options": ['','Passive','Open','Replied'],
				"width": "80",
				"reqd": 0,
				
		}
		/*{
				"fieldname":"sales_person",
				"label": __("Sales Person Name"),
				"fieldtype": "Link",
				"options":'Sales Person',
				"width": "80",
				"reqd": 0,
				
		},*/
		
	]
};
