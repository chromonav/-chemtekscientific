import frappe

from chemtech_custom_app.chemtech.custom_script.salesforce_item_sync import (
    sync_item_to_salesforce,
)


def _get_target_items():
    """Non-disabled Items that have a warehouse pinned on custom_warehouse."""
    return frappe.get_all(
        "Item",
        filters={
            "disabled": 0,
            "custom_warehouse": ["is", "set"],
        },
        fields=["name", "custom_warehouse", "custom_balance_quantity"],
    )


def _get_actual_qty_map(items):
    """{(item_code, warehouse): actual_qty} for the given items, in one query."""
    if not items:
        return {}

    bins = frappe.get_all(
        "Bin",
        filters={
            "item_code": ["in", list({i.name for i in items})],
            "warehouse": ["in", list({i.custom_warehouse for i in items})],
        },
        fields=["item_code", "warehouse", "actual_qty"],
    )

    return {(b.item_code, b.warehouse): b.actual_qty for b in bins}


def update_balance_quantity():
    """Hourly: refresh custom_balance_quantity from Bin, push changes to Salesforce.

    Only items whose quantity actually moved are written and synced, so a quiet
    hour costs one query and no API calls.
    """
    items = _get_target_items()
    qty_map = _get_actual_qty_map(items)

    updated = 0
    failed = 0

    for item in items:
        # No Bin row means nothing has ever been stocked there, which is a
        # balance of zero rather than "unknown".
        qty = int(qty_map.get((item.name, item.custom_warehouse)) or 0)

        if qty == (item.custom_balance_quantity or 0):
            continue

        try:
            # db_set rather than doc.save(): the Item on_update hook would fire a
            # second, redundant Salesforce push for the same record.
            frappe.db.set_value(
                "Item", item.name, "custom_balance_quantity", qty, update_modified=False
            )
            frappe.db.commit()

            sync_item_to_salesforce(frappe.get_doc("Item", item.name))
            updated += 1
        except Exception:
            failed += 1
            frappe.db.rollback()
            frappe.log_error(
                frappe.get_traceback(),
                title=f"Balance Quantity Sync Failed | Item: {item.name}",
            )

    return {"scanned": len(items), "updated": updated, "failed": failed}
