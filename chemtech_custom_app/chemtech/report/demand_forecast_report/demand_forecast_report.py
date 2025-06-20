# Copyright (c) 2025, abc and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

FIXED_ITEM_CODES = [
    "I5040-2.5 Litre", "I5041-2.5 Litre", "I5026-2.5L", "I5022-2.5l", "340-1L", "304-1L", "081-1L", "076-1L", "071-1L", "242-4L",
    "300-1L", "LC015-4L", "010-1L", "212-1L", "323-1 Litre", "51779-1L", "51781-1L", "69337-1 Litre", "44901-1 Litre", "80708-1L",
    "67484-1L", "79606-100ML", "79606-500 Millilitre", "17836-50G", "60221-250G", "17843-50G", "89152-250G", "17839-50G",
    "17839-10 Gram", "17843-250G", "17836-250G", "89152-50G", "34851-4L", "34885-2.5L", "34885-4 Litre", "34851-2.5 Litre",
    "34442-2.5L", "34865-1 Litre", "34850-1L", "34859-2.5L", "34860-2.5L", "34875-2.5L", "34836-500 Millilitre",
    "34828-10x4 Millilitre", "34739-500 Mililiter", "34805-500 Millilitre", "34741-1L", "34800-1 Litre", "34696-25 Gram",
    "34810-500 Mililitre", "34806-1 Litre", "34847-10x4 Millilitre", "34836-1 Litre", "34806-500ML", "34820-500 Mililiter",
    "34698-1 Litre", "34805-1 Litre.", "34849-10x8 Millilitre", "34816-1 Litre", "34840-50 Millilitre", "34803-100G",
    "34724-1L", "37859-1 Litre", "34693-10 Gram", "34840-10x5 Millilitre", "34827-1 Litre", "34817-1 Litre", "34738-1L",
    "34827-500Millilitre", "34807-500ML", "34821-50ML", "34811-500 Mililiters", "34816-500ML", "34801-1L", "34811-1L",
    "94318-250 Millilitre", "56302-50ML", "91707-10X1ML", "14267-25G", "40967-10X1ML", "55674-50G", "49199-50 Millilitre",
    "40867-50 Gram", "14266-25G", "34966-2.5L", "34967-4L", "39253-4 Litre", "34967-2.5L", "34966-4 Litre", "34965-1L",
    "39253-1L", "34986-1L", "34972-1L", "40967-10ML", "34972-2.5L", "44273-100ML", "34965-2.5L", "14264-50ML", "34986-2.5L",
    "65897-50ML", "84385-1 Litre", "95305-1L", "84385-2.5L", "84415-500 Mililiter", "08256-1L", "32221-500 MiliLitre",
    "61626H-500ML", "63548-1KG", "34488-1 Litre", "13423-5KG", "34856-2.5L", "221864-100G", "T6508-100ML", "34873-1L",
    "34856-1L", "45741-1L", "11090-5G", "P0662-500G", "33209-1L"
]

def execute(filters=None):
    columns = get_columns()
    data = []

    top_items = get_top_skus()
    salespersons = get_salespersons_in_forecast()

    for item in top_items:
        row = []
        company = frappe.defaults.get_user_default("Company")
        item_code = item.item_code
        available_qty = get_stock_quantity(item_code)
        forecast_by_salesperson = get_forecast_by_salesperson(item_code, salespersons)
        last_year_avg = get_last_year_avg_sold(item_code)

        total_forecast = sum(forecast_by_salesperson.values())
        new_order = available_qty - total_forecast

        row.append(company)
        row.append(item_code)
        row.append(available_qty)

        for sp in salespersons:
            row.append(forecast_by_salesperson.get(sp, 0))

        row.append(last_year_avg)
        row.append(new_order)
        data.append(row)

    return columns, data


def get_columns():
    salespersons = get_salespersons_in_forecast()
    columns = [
        {"label": "Company", "fieldname": "company", "fieldtype": "Data", "width": 150},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Available Stock", "fieldname": "stock_qty", "fieldtype": "Float", "width": 120},
    ]

    for sp in salespersons:
        columns.append({
            "label": f"{sp}",
            "fieldname": frappe.scrub(f"forecast_{sp}"),
            "fieldtype": "Float",
            "width": 120
        })

    columns += [
        {"label": "Last Year Avg Sold", "fieldname": "last_year_avg", "fieldtype": "Float", "width": 120},
        {"label": "New Order Required", "fieldname": "new_order", "fieldtype": "Float", "width": 120},
    ]

    return columns


def get_top_skus():
    return frappe.db.sql("""
        SELECT sii.item_code, SUM(sii.qty) as total_sold
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON sii.parent = si.name
        WHERE si.docstatus = 1
        AND sii.item_code IN %s
        AND si.posting_date BETWEEN DATE_SUB(CURDATE(), INTERVAL 12 MONTH) AND CURDATE()
        GROUP BY sii.item_code
        ORDER BY total_sold DESC
    """, (tuple(FIXED_ITEM_CODES),), as_dict=True)


def get_stock_quantity(item_code):
    qty = frappe.db.sql("""
        SELECT SUM(actual_qty)
        FROM `tabBin`
        WHERE item_code = %s
    """, (item_code,))
    return flt(qty[0][0]) if qty and qty[0][0] else 0


def get_salespersons_in_forecast():
    return frappe.get_all(
        "Salesperson Forecast",
        fields=["DISTINCT sales_person"],
        pluck="sales_person"
    )


def get_forecast_by_salesperson(item_code, salespersons):
    forecast_data = {sp: 0 for sp in salespersons}

    forecasts = frappe.get_all(
        "Salesperson Forecast",
        filters={"sales_person": ["in", salespersons]},
        fields=["name", "sales_person"]
    )

    forecast_ct_data = frappe.get_all(
        "Salesperson Forecast CT",
        filters={"parent": ["in", [forecast.name for forecast in forecasts]], "item": item_code},
        fields=["parent", "sales_qty", "month", "item"]
    )

    sales_forecast_map = {sp: {} for sp in salespersons}

    for row in forecast_ct_data:
        sp = next(f for f in forecasts if f.name == row.parent).sales_person
        if row.month not in sales_forecast_map[sp]:
            sales_forecast_map[sp][row.month] = 0
        sales_forecast_map[sp][row.month] += flt(row.sales_qty)

    for sp in salespersons:
        forecast_data[sp] = sum(sales_forecast_map[sp].values())

    return forecast_data


def get_last_year_avg_sold(item_code):
    qty = frappe.db.sql("""
        SELECT AVG(sii.qty) as avg_sold
        FROM `tabSales Invoice Item` sii
        JOIN `tabSales Invoice` si ON sii.parent = si.name
        WHERE sii.item_code = %s
        AND si.posting_date BETWEEN DATE_SUB(CURDATE(), INTERVAL 12 MONTH) AND CURDATE()
        AND si.docstatus = 1
    """, (item_code,))
    return flt(qty[0][0]) if qty and qty[0][0] else 0
