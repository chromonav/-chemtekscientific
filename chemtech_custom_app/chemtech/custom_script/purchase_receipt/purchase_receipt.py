import frappe

def validate_supplier_delivery_note(doc, method=None):
    if doc.supplier_delivery_note and doc.supplier and doc.docstatus != 2 and not doc.amended_from:      
        pr_data = frappe.db.get_value("Purchase Receipt", {'supplier_delivery_note' : doc.supplier_delivery_note, 'supplier' : doc.supplier}, ['name', 'docstatus', 'naming_series'], as_dict = 1)
        if pr_data and pr_data.naming_series != doc.naming_series:
            pass
        elif pr_data and pr_data.docstatus != 2:    
            frappe.throw('Supplier sales invoice number already exits')
