# Copyright (c) 2022, abc and contributors
# For license information, please see license.txt

import frappe
from frappe import _, qb

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data, None

def get_data(filters):
	
	if filters :
		data = frappe.db.sql(
		    """ SELECT 
					*
				FROM 
					`tabVisit Plan` 
				WHERE 
					visit_date BETWEEN '{0}' and '{1}'
					or customer='{2}' or sales_person = '{3}'
			""".format(filters.get('from_date'), filters.get('to_date'),filters.get('customer'),filters.get('sales_person')),as_dict=1,debug=1)
		print("******",data)
		return data 
	else :
		data = frappe.db.sql(
		    """ SELECT 
					*	
				FROM 
					`tabVisit Plan` vp
				
			""",as_dict=1,debug=1)
		return data 

def get_columns(filters):
    columns = [
        {
            "label": _("Visit Date"),
            "fieldname": "visit_date",
            "fieldtype": "Date",
            "width": 80,
        },
        {
            "label": _("Visit Day"),
            "fieldname": "visit_day",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 80,
        },
        {
            "label": _("Sales Person"),
            "fieldname": "sales_person",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Address"),
            "fieldname": "address",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Location"),
            "fieldname": "location",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("State"),
            "fieldname": "state",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Visit Purpose"),
            "fieldname": "visit_purpose",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Joint Visit"),
            "fieldname": "joint_visit",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Actual Customer Visited"),
            "fieldname": "actual_customer_visited",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Person Met"),
            "fieldname": "person_met",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Designation"),
            "fieldname": "designation",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Discussed on products"),
            "fieldname": "discussed_on_products",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Comments/Discussion points/Highlights"),
            "fieldname": "commentsdiscussion_pointshighlights",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Next Step/Way Forward"),
            "fieldname": "next_stepway_forward",
            "fieldtype": "Data",
            "width": 80,
        },

    ]
    return columns