import frappe


def _upsert_single_item(item):
    """Create or update one Item from a payload dict.

    Never raises — always returns a per-item success/failure result.
    """
    product_code = item.get("product_code")

    try:
        if not product_code:
            frappe.throw("product_code is required")

        product_name = item.get("product_name")
        product_group = item.get("product_group")
        uom = item.get("uom")
        warehouse = item.get("warehouse")
        disabled = frappe.utils.cint(item.get("disabled", 0))
        pack = item.get("pack")
        cas_number = item.get("cas_number")
        hsn = item.get("hsn")
        brand = item.get("brand")
        category = item.get("category")
        sub_category = item.get("sub_category")
        product_description = item.get("product_description")

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
            "product_code": product_code,
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
            "product_code": product_code,
            "message": str(e),
        }


@frappe.whitelist(methods=["POST"])
def upsert_item(items=None):
    """
    Bulk create or update ERPNext Items.

    `items` is a list of item payload dicts (each keyed on the mandatory
    `product_code`). Every item is processed independently — one failing
    item does not stop the rest. Returns a per-item result plus an
    overall summary.
    """

    if isinstance(items, str):
        items = frappe.parse_json(items)

    if not items or not isinstance(items, list):
        frappe.throw("items must be a non-empty list")

    results = [_upsert_single_item(item) for item in items]

    return {
        "success": all(result["success"] for result in results),
        "total": len(results),
        "success_count": sum(1 for result in results if result["success"]),
        "failed_count": sum(1 for result in results if not result["success"]),
        "results": results,
    }
