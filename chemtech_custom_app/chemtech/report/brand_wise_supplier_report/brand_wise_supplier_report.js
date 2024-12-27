// Copyright (c) 2024, abc and contributors
// For license information, please see license.txt
// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt


frappe.query_reports["Brand-wise Supplier Report"] = {
	"filters": [
		{
			"fieldname": "brand",
			"label": __("Brand"),
			"fieldtype": "MultiSelectList",
			"options": "Brand",
			"get_data": function (txt) {
				return frappe.db.get_link_options("Brand", txt);
			}
		}
	]
};
