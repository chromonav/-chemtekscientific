import frappe

from chemtech_custom_app.chemtech.custom_script.salesforce_item_sync import (
    sync_item_to_salesforce,
)


def _get_target_items():
    """Non-disabled Items tracked for balance quantity."""
    return frappe.get_all(
        "Item",
        filters={"disabled": 0},
        fields=["name", "custom_balance_quantity"],
    )


def _get_actual_qty_map():
    """{item_code: total_actual_qty} summed across every warehouse, in one query."""
    bins = frappe.get_all(
        "Bin",
        fields=["item_code", "sum(actual_qty) as actual_qty"],
        group_by="item_code",
    )

    return {b.item_code: b.actual_qty for b in bins}


def update_balance_quantity():
    """Hourly: refresh custom_balance_quantity from Bin (summed across all
    company warehouses), push changes to Salesforce.

    Only items whose quantity actually moved are written and synced, so a quiet
    hour costs one query and no API calls.
    """
    items = _get_target_items()
    qty_map = _get_actual_qty_map()

    updated = 0
    failed = 0

    for item in items:
        # No Bin rows means nothing has ever been stocked anywhere, which is a
        # balance of zero rather than "unknown".
        qty = int(qty_map.get(item.name) or 0)

        if qty == (item.custom_balance_quantity or 0):
            continue

        try:
            doc = frappe.get_doc("Item", item.name)
            doc.custom_balance_quantity = qty
            # Most Items are missing unrelated mandatory custom fields
            # (custom_product_group, custom_sub_category); this job only owns
            # balance quantity and must not be blocked by that.
            doc.flags.ignore_mandatory = True
            doc.save()

            sync_item_to_salesforce(doc)
            updated += 1
        except Exception:
            failed += 1
            frappe.db.rollback()
            frappe.log_error(
                frappe.get_traceback(),
                title=f"Balance Quantity Sync Failed | Item: {item.name}",
            )

    return {"scanned": len(items), "updated": updated, "failed": failed}
