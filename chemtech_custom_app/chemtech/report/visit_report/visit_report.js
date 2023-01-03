// Copyright (c) 2022, abc and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Visit Report"] = {
	"filters": [

		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"width": "100",
			"options": "Customer",
			"reqd": 0,
			"default": frappe.defaults.get_default("customer")
		},
		{
			"fieldname": "sales_person",
			"label": __("Sales Person"),
			"fieldtype": "Link",
			"width": "100",
			"options": "Sales Person",
			"reqd": 0,
			"default": frappe.defaults.get_default("Sales Person")
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 0,
			
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"width": "80",
			"reqd": 0,
		}

	]
};
