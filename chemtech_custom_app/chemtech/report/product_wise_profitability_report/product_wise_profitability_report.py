# Copyright (c) 2022, abc and contributors
# For license information, please see license.txt

import copy
from collections import OrderedDict

import frappe
from frappe import _, qb
from frappe.query_builder import CustomFunction
from frappe.query_builder.functions import Max
from frappe.utils import date_diff, flt, getdate
import re



def execute(filters=None):
    if not filters:
        return [], [], None, []

    validate_filters(filters)

    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data, None

def validate_filters(filters):
    from_date, to_date = filters.get("from_date"), filters.get("to_date")

    if not from_date and to_date:
        frappe.throw(_("From and To Dates are required."))
    elif date_diff(to_date, from_date) < 0:
        frappe.throw(_("To Date cannot be before From Date."))



def get_data(filters):
    data = frappe.db.sql(""" SELECT DISTINCT si.posting_date as si_posting_date,MONTHNAME(si.posting_date) as posting_date_month,si.company,si.name as sales_invoice_name,si.customer_name,
    ad.city as location,sii.item_code as item_code,sii.brand as si_brand,sii.lot_number as lot_no,sii.item_name,
    sii.rate as si_rate,sii.item_tax_template as sii_item_tax_template,sii.qty as si_qty,sii.lot_number as lot_no,
    sii.taxable_value as si_taxable_value,si.total_taxes_and_charges as si_gst_tax_amount,sii.batch_no as si_batch_no
    FROM `tabSales Invoice` si JOIN `tabSales Invoice Item` sii on sii.parent = si.name
    JOIN `tabAddress` ad ON si.customer_address = ad.name WHERE posting_date BETWEEN '{0}' and '{1}' and si.company='{2}' and si.status not in ('Rerurn','Cancelled')"""
    .format(filters.get('from_date'), filters.get('to_date'),filters.get('company')),as_dict=1,debug=1)
    item_code_list = [item.item_code for item in data]

    data1 = frappe.db.sql(""" SELECT DISTINCT
     pii.item_code,pi.name as purchase_invoice,pi.company as company,pi.posting_date,
     pii.item_name, pii.rate as pi_rate, pii.qty as pii_qty,pii.item_tax_template as pi_tax ,
     pi.total_taxes_and_charges as pi_gst_tax_amount,pi.grand_total as pi_total
     FROM `tabPurchase Invoice Item` pii
     JOIN `tabPurchase Invoice` pi  on pii.parent=pi.name 
     JOIN `tabSales Invoice` si  on pi.company=si.company 
     where  pii.item_code in {0} and pi.posting_date < si.posting_date  and pi.company= '{1}'
     and pi.status not in ('Cancelled', 'Return','Draft','Debit Note Issued')
     """.format(tuple(item_code_list),filters.get('company')),as_dict=1,debug=1)
    
     
    data2 = frappe.db.sql(""" SELECT DISTINCT 
        sri.parent as stock_voucher,sr.purpose as stock_purpose,sr.posting_date ,sri.item_code,
        sri.batch_no,sri.valuation_rate as valuation_rate,sri.qty
        FROM `tabStock Reconciliation Item`sri JOIN `tabStock Reconciliation`sr on sri.parent=sr.name  
        JOIN `tabSales Invoice` si  on sr.company=si.company
        where sri.item_code in {0} and sr.company= '{1}' and sr.posting_date < si.posting_date """.format(tuple(item_code_list),filters.get('company')),as_dict=1,debug=1)
    
    data3 = frappe.db.sql(""" SELECT DISTINCT 
        pri.parent as purchase_receipt, pr.posting_date ,pr.company ,pri.item_code,
        pri.batch_no,pri.rate as purchase_rec_rate,pri.item_tax_template as pr_tax,
        pri.qty,pr.total_taxes_and_charges as pr_gst_tax_amount
        FROM `tabPurchase Receipt Item`pri
        JOIN `tabPurchase Receipt` pr on pr.name=pri.parent 
        JOIN `tabSales Invoice` si  on pr.company=si.company
        where pri.item_code in {0} and pr.company= '{1}' and pr.posting_date < si.posting_date
        """.format(tuple(item_code_list),filters.get('company')),as_dict=1,debug=1)
    
    data4= frappe.db.sql("""SELECT DISTINCT sed.basic_rate as stock_rate,
     sed.parent as manufacture,sed.parenttype ,se.stock_entry_type as stock_entry_type,se.company,sed.item_code
     FROM `tabStock Entry Detail`sed JOIN `tabStock Entry`se on se.name=sed.parent
     JOIN `tabSales Invoice` si  on se.company=si.company
     where sed.item_code in {0} and se.company= '{1}' and se.posting_date < si.posting_date
        """.format(tuple(item_code_list),filters.get('company')),as_dict=1,debug=1)
    
    si_gst_list = []
    si_test_list=[]
    si_Final_gst=[]
    for row in data:
        if (row.get('sii_item_tax_template')!=None):
            si_temp = re.findall(r'\d+', row.get('sii_item_tax_template'))
            si_res = list(map(int, si_temp))
            si_gst_list.append(si_res)
            for i in si_gst_list:
                si_test_list = [str(element) for element in i]  
                 
                si_new_integer = int(''.join(si_test_list))
                si_Final_gst.append(si_new_integer)
                for i in si_Final_gst:
                    si_qty_rate = (row.get('si_rate')*row.get('si_qty'))
                    row.update({'si_gst_tax_amount':(si_qty_rate)*flt(i/100)})
                    row.update({'si_total_value':(flt(row.get('si_taxable_value')+row.get('si_gst_tax_amount')))})


    pi_list=[]
    pi_gst_list =[]
    pi_Final_gst=[]
    for row in data:
        for row1 in data1:
            if (row1.get('pi_tax')!=None):
                pi_temp = re.findall(r'\d+', row1.get('pi_tax'))
                pi_res = list(map(int, pi_temp))
                pi_gst_list.append(pi_res)
                for i in pi_gst_list:
                    pi_list = [str(element) for element in i]  
                    pi_new_integer = int(''.join(pi_list))
                    pi_Final_gst.append(pi_new_integer)
                    # for i in pi_Final_gst:
                    #     pur_inv_qty_rate = (row1.get('pi_rate')*row.get('si_qty'))
                    #     row.update({'pi_gst_tax_amount':(pur_inv_qty_rate)*flt(i/100)})
                    

    for row in data:
        row.update({'si_total_value':(flt(row.get('si_taxable_value')+row.get('si_gst_tax_amount')))})
        
        for row1 in data1:
            if (row.get('item_code')==row1.get('item_code')and row.get('company') == row1.get('company')):
                row.update({'purchase_taxable_value':(flt(row1.get('pi_rate')*row.get('si_qty')))})
                #row.update({'pi_gst_tax_amount':row.get('pi_gst_tax_amount')})
                    
                row.update({'pi_total_value':(flt(row.get('purchase_taxable_value')+flt(row.get('pi_gst_tax_amount'))))})
                #row.update({'gross_profit':(flt(row.get('si_total_value')-row.get('pi_total_value')))})
                        
                row.update(row1)
                
        for row2 in data2:
            if row.get('purchase_invoice') == None :
                if (row.get('item_code')==row2.get('item_code')):
                    row.update({'purchase_invoice':row2.get('stock_voucher')})
                    row.update({'stock_purpose':row2.get('stock_purpose')})
                    row.update({'pi_rate':row2.get('valuation_rate')})
                    row.update({'purchase_taxable_value':(flt(row.get('pi_rate')*row.get('si_qty')))})                            
                    row.update({'pi_total_value':(flt(row.get('pi_rate')*row.get('si_qty')))})                        
                    row.update({'gross_profit':(flt(row.get('si_total_value')-row.get('purchase_taxable_value')))})
                      

        for row3 in data3:
            if row.get('purchase_invoice') == None and row.get('stock_voucher')==None:
                if (row.get('item_code')==row3.get('item_code')):
                    row.update({'purchase_invoice':row3.get('purchase_receipt')})
                    row.update({'pi_rate':row3.get('purchase_rec_rate')})
                    row.update({'pi_tax':row3.get('pr_tax')})
                    row.update({'purchase_taxable_value':(flt(row.get('pi_rate')*row.get('si_qty')))})
                    row.update({'pi_total_value':(flt(row.get('purchase_taxable_value')+row3.get('pr_gst_tax_amount')))})
                    row.update({'pi_gst_tax_amount':row3.get('pr_gst_tax_amount')})
                    row.update({'pi_total_value':(flt(row.get('purchase_taxable_value')+row.get('pi_gst_tax_amount')))})
                    row.update({'gross_profit':(flt(row.get('si_total_value')-row.get('pi_total_value')))})

        for row4 in data4:
            if row.get('purchase_invoice') == None and row.get('stock_voucher')==None and row.get('purchase_receipt')==None :
                if (row.get('item_code')==row4.get('item_code')):
                    row.update({'purchase_invoice':row4.get('manufacture')})
                    row.update({'stock_purpose':row4.get('stock_entry_type')})
                    row.update({'pi_rate':row4.get('stock_rate')})
                    row.update({'purchase_taxable_value':(flt(row.get('pi_rate')*row.get('si_qty')))})
                    row.update({'pi_total_value':(flt(row.get('pi_rate')*row.get('si_qty')))}) 
                    row.update({'gross_profit':(flt(row.get('si_total_value')-row.get('purchase_taxable_value')))})
           
    return data



    
    

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
            "fieldtype": "Link",
            "options":"Sales Invoice",
            "width": 80,
        },
        {
            "label": _("Sell Date"),
            "fieldname": "si_posting_date",
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
            "label": _("Purchase Invoice"),
            "fieldname": "purchase_invoice",
            "fieldtype": "Data",
            "width": 80,
        }, 
        {
            "label": _("Stock Purpose"),
            "fieldname": "stock_purpose",
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
            "label": _("Batch_NO"),
            "fieldname": "si_batch_no",
            "fieldtype": "Data",
            "width": 50,
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
        
        # {
        #     "label": _("Lot No"),
        #     "fieldname": "lot_no",
        #     "fieldtype": "Data",
        #     "width": 50,
        # },
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
            "fieldname": "purchase_taxable_value",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "convertible": "rate",
            "width": 80,
        },
         {
            "label": _("Purchase GST % "),
            "fieldname": "pi_tax",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("Purchase GST Tax Amount"),
            "fieldname": "pi_gst_tax_amount",
            "fieldtype": "Currency",
            "options": "Company:company:default_currency",
            "convertible": "rate",
            "width": 80,
        },
        
        {
            "label": _("Purchase Total Value"),
            "fieldname": "pi_total",
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