// Copyright (c) 2025, abc and contributors
// For license information, please see license.txt
frappe.query_reports["Demand Forecast Report"] = {
    "filters": [
        {
            fieldname: "company",
            label: "Company",
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company")
        }
    ]
}
