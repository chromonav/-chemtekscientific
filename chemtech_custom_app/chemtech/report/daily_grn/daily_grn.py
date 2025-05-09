import frappe
from frappe.utils import getdate, today

def execute(filters=None):
    if not filters:
        filters = {}

    from_date = getdate(filters.get("from_date", today()))
    to_date = getdate(filters.get("to_date", today()))

    columns = get_columns()
    data = []

    # Fetch GRN items (Purchase Receipts)
    grn_items = frappe.db.sql("""
        SELECT
            pri.item_code,
            pri.qty AS grn_qty,
            pr.posting_date,
            pri.warehouse,
            pr.name AS purchase_receipt
        FROM
            `tabPurchase Receipt Item` pri
        JOIN
            `tabPurchase Receipt` pr ON pri.parent = pr.name
        WHERE
            pr.docstatus = 1
            AND pr.posting_date BETWEEN %s AND %s
    """, (from_date, to_date), as_dict=1)

    # Group GRNs by item and warehouse
    grn_map = {}
    for row in grn_items:
        key = (row.item_code, row.warehouse)
        grn_map.setdefault(key, []).append(row)

    # Fetch pending Sales Orders (Regular only)
    sales_orders = frappe.db.sql("""
        SELECT
            soi.parent AS sales_order,
            so.transaction_date,
            so.customer,
            soi.item_code,
            soi.qty,
            soi.delivered_qty,
            soi.warehouse,
            soi.name AS so_item
        FROM
            `tabSales Order Item` soi
        JOIN
            `tabSales Order` so ON soi.parent = so.name
        WHERE
            so.docstatus = 1
            AND so.status NOT IN ('Completed', 'Closed')
            AND soi.qty > soi.delivered_qty
            AND IFNULL(so.order_category__, '') = 'Regular'
    """, as_dict=1)

    for so in sales_orders:
        pending_qty = so.qty - so.delivered_qty
        grn_qty_today = 0
        grn_list = grn_map.get((so.item_code, so.warehouse), [])

        for grn in grn_list:
            grn_qty_today += grn.grn_qty

        data.append({
            "sales_order": so.sales_order,
            "customer": so.customer,
            "item_code": so.item_code,
            "ordered_qty": so.qty,
            "delivered_qty": so.delivered_qty,
            "pending_qty": pending_qty,
            "grn_qty_today": grn_qty_today,
            "warehouse": so.warehouse,
            # "can_bill_from": getdate(grn.posting_date).strftime('%Y-%m-%d') if grn_list else '',
            "action": "Close Manually" if pending_qty > 0 else ""
        })

    return columns, data


def get_columns():
    return [
        {"label": "Sales Order", "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 140},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Ordered Qty", "fieldname": "ordered_qty", "fieldtype": "Float", "width": 100},
        {"label": "Delivered Qty", "fieldname": "delivered_qty", "fieldtype": "Float", "width": 100},
        {"label": "Pending Qty", "fieldname": "pending_qty", "fieldtype": "Float", "width": 100},
        {"label": "GRN Qty (Today)", "fieldname": "grn_qty_today", "fieldtype": "Float", "width": 110},
        {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 120},
        # {"label": "Can Bill From", "fieldname": "can_bill_from", "fieldtype": "Date", "width": 100},
        # {"label": "Action", "fieldname": "action", "fieldtype": "Data", "width": 120},
    ]
