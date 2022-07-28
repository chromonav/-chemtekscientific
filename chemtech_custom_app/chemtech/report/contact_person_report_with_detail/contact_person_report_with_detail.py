# Copyright (c) 2022, abc and contributors
# For license information, please see license.txt
import frappe
from frappe import _

def execute(filters=None):
	if not filters:
		return [], [], None, []

	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data, None

def get_data(filters):
	print("**",filters)
	data = frappe.db.sql("""SELECT co.name as acc_name,co.address as location,co.status as contact_status,co.designation as designation,
		co.department as department,co.mobile_no as mobile_no,co.phone as phone,co.email_id as email_id,cu.sales_person as sales_person_name,
		co.area_of_interest_1 as area_of_interest_1,co.area_of_interest_2 as area_of_interest_2,co.hplc as hplc,
		co.uplc as uplc,co.gchs as gchs,co.gcms as gcms,
		co.lcms as lcms,co.icp_ as icp,	co.kfr as kfr,co.ic as ic,co.ph_ as ph,co.icpms as icpms,co.ftir_ as ftir,
		co.dissolution as dissolution,co.malvern as malvern
		FROM `tabContact` co, `tabCustomer` cu
	 	WHERE co.company_name=cu.customer_name""".format(filters.get('customer_name'), filters.get('status')),as_dict=1,debug=1)
	print("IIIIIIIIIIIIIIIIIIIIIIIIIII", data)
	return data

def get_columns(filters):
	columns = [
		{
            "label": _("Sales Person"),
            "fieldname": "sales_person_name",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Account Name"),
            "fieldname": "acc_name",
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
            "label": _("Status"),
            "fieldname": "contact_status",
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
            "label": _("Department"),
            "fieldname": "department",
            "fieldtype": "Data",
            "width": 80,
        },	
        {
            "label": _("Mobile no."),
            "fieldname": "mobile_no",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Landline no."),
            "fieldname": "phone",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Email Id"),
            "fieldname": "email_id",
            "fieldtype": "Data",
            "width": 80,
        },	
        {
            "label": _("Area of Interest 1"),
            "fieldname": "area_of_interest_1",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Area of Interest 2"),
            "fieldname": "area_of_interest_2",
            "fieldtype": "Data",
            "width": 80,
        },	
        {
            "label": _("HPLC"),
            "fieldname": "hplc",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("UPLC"),
            "fieldname": "uplc",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("GCHS"),
            "fieldname": "gchs",
            "fieldtype": "Data",
            "width": 80,
        },	
        {
            "label": _("GCMS/FID"),
            "fieldname": "gcms",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("LCMS"),
            "fieldname": "lcms",
            "fieldtype": "Data",
            "width": 80,
        },	
        {
            "label": _("ICP"),
            "fieldname": "icp",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("KFR"),
            "fieldname": "kfr",
            "fieldtype": "Data",
            "width": 80,
        },	
        {
            "label": _("IC"),
            "fieldname": "ic",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("PH"),
            "fieldname": "ph",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("ICP-MS"),
            "fieldname": "icpms",
            "fieldtype": "Data",
            "width": 80,
        },	
        {
            "label": _("FTIR"),
            "fieldname": "ftir",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Dissolution"),
            "fieldname": "dissolution",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Malvern"),
            "fieldname": "malvern",
            "fieldtype": "Data",
            "width": 80,
        },	
	]
	return columns
