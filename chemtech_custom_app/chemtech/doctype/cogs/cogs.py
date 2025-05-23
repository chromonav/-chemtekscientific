# Copyright (c) 2025, abc and contributors
# For license information, please see license.txt

# import frappe
import frappe
from erpnext.stock.stock_ledger import get_valuation_rate as erp_get_valuation_rate
from frappe.model.document import Document

@frappe.whitelist()
def get_valuation_rate(item_code):
    # Query latest valuation rate from Stock Ledger Entry
    rate = frappe.db.get_value(
        "Stock Ledger Entry",
        filters={"item_code": item_code},
        fieldname="valuation_rate",
        order_by="posting_date desc, posting_time desc",
    )
    return rate or 0



class COGS(Document):
	pass

