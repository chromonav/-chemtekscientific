import frappe

def execute(filters=None):
    if not filters:
        filters = {}
    
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {"label": "Quotation", "fieldname": "quotation", "fieldtype": "Link", "options": "Quotation", "width": 150},
        {"label": "QT Date", "fieldname": "qt_date", "fieldtype": "Date", "width": 100},
        {"label": "Customer Name", "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
        {"label": "Quotation Status", "fieldname": "quotation_status", "fieldtype": "HTML", "width": 150},
        {"label": "Sales Order", "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 150},
        {"label": "SO Date", "fieldname": "so_date", "fieldtype": "Date", "width": 100},
        {"label": "SO Delivered/Billed %", "fieldname": "so_delivered_billed", "fieldtype": "Data", "width": 150},
        {"label": "SO Status", "fieldname": "so_status", "fieldtype": "HTML", "width": 150},
        {"label": "SO Adv Payment", "fieldname": "so_adv_payment", "fieldtype": "Currency", "width": 150},
        {"label": "Production Plan", "fieldname": "production_plan", "fieldtype": "Link", "options": "Production Plan", "width": 150},
        {"label": "PRO Date", "fieldname": "pro_date", "fieldtype": "Date", "width": 100},
        {"label": "PP Status", "fieldname": "pp_status", "fieldtype": "HTML", "width": 150},
        {"label": "Work Order", "fieldname": "work_order", "fieldtype": "Link", "options": "Work Order", "width": 150},
        {"label": "Plan Date", "fieldname": "plan_date", "fieldtype": "Date", "width": 100},
        {"label": "Work Order Status", "fieldname": "work_order_status", "fieldtype": "HTML", "width": 150},
        {"label": "Delivery Note", "fieldname": "delivery_note", "fieldtype": "Link", "options": "Delivery Note", "width": 150},
        {"label": "DN Date", "fieldname": "dn_date", "fieldtype": "Date", "width": 100},
        {"label": "DN Status", "fieldname": "dn_status", "fieldtype": "HTML", "width": 150},
        {"label": "Sales Invoice", "fieldname": "sales_invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 150},
        {"label": "SI Date", "fieldname": "si_date", "fieldtype": "Date", "width": 100},
        {"label": "Invoice Status", "fieldname": "invoice_status", "fieldtype": "HTML", "width": 150},
    ]

# def get_data(filters):
#     conditions = ""
#     if filters.get("start_date") and filters.get("end_date"):
#         conditions += " AND q.transaction_date BETWEEN %(start_date)s AND %(end_date)s "
    
#     query = """
#     SELECT 
#         q.name AS quotation,
#         q.transaction_date AS qt_date,
#         q.customer_name,
#         CASE q.status
#             WHEN 'Draft' THEN '<span style="color: #808080">' || q.status || '</span>'
#             WHEN 'Submitted' THEN '<span style="color: #0000FF">' || q.status || '</span>'
#             WHEN 'Cancelled' THEN '<span style="color: #FF0000">' || q.status || '</span>'
#             WHEN 'Ordered' THEN '<span style="color: #008000">' || q.status || '</span>'
#             ELSE q.status
#         END AS quotation_status,
#         so.name AS sales_order,
#         so.transaction_date AS so_date,
#         CONCAT(
#             ROUND((SUM(CASE WHEN so.per_billed < 100 AND so.per_delivered = 100 THEN 1 ELSE 0 END) / COUNT(so.name)) * 100, 2), '%% | ',
#             ROUND((SUM(CASE WHEN so.per_delivered < 100 THEN 1 ELSE 0 END) / COUNT(so.name)) * 100, 2), '%%'
#         ) AS so_delivered_billed,
#         CASE so.status
#             WHEN 'Draft' THEN '<span style="color: #808080">' || so.status || '</span>'
#             WHEN 'To Deliver and Bill' THEN '<span style="color: red">' || so.status || '</span>'
#             WHEN 'Completed' THEN '<span style="color: #008000">' || so.status || '</span>'
#             ELSE so.status
#         END AS so_status,
#         so.advance_paid AS so_adv_payment,
#         pp.name AS production_plan,
#         pp.posting_date AS pro_date,
#         pp.status AS pp_status,
#         wo.name AS work_order,
#         wo.planned_start_date AS plan_date,
#         dn.name AS delivery_note,
#         dn.posting_date AS dn_date,
#         si.name AS sales_invoice,
#         si.posting_date AS si_date,
#         si.status AS invoice_status
#     FROM 
#         `tabQuotation` AS q
#         LEFT JOIN `tabSales Order Item` AS soi ON soi.prevdoc_docname = q.name
#         LEFT JOIN `tabSales Order` AS so ON soi.parent = so.name
#         LEFT JOIN `tabProduction Plan` AS pp ON pp.name = so.name
#         LEFT JOIN `tabWork Order` AS wo ON wo.production_plan = pp.name
#         LEFT JOIN `tabDelivery Note` AS dn ON dn.name = so.name
#         LEFT JOIN `tabSales Invoice` AS si ON si.name = so.name
#     WHERE 1=1 {conditions}
#     GROUP BY q.name
#     ORDER BY q.name;
#     """.format(conditions=conditions)
    
#     return frappe.db.sql(query, filters, as_dict=True)




def get_data(filters):
    conditions = ""
    if filters.get("start_date") and filters.get("end_date"):
        conditions += " AND q.transaction_date BETWEEN %(start_date)s AND %(end_date)s "
    
    query = """
    SELECT 
        q.name AS quotation,
        q.transaction_date AS qt_date,
        q.customer_name,
        CASE q.status
            WHEN 'Draft' THEN '<span style="color: #808080">' || q.status || '</span>'
            WHEN 'Submitted' THEN '<span style="color: #0000FF">' || q.status || '</span>'
            WHEN 'Cancelled' THEN '<span style="color: #FF0000">' || q.status || '</span>'
            WHEN 'Ordered' THEN '<span style="color: #008000">' || q.status || '</span>'
            ELSE q.status
        END AS quotation_status,
        so.name AS sales_order,
        so.transaction_date AS so_date,
        CONCAT(
            ROUND((SUM(CASE WHEN so.per_billed < 100 AND so.per_delivered = 100 THEN 1 ELSE 0 END) / COUNT(so.name)) * 100, 2), '%% | ',
            ROUND((SUM(CASE WHEN so.per_delivered < 100 THEN 1 ELSE 0 END) / COUNT(so.name)) * 100, 2), '%%'
        ) AS so_delivered_billed,
        CASE so.status
            WHEN 'Draft' THEN '<span style="color: #808080">' || so.status || '</span>'
            WHEN 'To Deliver and Bill' THEN '<span style="color: red">' || so.status || '</span>'
            WHEN 'Completed' THEN '<span style="color: #008000">' || so.status || '</span>'
            ELSE so.status
        END AS so_status,
        so.advance_paid AS so_adv_payment,
        pp.name AS production_plan,
        pp.posting_date AS pro_date,
        pp.status AS pp_status,
        wo.name AS work_order,
        wo.planned_start_date AS plan_date,
        dn.name AS delivery_note,
        dn.posting_date AS dn_date,
        si.name AS sales_invoice,
        si.posting_date AS si_date,
        si.status AS invoice_status
    FROM 
        `tabQuotation` AS q
        LEFT JOIN `tabSales Order Item` AS soi ON soi.prevdoc_docname = q.name
        LEFT JOIN `tabSales Order` AS so ON soi.parent = so.name
        LEFT JOIN `tabProduction Plan Item` AS ppi ON ppi.sales_order = so.name
        LEFT JOIN `tabProduction Plan` AS pp ON pp.name = ppi.parent
        LEFT JOIN `tabWork Order` AS wo ON wo.production_plan = pp.name
        LEFT JOIN `tabDelivery Note` AS dn ON dn.name = so.name
		LEFT JOIN `tabSales Invoice` AS si ON si.name = so.name
    WHERE 1=1 {conditions}
    GROUP BY q.name
    ORDER BY q.name;
    """.format(conditions=conditions)
    
    return frappe.db.sql(query, filters, as_dict=True)
