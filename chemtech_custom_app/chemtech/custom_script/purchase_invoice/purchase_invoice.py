import frappe

def validate_bill_no(doc, method=None):    
    if doc.bill_no and doc.supplier and doc.docstatus != 2 and not doc.amended_from:
        data = frappe.get_value("Purchase Invoice", {'bill_no' : doc.bill_no, 'supplier' : doc.supplier}, ['name'])
        if data:    
            frappe.throw('Supplier invoice number already exits')
