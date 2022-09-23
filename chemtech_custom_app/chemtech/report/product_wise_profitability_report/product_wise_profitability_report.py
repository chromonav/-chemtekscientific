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
    data = frappe.db.sql(""" SELECT DISTINCT si.posting_date,MONTHNAME(si.posting_date) as posting_date_month,si.company,si.name as sales_invoice_name,si.customer_name,
    ad.city as location,sii.item_code as item_code,sii.brand as si_brand,sii.item_name,sii.rate as si_rate,sii.item_tax_template as sii_item_tax_template,
    sii.qty as si_qty,sii.lot_number as lot_no,sii.taxable_value as si_taxable_value,si.total_taxes_and_charges as si_gst_tax_amount,
    (si.total_taxes_and_charges+sii.taxable_value) as si_total_value FROM `tabSales Invoice` si JOIN `tabSales Invoice Item` sii on sii.parent = si.name
    JOIN `tabAddress` ad ON si.customer_address = ad.name WHERE posting_date BETWEEN '{0}' and '{1}' and si.company='{2}' """
    .format(filters.get('from_date'), filters.get('to_date'),filters.get('company')),as_dict=1,debug=1)
    item_code_list = [item.item_code for item in data]
    
    data2 = frappe.db.sql(""" SELECT DISTINCT pii.item_code,po.name as purchase_order,po.company,po.transaction_date,pii.item_name, pii.rate as pi_rate, pii.qty as pii_qty, 
    pii.taxable_value as po_taxable_value,po.company,pii.item_tax_template as pii_item_tax_template,
    po.total_taxes_and_charges as po_gst_tax_amount,(pii.taxable_value+po.total_taxes_and_charges) as pi_total_value from `tabPurchase Invoice Item` pii 
    join `tabPurchase Order` po  on pii.purchase_order=po.name join `tabSales Invoice` si  on po.company=si.company where po.company='{1}'
     and  pii.item_code in {0} and po.transaction_date<si.posting_date """.format(tuple(item_code_list),filters.get('company')),as_dict=1)
    

    for row in data:
        for row1 in data2:
            if (row.get('item_code')==row1.get('item_code')and row.get('company') == row1.get('company')):
                row.update({'gross_profit':(flt(row.get('si_rate'))-flt(row1.get('pi_rate')))})
                row.update(row1)

    return data


# def get_data(filters):
	
#     data = frappe.db.sql(""" SELECT si.posting_date,MONTHNAME(si.posting_date) as posting_date_month,si.company,si.name as sales_invoice_name,si.customer_name,ad.city as location,sii.item_code as item_code,sii.brand as si_brand,sii.item_name,sii.rate as si_rate,
#         sii.item_tax_template as sii_item_tax_template,sii.qty as si_qty,sii.lot_number as lot_no,sii.taxable_value as si_taxable_value,
#         si.total_taxes_and_charges as si_gst_tax_amount,(si.total_taxes_and_charges+sii.taxable_value) as si_total_value 
#         FROM `tabSales Invoice` si JOIN `tabSales Invoice Item` sii on sii.parent = si.name JOIN `tabAddress` ad ON si.customer_address = 
#          ad.name WHERE posting_date BETWEEN '{0}' and '{1}' and si.company = '{2}' and si.status not in ('Return','Cancelled')GROUP BY 
#          sii.item_code ORDER BY si.posting_date""".format(filters.get('from_date'), filters.get('to_date'),filters.get('company')),as_dict=1,debug=1)
#     item_code_list = [item.item_code for item in data]
    
#     data1=frappe.db.sql("""SELECT po.transaction_date,pii.item_code as pi_item_code, pii.item_name, pii.rate as pi_rate,
#      pii.qty as pii_qty, pii.taxable_value as po_taxable_value,pii.purchase_order, po.name as po_name,po.company ,
#      pii.item_tax_template as pii_item_tax_template,po.total_taxes_and_charges as po_gst_tax_amount,(pii.taxable_value+po.total_taxes_and_charges) as pi_total_value
#      from `tabPurchase Invoice Item` pii join `tabPurchase Order` po on po.name = pii.purchase_order JOIN `tabSales Invoice` si ON po.transaction_date=si.posting_date 
#      where po.company = '{0}' and pii.item_code in {1} and po.company = '{4}' and po.transaction_date <=si.posting_date """
#      .format(filters.get('company'),tuple(item_code_list),filters.get('from_date'), filters.get('to_date'),filters.get('company')),as_dict=1,debug=1)
    
#     for row in data:
#         for row1 in data1:
#             if row.get('item_code') == row1.get('pi_item_code') and row.get('company') == row1.get('company'):
#                 row1.update({'balance_qty':(row.get('si_qty')-row1.get('pii_qty'))})
#                 row1.update({'gross_profit':(flt(row.get('si_rate'))-flt(row.get('pi_rate')))})
#                 row.update(row1)
#             elif row.get('item_code') == row1.get('pi_item_code'):
#                 row1.update({'balance_qty':(row.get('si_qty')-row1.get('pii_qty'))})
#                 row1.update({'gross_profit':(flt(row.get('si_rate'))-flt(row.get('pi_rate')))})
#                 row.update(row1)

   
#     return data

	
	

def get_columns(filters):
	columns = [
		
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 80,
        },
        {
            "label": _("Sales Invoice"),
            "fieldname": "sales_invoice_name",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Sell Date"),
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 80,
        },
        {
            "label": _("Sell Month"),
            "fieldname": "posting_date_month",
            "fieldtype": "data",
            "width": 80,
        },
        {
            "label": _("Customer Name"),
            "fieldname": "customer_name",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Customer Location"),
            "fieldname": "location",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Purchase Order"),
            "fieldname": "purchase_order",
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
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Sell Qt"),
            "fieldname": "si_qty",
            "fieldtype": "Data",
            "width": 50,
        },
        {
            "label": _("Brand"),
            "fieldname": "si_brand",
            "fieldtype": "Data",
            "width": 50,
        },
        {
            "label": _("Selling Rate"),
            "fieldname": "si_rate",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "convertible": "rate",
            "width": 80,
        },
        
        
        {
            "label": _("Sales Taxable Value"),
            "fieldname": "si_taxable_value",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "convertible": "rate",
            "width": 80,
        },
        {
            "label": _("Sales GST % "),
            "fieldname": "sii_item_tax_template",
            "fieldtype": "Data",
            "width": 80,
        },
        
         {
            "label": _("Sales GST Tax Amount"),
            "fieldname": "si_gst_tax_amount",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "convertible": "rate",
            "width": 80,
        },
        {
            "label": _("Sell Total Value"),
            "fieldname": "si_total_value",
            "fieldtype": "Currency",
            "width": 80,
        },
            
        {
            "label": _("Purchase Rate"),
            "fieldname": "pi_rate",
            "fieldtype": "Currency",
            "width": 80,
        },
        {
            "label": _("Purchase Taxable Value"),
            "fieldname": "po_taxable_value",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "convertible": "rate",
            "width": 80,
        },
         {
            "label": _("Purchase GST % "),
            "fieldname": "pii_item_tax_template",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Purchase GST Tax Amount"),
            "fieldname": "po_gst_tax_amount",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "convertible": "rate",
            "width": 80,
        },
        
        {
            "label": _("Purchase Total Value"),
            "fieldname": "pi_total_value",
            "fieldtype": "Currency",
            "width": 80,
        },
        {
            "label": _("Gross Profit"),
            "fieldname": "gross_profit",
            "fieldtype": "Currency",
            "width": 80,
        },
		
		
		

	]
	return columns
