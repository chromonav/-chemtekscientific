# Copyright (c) 2022, abc and contributors
# For license information, please see license.txt

import copy
from collections import OrderedDict

import frappe
from frappe import _, qb
from frappe.query_builder import CustomFunction
from frappe.query_builder.functions import Max
from frappe.utils import date_diff, flt, getdate




def execute(filters=None):
	""" columns, data = [], []
	return columns, data """
	if not filters:
		return [], [], None, []

	validate_filters(filters)

	columns = get_columns(filters)
	#conditions = get_conditions(filters)
	data = get_data(filters)
	return columns, data, None

def validate_filters(filters):
	from_date, to_date = filters.get("from_date"), filters.get("to_date")

	if not from_date and to_date:
		frappe.throw(_("From and To Dates are required."))
	elif date_diff(to_date, from_date) < 0:
		frappe.throw(_("To Date cannot be before From Date."))




def get_data(filters):
	#print("*************	",filters)

	data = frappe.db.sql(""" SELECT si.name as sales_invoice_name,si.company,
	si.posting_date,si.customer_name,sii.item_code,sii.batch_no as batch_id,
    sii.item_name,sii.rate as si_rate,sii.qty as si_qty,pii.parent as parent,
	pii.purchase_order as purchase_order,pii.qty as pii_qty,pii.rate as pii_rate,((sii.rate)-(pii.rate)) as gross_profit 
    FROM `tabSales Invoice` si 
	JOIN `tabSales Invoice Item` sii on sii.parent = si.name 
    JOIN `tabPurchase Invoice Item` pii
    ON pii.batch_no = sii.batch_no and pii.item_code = sii.item_code 
    WHERE posting_date BETWEEN '{0}' and '{1}' and si.company = '{2}' """.format(filters.get('from_date'), filters.get('to_date'),filters.get('company')),as_dict=1,debug=1)
	
	purchase_order_name = [item.purchase_order for item in data]
	#print("))))))))))))))))", purchase_order_name)
	li =[]
	for i in purchase_order_name:
		if i!= None:
			li.append(i)
	#print("#####",li)


	data1 = frappe.db.sql("""SELECT name, company from `tabPurchase Order` where name in {0} and company = '{1}' """.format(tuple(li), filters.get('company')), as_dict = 1, debug = 1)
	print("$$$$$$$$$$$$$$$$", data1)

	for row in data:
		for row1 in data1:
			if row.get('purchase_order')==row1.get('name'):
				print("^^^^^^",row.get('purchase_order'),row1.get('name'))
				row.update(({row.get('purchase_order'):row.get('name')}))
			else:
				row.update(({row.get('purchase_order'):'None'}))
	print("%%%",data)
	return data

	
	

def get_columns(filters):
	columns = [
		{
            "label": _("Sales Invoice"),
            "fieldname": "sales_invoice_name",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 80,
        },
        {
            "label": _("Sell Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 80,
        },
        {
            "label": _("Customer Name"),
            "fieldname": "customer_name",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Data",
            "width": 80,
        },
        
        {
            "label": _("Batch_ID"),
            "fieldname": "batch_id",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Selling Rate"),
            "fieldname": "si_rate",
            "fieldtype": "Currenc",
            "options": "Company:company:default_currency",
            "convertible": "rate",
            "width": 80,
        },
        
        {
            "label": _("Sell Qt"),
            "fieldname": "si_qty",
            "fieldtype": "Data",
            "width": 50,
        },
        
        {
            "label": _("Purchase Qty"),
            "fieldname": "pii_qty",
            "fieldtype": "Data",
            "width": 50,
        },
        {
            "label": _("Purchase Rate"),
            "fieldname": "pii_rate",
            "fieldtype": "Currency",
            "width": 80,
        },
        {
            "label": _("Gross Profit"),
            "fieldname": "gross_profit",
            "fieldtype": "Currency",
            "width": 80,
        },
		{
            "label": _("Purchase Order"),
            "fieldname": "purchase_order",
            "fieldtype": "Data",
            "width": 80,
        }
		
		

	]
	return columns