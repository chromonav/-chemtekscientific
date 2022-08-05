# Copyright (c) 2022, abc and contributors
# For license information, please see license.txt
import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data, None

def get_data(filters):
    if filters:
        data = frappe.db.sql(""" SELECT DISTINCT cu.sales_person as sales_person_name,cu.customer_name as customer_name,co.address as contact_address,
            CONCAT_WS(' ' ,co.first_name,co.last_name) as contact_person,co.creation as creation_date,co.status as contact_status,co.designation as designation,co.department as department,
            co.mobile_no as mobile_no,co.phone as landline,co.email_id as email_id,
            co.area_of_interest_2 as area_of_interest_2,co.hplc as hplc,co.uplc as uplc,co.gchs as gchs,co.gcms as gcms,
            co.lcms as lcms,co.icp_ as icp,co._kfr as kfr,co.ic as ic,co.ph_ as ph,co.icpms as icpms,co.ftir_ as ftir,
            co.dissolution as dissolution,co.malvern as malvern FROM tabCustomer cu JOIN tabContact co ON cu.customer_name=co.company_name
            WHERE co.first_name='{0}' OR co.status='{1}'  """
            .format(filters.get('first_name'),filters.get('status')),as_dict=1,debug=1)

        address_list = [adrs.contact_address for adrs in data]
        
        data1 = frappe.db.sql("""SELECT name,city as ad_city,CONCAT_WS(' ' , address_line1,address_line2,city,state,gst_state_number,pincode,country)as full_address,state as ad_state FROM tabAddress""",as_dict=1,debug=1)
        add_list = []
        for i in address_list:
            if i != None:
                add_list.append(i)
        for row in data:
            for row1 in data1:
                if row.get('contact_address') == row1.get('name'):
                    row.update(row1)
        
        return data
    else:
        data =frappe.db.sql(""" SELECT DISTINCT cu.sales_person as sales_person_name,cu.customer_name as customer_name,co.address as contact_address,
            CONCAT_WS(' ' ,co.first_name,co.last_name) as contact_person,co.creation as creation_date,co.status as contact_status,co.designation as designation,co.department as department,
            co.mobile_no as mobile_no,co.phone as landline,co.email_id as email_id,
            co.area_of_interest_2 as area_of_interest_2,co.hplc as hplc,co.uplc as uplc,co.gchs as gchs,co.gcms as gcms,
            co.lcms as lcms,co.icp_ as icp,co._kfr as kfr,co.ic as ic,co.ph_ as ph,co.icpms as icpms,co.ftir_ as ftir,
            co.dissolution as dissolution,co.malvern as malvern  FROM tabCustomer cu JOIN tabContact co ON cu.customer_name=co.company_name""",as_dict=1,debug=1)
        address_list = [adrs.contact_address for adrs in data]
        
        data1 = frappe.db.sql("""SELECT name,city as ad_city,CONCAT_WS(' ' , address_line1,address_line2)as full_address,state as ad_state FROM tabAddress""",as_dict=1,debug=1)
        add_list = []
        for i in address_list:
            if i != None:
                add_list.append(i)
        
        for row in data:
            for row1 in data1:
                if row.get('contact_address') == row1.get('name'):
                    row.update(row1)
                
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
            "label": _("Customer Name"),
            "fieldname": "customer_name",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Address"),
            "fieldname": "contact_address",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Full Address"),
            "fieldname": "full_address",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("City"),
            "fieldname": "ad_city",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("State"),
            "fieldname": "ad_state",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Contact Person"),
            "fieldname": "contact_person",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Creation Date"),
            "fieldname": "creation_date",
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
            "fieldname": "landline",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Email Id"),
            "fieldname": "email_id",
            "fieldtype": "Data",
            "width": 80,
        },	
        #{
        #   "label": _("Area of Interest 1"),
        #    "fieldname": "area_of_interest_1",
        #   "fieldtype": "Data",
        #    "width": 80,
        #},
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
        }	
	]
	return columns





# def get_data(filters):
#     if filters:
#         print("++++++++++++++++++",filters)
#         data = frappe.db.sql(""" SELECT cu.sales_person as sales_person_name, cu.customer_name as customer_name,
#             co.address as full_addess,ad.city as ad_city,ad.state as ad_state,CONCAT(co.first_name,co.last_name) as contact_person,co.creation as creation_date,
#             co.status as contact_status,co.designation as designation,co.department as department,co.mobile_no as mobile_no,
#             co.phone as landline,co.email_id as email_id,co.area_of_interest_1 as area_of_interest_1,
#             co.area_of_interest_2 as area_of_interest_2,co.hplc as hplc,co.uplc as uplc,co.gchs as gchs,co.gcms as gcms,co.lcms as lcms,
#             co.icp_ as icp,co._kfr as kfr,co.ic as ic,co.ph_ as ph,co.icpms as icpms,co.ftir_ as ftir,co.dissolution as dissolution,co.malvern as malvern
#             FROM `tabCustomer` cu JOIN `tabContact`co ON cu.customer_name=co.company_name JOIN tabAddress ad ON ad.address_title=co.address
#             WHERE co.first_name ='{0}' OR co.status='{1}' """.format(filters.get('first_name'),filters.get('status'),as_dict=1,debug=1))
#         print("~~~~~~~~~~~~~~~~~~~~~~~~",data)
#         return data
#     # elif filters:
#     #     print("======= in elif",filters)
#     #     data = frappe.db.sql(""" SELECT cu.sales_person as sales_person_name, cu.customer_name as customer_name,co.address as full_addess,CONCAT(co.first_name,co.last_name) as contact_person,co.creation as creation_date,co.status as contact_status,co.designation as designation FROM `tabCustomer` cu JOIN `tabContact`co ON cu.customer_name=co.company_name WHERE cu.sales_person ='{0}' OR co.status='{1}' """.format(filters.get('sales_person'),filters.get('status'),as_dict=1,debug=1))
#     #     return data
#     else:
#         print("---------------in else")
#         data = frappe.db.sql("""SELECT cu.sales_person as sales_person_name,CONCAT(co.first_name,co.last_name) as contact_person,
#             co.company_name as customer_name,co.address as full_address,ad.city as ad_city,ad.state as ad_state,co.creation as creation_date,co.status as contact_status,
#             co.designation as designation,co.department as department,co.mobile_no as mobile_no,
#             co.phone as landline,co.email_id as email_id,co.area_of_interest_1 as area_of_interest_1,
#             co.area_of_interest_2 as area_of_interest_2,co.hplc as hplc,co.uplc as uplc,co.gchs as gchs,co.gcms as gcms,co.lcms as lcms,
#             co.icp_ as icp,co._kfr as kfr,co.ic as ic,co.ph_ as ph,co.icpms as icpms,co.ftir_ as ftir,co.dissolution as dissolution,co.malvern as malvern
#             FROM `tabContact` co JOIN `tabCustomer` cu ON co.company_name=cu.customer_name
#             JOIN tabAddress ad ON ad.address_title=co.address""",as_dict=1,debug=1)
#         return data
