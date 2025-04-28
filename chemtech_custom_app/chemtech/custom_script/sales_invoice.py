import frappe

def get_invoice_item(doc,method):
    print(f"""\n\n\n\n invoice name = {doc.name}\n\n\n""")
    print(f"""\n\n\n\n invoice item = {doc.items}\n\n\n""")

    for data in doc.items:
        print("data--",data)
        print(f"""\n\n\n\n itemcode= {data.item_code}\n\n\n""")
        pack_value = frappe.db.sql(f""" SELECT pack FROM `tabItem` WHERE item_code = '{data.item_code}' """,as_dict=True)
        print(f"""\n\n\n\n pack_value = {pack_value}\n\n\n""")
        data.pack = pack_value[0]['pack']

def before_save(doc, method):
	call = True
	for data in doc.items:
		if data.pack !=None:
			call = False
			break
	if call == True:
		get_invoice_item(doc, method)
		

import frappe
from datetime import datetime, timedelta
from frappe import _

@frappe.whitelist()
def validate_sales_invoice(doc, method):
    customer = doc.customer
    today = datetime.today().date()  # Convert to date

    # Query for all unpaid sales invoices for this customer that are past due
    sales_invoices = frappe.get_all('Sales Invoice', 
                                    filters={'customer': customer, 'docstatus': 1},  # docstatus = 1 means Open/Submitted
                                    fields=['name', 'due_date', 'outstanding_amount'])  # Fetch due_date and outstanding_amount
    
    for invoice in sales_invoices:
        due_date = invoice.get('due_date')  # Get due_date directly from Sales Invoice
        outstanding_amount = invoice.get('outstanding_amount')  # Get outstanding_amount
        
        # Calculate the gap between the due date and the current date
        if due_date:
            gap = today - due_date

            # If there's an outstanding amount and payment terms are exceeded
            if outstanding_amount > 0 and gap.days > 0:
                # Fetch the customer record to check the custom checkbox
                customer_record = frappe.get_doc('Customer', customer)
                allow_sales_invoice_creation = customer_record.custom_allow_sales_invoice_creation_on_payment_due
                
                # Check if the customer has allowed sales invoice creation even if payment terms are exceeded
                if not allow_sales_invoice_creation:
                    frappe.throw(_("Cannot create a new sales invoice as the customer has overdue payments."))
                else:
                    # Log the gap information
                    frappe.msgprint(_("The customer has overdue payments, but invoice creation is allowed due to the setting in the customer record."))


