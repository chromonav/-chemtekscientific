// Copyright (c) 2022, abc and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Sales Order Anlysis For All Company"] = {
	"filters": [
		/*{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Select",
			"width": "80",

			"options": ['Chemtek Scientific Pvt. Ltd','Chemtek Scientific Pvt. Ltd Vapi','Chemtek Scientific Pvt. Ltd Bangalore',
			'Chemtek Scientific Pvt. Ltd Hyderabad','Lab-Quest International','Chemtek Scientific Company',
			'Labserve International'],
			"reqd": 0
			
		},

			"options": ['Chemtek Scientific Pvt. Ltd Mumbai','Chemtek Scientific Pvt. Ltd Vapi','Chemtek Scientific Pvt. Ltd Bangalore',
			'Chemtek Scientific Pvt. Ltd Hyderabad','Lab-Quest International','Chemtek Scientific Company',
			'LSI – Labserve International'],
			"reqd": 0
			
		},*/

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
			
		},
		{
			"fieldname": "sales_order",
			"label": __("Sales Order"),
			"fieldtype": "MultiSelectList",
			"width": "80",
			"options": "Sales Order",
			"get_data": function(txt) {
				return frappe.db.get_link_options("Sales Order", txt);
			},
			"get_query": () =>{
				return {
					filters: { "docstatus": 1 }
				}
			}
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "MultiSelectList",
			"width": "80",
			get_data: function(txt) {
				let status = ["To Bill", "To Deliver", "To Deliver and Bill", "Completed"]
				let options = []
				for (let option of status){
					options.push({
						"value": option,
						"label": __(option),
						"description": ""
					})
				}
				return options
			}
		},
		{
			"fieldname": "group_by_so",
			"label": __("Group by Sales Order"),
			"fieldtype": "Check",
			"default": 0
		}
	],

	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		let format_fields = ["delivered_qty", "billed_amount"];

		if (in_list(format_fields, column.fieldname) && data && data[column.fieldname] > 0) {
			value = "<span style='color:green;'>" + value + "</span>";
		}

		if (column.fieldname == "delay" && data && data[column.fieldname] > 0) {
			value = "<span style='color:red;'>" + value + "</span>";
		}
		return value;
	}
};
