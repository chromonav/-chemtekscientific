import frappe

def validate_bill_no(doc, method=None):            
    if doc.bill_no and doc.supplier and doc.docstatus != 2 and not doc.amended_from:
        pi_data = frappe.db.get_value("Purchase Invoice", {'bill_no' : doc.bill_no, 'supplier' : doc.supplier}, ['name','docstatus','naming_series'], as_dict = 1)
        if pi_data and pi_data.naming_series != doc.naming_series:
            pass
        elif pi_data and pi_data.docstatus != 2:    
            frappe.throw('Supplier invoice number already exits')
