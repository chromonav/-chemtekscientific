import frappe

def validate_supplier_delivery_note(doc, method=None):
    if doc.supplier_delivery_note and doc.supplier and doc.docstatus != 2 and not doc.amended_from:      
        data = frappe.get_value("Purchase Receipt", {'supplier_delivery_note' : doc.supplier_delivery_note, 'supplier' : doc.supplier}, ['name'])
        if data:    
            frappe.throw('Supplier sales invoice number already exits')