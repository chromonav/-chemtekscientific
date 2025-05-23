# # Copyright (c) 2025, abc and contributors
# # For license information, please see license.txt

import frappe
def execute(filters=None):
    columns = get_columns()
    data = []

    cogs_records = frappe.get_all("COGS", fields=["name", "item_code", "total"])

    for cogs in cogs_records:
        # Add main item row (parent)
        data.append({
            "indent": 0,
            "item_code": cogs.item_code,
            "qty": "",
            "uom": "",
            "rate": "",
            "amount": "",
            "total": cogs.total,
            "is_group": 1
        })

        # Fetch child table rows
        raw_materials = frappe.get_all(
            "COGS CT",
            filters={"parent": cogs.name, "parenttype": "COGS"},
            fields=["item_code", "qty", "uom", "rate", "amount"]
        )

        for raw in raw_materials:
            data.append({
                "indent": 1,
                "item_code": raw.item_code,
                "qty": raw.qty,
                "uom": raw.uom,
                "rate": raw.rate,
                "amount": raw.amount,
                "total": ""
            })

    return columns, data


def get_columns():
    return [
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 200},
        {"label": "Qty", "fieldname": "qty", "fieldtype": "Float", "width": 80},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
        {"label": "Rate", "fieldname": "rate", "fieldtype": "Currency", "width": 100},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 100},
        {"label": "Total Cost", "fieldname": "total", "fieldtype": "Currency", "width": 100},
    ]
