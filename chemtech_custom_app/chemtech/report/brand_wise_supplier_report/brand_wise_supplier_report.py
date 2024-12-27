# Copyright (c) 2024, abc and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    if not filters:
        filters = {}
    selected_brands = filters.get("brand")
    
    if isinstance(selected_brands, list):
        brand_list = [b.strip() for b in selected_brands]
    elif isinstance(selected_brands, str):
        brand_list = [b.strip() for b in selected_brands.split(",")]
    else:
        brand_list = []

    
    data = get_suppliers_with_brands(brand_list)
    
    columns = get_columns()
    return columns, data

def get_suppliers_with_brands(brand_list):
    """
    Query suppliers whose custom_brand field contains one or more of the selected brands.
    """
    if not brand_list:
        return frappe.db.sql("""
            SELECT
                name AS supplier_name,
                supplier_name AS supplier_display_name,
                custom_brand AS brand_name
            FROM
                `tabSupplier`
        """, as_dict=True)

    # Query to match selected brands with the custom_brand field using FIND_IN_SET.
    return frappe.db.sql("""
        SELECT
            name AS supplier_name,
            supplier_name AS supplier_display_name,
            custom_brand AS brand_name
        FROM
            `tabSupplier`
        WHERE
            (
                SELECT GROUP_CONCAT(brand) 
                FROM `tabBrand CT` 
                WHERE FIND_IN_SET(brand, tabSupplier.custom_brand)
            ) IS NOT NULL
            
    """, tuple(brand_list), as_dict=True)

def get_columns():
    return [
        # {"label": "Company Name", "fieldname": "company_name", "fieldtype": "Link", "options": "Company", "width": 150},
        {"label": "Supplier Name", "fieldname": "supplier_name", "fieldtype": "Link", "options": "Supplier", "width": 150},
        {"label": "Brand Name", "fieldname": "brand_name", "fieldtype": "Link", "options": "Brand", "width": 150}
    ]