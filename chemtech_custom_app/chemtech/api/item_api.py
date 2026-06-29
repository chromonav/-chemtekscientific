import frappe


@frappe.whitelist(methods=["POST"])
def upsert_item(item_code=None, item_name=None, hsn_sac=None, pack=None, sub_category=None, uom=None, name=None):
    """
    Create or update an Item.
    If `name` is provided, update the existing Item with that name.
    Otherwise, create a new Item using `item_code`.
    Returns the document name.
    """
    if name:
        doc = frappe.get_doc("Item", name)
        if item_code:
            doc.item_code = item_code
        if item_name:
            doc.item_name = item_name
        if uom:
            doc.stock_uom = uom
        if hsn_sac is not None:
            doc.gst_hsn_code = hsn_sac
        if pack is not None:
            doc.pack = pack
        if sub_category is not None:
            doc.custom_sub_category = sub_category
        doc.flags.ignore_salesforce_sync = True
        doc.save(ignore_permissions=True)
    else:
        if not item_code:
            frappe.throw("item_code is required to create a new Item.")
        doc = frappe.get_doc({
            "doctype": "Item",
            "item_code": item_code,
            "item_name": item_name or item_code,
            "stock_uom": uom or "Nos",
            "item_group": "All Item Groups",
            "gst_hsn_code": hsn_sac or "",
            "pack": pack or "",
            "custom_sub_category": sub_category or "",
        })
        doc.flags.ignore_salesforce_sync = True
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"name": doc.name}
