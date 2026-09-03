import frappe


@frappe.whitelist(methods=["POST"])
def upsert_item(
    product_code=None,
    product_name=None,
    product_group=None,
    uom=None,
    warehouse=None,
    disabled=0,
    pack=None,
    cas_number=None,
    hsn=None,
    brand=None,
    category=None,
    sub_category=None,
    product_description=None,
):
    """
    Create or Update ERPNext Item using Product Code.

    product_code is mandatory.
    """

    try:
        if not product_code:
            frappe.throw("product_code is required")

        # Convert disabled safely
        disabled = frappe.utils.cint(disabled)

        # Check whether Item already exists
        if frappe.db.exists("Item", {"item_code": product_code}):

            item_name = frappe.db.get_value(
                "Item",
                {"item_code": product_code},
                "name"
            )

            doc = frappe.get_doc("Item", item_name)
            action = "updated"

        else:
            doc = frappe.new_doc("Item")
            doc.item_code = product_code
            action = "created"

        # Mandatory / Standard Fields
        doc.item_code = product_code
        doc.item_name = product_name or product_code
        doc.custom_product_group = product_group or "All Item Groups"
        doc.stock_uom = uom or "Nos"
        doc.disabled = disabled

        # Custom Fields
        doc.gst_hsn_code = hsn or ""
        doc.pack = pack or ""
        doc.cas_number = cas_number or ""
        doc.brand = brand or ""
        doc.item_group = category or ""
        doc.custom_sub_category = sub_category or ""
        doc.description = product_description or ""
        doc.custom_warehouse = warehouse or ""

        # Disable Salesforce Sync
        doc.flags.ignore_salesforce_sync = True

        if action == "created":
            doc.insert(ignore_permissions=True)
        else:
            doc.save(ignore_permissions=True)

        frappe.db.commit()

        return {
            "success": True,
            "message": f"Item {action} successfully",
            "action": action,
            "data": {
                "name": doc.name,
                "item_code": doc.item_code,
                "item_name": doc.item_name,
            },
        }

    except Exception as e:

        frappe.db.rollback()

        frappe.log_error(
            frappe.get_traceback(),
            "Item Upsert API Error"
        )

        return {
            "success": False,
            "message": str(e),
        }