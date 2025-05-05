# Copyright (c) 2025, abc and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

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
        AND si.posting_date BETWEEN DATE_SUB(CURDATE(), INTERVAL 12 MONTH) AND CURDATE()
        GROUP BY sii.item_code
        ORDER BY total_sold DESC
    """, as_dict=True)


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
    # Fetch all forecast data for the given salespersons and item_code
    forecast_data = {sp: 0 for sp in salespersons}

    forecasts = frappe.get_all(
        "Salesperson Forecast",
        filters={"sales_person": ["in", salespersons]},
        fields=["name", "sales_person"]
    )

    # Get all forecast child table data at once for the relevant forecasts
    forecast_ct_data = frappe.get_all(
        "Salesperson Forecast CT",
        filters={"parent": ["in", [forecast.name for forecast in forecasts]], "item": item_code},
        fields=["parent", "sales_qty", "month", "item"]
    )

    # Map to group sales_qty by salesperson and item
    sales_forecast_map = {sp: {} for sp in salespersons}

    # Populate the map with forecasted quantities grouped by salesperson and item
    for row in forecast_ct_data:
        sp = next(f for f in forecasts if f.name == row.parent).sales_person
        if row.item == item_code:
            if row.month not in sales_forecast_map[sp]:
                sales_forecast_map[sp][row.month] = 0
            sales_forecast_map[sp][row.month] += flt(row.sales_qty)

    # Sum up the forecast for each salesperson
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
