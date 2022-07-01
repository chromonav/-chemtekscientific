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

