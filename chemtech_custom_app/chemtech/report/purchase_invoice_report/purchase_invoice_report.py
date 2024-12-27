# Copyright (c) 2024, abc and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import flt

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "ID", "fieldname": "name", "fieldtype": "Link", "options": "Purchase Invoice", "width": 150},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 150},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
        {"label": "Purchase Type", "fieldname": "custom_purchase_type", "fieldtype": "Select", "options": "Fixed Asset Purchase\nOffice Maintenance Purchase\nBusiness Promotion Purchase\nServices Related Purchase\nImport/Custom Related Services\nOther Non-Operational Purchase", "width": 200},
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
        {"label": "Total (Supplier Currency)", "fieldname": "grand_total", "fieldtype": "Currency", "options": "currency", "width": 180},
        {"label": "Currency", "fieldname": "currency", "fieldtype": "Data", "width": 80},
        {"label": "Total (Company Currency)", "fieldname": "grand_total_in_company_currency", "fieldtype": "Currency", "options": "company_currency", "width": 200},
        {"label": "Outstanding Amount", "fieldname": "outstanding_amount", "fieldtype": "Currency", "width": 180},
        {"label": "Due Date", "fieldname": "due_date", "fieldtype": "Date", "width": 120},
        {"label": "Duty Charges", "fieldname": "duty_charges", "fieldtype": "Currency", "width": 150},
        {"label": "Freight Charges", "fieldname": "freight_charges", "fieldtype": "Currency", "width": 150},
        {"label": "Other Charges", "fieldname": "other_charges", "fieldtype": "Currency", "width": 150},
        {"label": "Charges Total (Supplier Currency)", "fieldname": "charges_total", "fieldtype": "Float", "width": 200},
        {"label": "Grand Total (Company Currency)", "fieldname": "total_additional_charges_c", "fieldtype": "Currency", "width": 200},
        {"label": "Grand Total (Supplier Currency)", "fieldname": "total_additional_charges_s", "fieldtype": "Float", "width": 200},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
    ]

def get_data(filters):
    conditions = ""
    if filters.get("company"):
        conditions += " AND pi.company=%(company)s"
    if filters.get("from_date") and filters.get("to_date"):
        conditions += " AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s"

    # Main query with join to child table, Supplier table, and exchange rate table
    query = """
        SELECT
            pi.name,
            pi.supplier,
            pi.company,
            pi.posting_date,
            pi.grand_total,
            pi.currency,
            pi.base_total AS grand_total_in_company_currency,
            pi.outstanding_amount,
            pi.due_date,
            pi.custom_purchase_type, -- Include the custom field
            COALESCE(SUM(adc.duty_charges), 0) AS duty_charges,
            COALESCE(SUM(adc.freight_charges), 0) AS freight_charges,
            COALESCE(SUM(adc.other_charges), 0) AS other_charges,
            COALESCE(SUM(adc.duty_charges + adc.freight_charges + adc.other_charges), 0) + pi.base_total AS total_additional_charges_c,
            pi.status,
            
            -- Calculate exchange rate if currency is not INR
            CASE
                WHEN pi.currency != 'INR' THEN 
                    (SELECT 
                        exchange_rate
                     FROM
                        `tabCurrency Exchange`
                     WHERE
                        from_currency = pi.currency AND to_currency = 'INR' AND
                        DATE(date) <= pi.posting_date
                     ORDER BY
                        date DESC
                     LIMIT 1)
                ELSE 1
            END AS exchange_rate,
            
            -- Apply the exchange rate to the charges and add grand_total
            COALESCE(SUM(adc.duty_charges + adc.freight_charges + adc.other_charges), 0) / 
            CASE
                WHEN pi.currency != 'INR' THEN 
                    (SELECT 
                        exchange_rate
                     FROM
                        `tabCurrency Exchange`
                     WHERE
                        from_currency = pi.currency AND to_currency = 'INR' AND
                        DATE(date) <= pi.posting_date
                     ORDER BY
                        date DESC
                     LIMIT 1)
                ELSE 1
            END AS charges_total,

            COALESCE(SUM(adc.duty_charges + adc.freight_charges + adc.other_charges), 0) / 
            CASE
                WHEN pi.currency != 'INR' THEN 
                    (SELECT 
                        exchange_rate
                     FROM
                        `tabCurrency Exchange`
                     WHERE
                        from_currency = pi.currency AND to_currency = 'INR' AND
                        DATE(date) <= pi.posting_date
                     ORDER BY
                        date DESC
                     LIMIT 1)
                ELSE 1
            END + pi.grand_total AS total_additional_charges_s

        FROM
            `tabPurchase Invoice` AS pi
        LEFT JOIN
            `tabAdditional Duties and Charges CT` AS adc
            ON pi.name = adc.parent
        LEFT JOIN
            `tabSupplier` AS s
            ON pi.supplier = s.name
        WHERE
            pi.docstatus < 2 {conditions}
        GROUP BY
            pi.name
    """.format(conditions=conditions)

    results = frappe.db.sql(query, filters, as_dict=True)
    return results