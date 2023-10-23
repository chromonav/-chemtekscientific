import frappe

def validate_bill_no(doc, method=None):
    if doc.bill_no and doc.supplier:
        data = frappe.get_value("Purchase Invoice", {'bill_no' : doc.bill_no, 'supplier' : doc.supplier}, ['name'])
        if data:    
            frappe.throw('Supplier invoice number already exits')
            