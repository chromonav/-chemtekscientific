import frappe
from frappe.utils import getdate, add_years, nowdate

def validate_delivery_note(doc, method):
    today = getdate(nowdate())
    one_year_from_today = add_years(today, 1)

    for item in doc.items:
        if item.batch_no:
            expiry_date = frappe.db.get_value("Batch", item.batch_no, "expiry_date")
            if expiry_date:
                expiry_date = getdate(expiry_date)
                if expiry_date <= one_year_from_today:
                    frappe.msgprint(
                        title="Batch Expiry Warning",
                        msg=f"The batch <b>{item.batch_no}</b> for item <b>{item.item_code}</b> is expiring on <b>{expiry_date.strftime('%d-%m-%Y')}</b>, which is within 1 year.",
                        indicator="orange"
                    )
