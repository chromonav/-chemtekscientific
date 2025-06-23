import frappe
from frappe.utils import add_months, nowdate

@frappe.whitelist()
def get_all_item_data(item_codes):
    item_codes = frappe.parse_json(item_codes)
    today = nowdate()
    two_months_ago = add_months(today, -2)

    def get_stock_from_warehouses(item_code, keyword):
        warehouses = frappe.db.sql_list("""
            SELECT name FROM `tabWarehouse`
            WHERE name LIKE %s AND is_group = 0
        """, (f"%{keyword}%",))
        if not warehouses:
            return 0
        return frappe.db.sql("""SELECT SUM(actual_qty) FROM `tabBin`
            WHERE item_code = %s AND warehouse IN %s""",
            (item_code, tuple(warehouses))
        )[0][0] or 0

    def get_ordered_and_delivered_qty(item_code, company_name):
        result = frappe.db.sql("""SELECT SUM(soi.qty), SUM(soi.delivered_qty)
            FROM `tabSales Order Item` soi
            JOIN `tabSales Order` so ON soi.parent = so.name
            WHERE soi.item_code = %s AND so.company = %s
            AND so.docstatus = 1
            AND so.status NOT IN ('Stopped', 'On Hold', 'Completed', 'Closed', 'Cancelled')""",
            (item_code, company_name)
        )[0]
        ordered_qty = result[0] or 0
        delivered_qty = result[1] or 0
        return ordered_qty, delivered_qty, ordered_qty - delivered_qty

    def get_avg_sales(item_code, keyword):
        return frappe.db.sql("""SELECT SUM(sii.qty)/2
            FROM `tabSales Invoice Item` sii
            JOIN `tabSales Invoice` si ON sii.parent = si.name
            WHERE sii.item_code = %s AND si.company LIKE %s
            AND si.docstatus = 1 AND si.posting_date >= %s""",
            (item_code, f"%{keyword}%", two_months_ago)
        )[0][0] or 0

    all_data = []

    for item_code in item_codes:
        try:
            item = frappe.get_doc("Item", item_code)

            stock_mum = get_stock_from_warehouses(item_code, "CSPL")
            stock_vapi = get_stock_from_warehouses(item_code, "CSPL-VAPI")
            stock_blr = get_stock_from_warehouses(item_code, "CSPLB")
            stock_hyd = get_stock_from_warehouses(item_code, "CSPLH")
            total_stock = stock_mum + stock_vapi + stock_blr + stock_hyd

            ordered_mum, delivered_mum, open_mum = get_ordered_and_delivered_qty(item_code, "Chemtek Scientific Private Limited")
            ordered_vapi, delivered_vapi, open_vapi = get_ordered_and_delivered_qty(item_code, "Chemtek Scientific Private Limited- Vapi")
            ordered_blr, delivered_blr, open_blr = get_ordered_and_delivered_qty(item_code, "Chemtek Scientific Private Limited-Bangalore")
            ordered_hyd, delivered_hyd, open_hyd = get_ordered_and_delivered_qty(item_code, "Chemtek Scientific Private Limited-Hyd")

            total_ordered = ordered_mum + ordered_vapi + ordered_blr + ordered_hyd
            total_delivered = delivered_mum + delivered_vapi + delivered_blr + delivered_hyd
            total_open_orders = total_ordered - total_delivered

            avg_mum = get_avg_sales(item_code, "Chemtek Scientific Private Limited")
            avg_vapi = get_avg_sales(item_code, "Chemtek Scientific Private Limited- Vapi")
            avg_blr = get_avg_sales(item_code, "Chemtek Scientific Private Limited-Bangalore")
            avg_hyd = get_avg_sales(item_code, "Chemtek Scientific Private Limited-Hyd")
            avg_total = avg_mum + avg_vapi + avg_blr + avg_hyd

            must_stock = avg_total * 2
            must_order_mum = max((avg_mum * 2) - stock_mum, 0)
            must_order_vapi = max((avg_vapi * 2) - stock_vapi, 0)
            must_order_blr = max((avg_blr * 2) - stock_blr, 0)
            must_order_hyd = max((avg_hyd * 2) - stock_hyd, 0)
            total_required_qty = max(must_stock - total_stock, 0)

            all_data.append({
                "item_code":item.item_code,
                "item_name": item.item_name,
                "item_group": item.item_group,
                "stock_mum": stock_mum,
                "stock_vapi": stock_vapi,
                "stock_blr": stock_blr,
                "stock_hyd": stock_hyd,
                "total_stock": total_stock,
                "ordered_mum": ordered_mum,
                "ordered_vapi": ordered_vapi,
                "ordered_blr": ordered_blr,
                "ordered_hyd": ordered_hyd,
                "delivered_mum": delivered_mum,
                "delivered_vapi": delivered_vapi,
                "delivered_blr": delivered_blr,
                "delivered_hyd": delivered_hyd,
                "open_mum": open_mum,
                "open_vapi": open_vapi,
                "open_blr": open_blr,
                "open_hyd": open_hyd,
                "open_orders": total_open_orders,
                "avg_mum": avg_mum,
                "avg_vapi": avg_vapi,
                "avg_blr": avg_blr,
                "avg_hyd": avg_hyd,
                "average_sales": avg_total,
                "must_stock": must_stock,
                "must_order_mum": must_order_mum,
                "must_order_vapi": must_order_vapi,
                "must_order_blr": must_order_blr,
                "must_order_hyd": must_order_hyd,
                "required_qty": total_required_qty
            })
        except Exception as e:
            frappe.log_error(f"Failed for {item_code}: {e}")

    return all_data
