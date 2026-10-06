import frappe
import requests
from frappe import _
from frappe.utils import getdate, nowdate


ENDPOINT_PATH = "/services/apexrest/v1/pricebook-gateway"


def _push_to_salesforce(record, label):
    """POST one pricebook record to the gateway. Never raises: failures are
    logged and returned as {"success": False, "error": ...}."""

    from chemtech_custom_app.chemtech.doctype.salesforce_setting.salesforce_setting import (
        get_valid_access_token,
    )

    try:
        sf_setting = frappe.get_single("Salesforce Setting")
        instance_url = sf_setting.salesforce_url.rstrip("/")
        access_token = get_valid_access_token()

        endpoint = f"{instance_url}{ENDPOINT_PATH}"
        payload = {"records": [record]}

        response = requests.post(
            endpoint,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            timeout=30,
        )

        if not response.ok:
            frappe.log_error(
                message=f"Status {response.status_code}: {response.text}",
                title=f"Salesforce Sync Failed | {label}",
            )
            return {"success": False, "error": f"Status {response.status_code}: {response.text}"}

        frappe.log_error(
            message=f"Payload: {frappe.as_json(payload)}\n\nResponse: {response.text}",
            title=f"Salesforce Sync Success | {label}",
        )
        return {"success": True, "response": response.text}

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            title=f"Salesforce Sync Error | {label}",
        )
        return {"success": False, "error": str(e)}


def _is_effective(row, today):
    """True when the Item Price has started and has not expired."""
    return not (row.valid_from and getdate(row.valid_from) > today) and not (
        row.valid_upto and getdate(row.valid_upto) < today
    )


def _build_item_price_entry(row, today):
    """One Item Price row -> PricebookEntries record. Item Price has no active
    flag, so a price is active while it is within its validity window."""
    return {
        "ProductCode": row.item_code or "",
        "UnitPrice": float(row.price_list_rate or 0),
        "IsActive": _is_effective(row, today),
    }


def _build_price_list_record(price_list):
    """Price List + the Item Price documents linked to it -> gateway record."""
    item_prices = frappe.get_all(
        "Item Price",
        filters={"price_list": price_list.name},
        fields=["item_code", "price_list_rate", "valid_from", "valid_upto"],
        order_by="item_code asc, valid_from desc, modified desc",
    )

    # Salesforce keys an entry on ProductCode, so only one Item Price per item
    # can be sent. Item Prices pile up per item (re-entered prices, UOM or
    # validity variants); pick the one ERPNext would apply today: the newest
    # valid_from that has started and not expired. An item with no currently
    # effective price falls back to its newest row, sent as inactive.
    today = getdate(nowdate())
    chosen = {}
    for row in item_prices:
        current = chosen.get(row.item_code)
        if current is not None and _is_effective(current, today):
            continue
        if current is None or _is_effective(row, today):
            chosen[row.item_code] = row

    return {
        "Name": price_list.price_list_name or price_list.name or "",
        "IsActive": bool(price_list.enabled),
        "Description": price_list.get("custom_description") or "",
        "PricebookEntries": [_build_item_price_entry(row, today) for row in chosen.values()],
    }


@frappe.whitelist()
def sync_price_list(name):
    """Push one Price List and its Item Prices — the Price List form's
    "Sync to Salesforce" button."""
    price_list = frappe.get_doc("Price List", name)
    price_list.check_permission("read")

    try:
        record = _build_price_list_record(price_list)
    except frappe.ValidationError as e:
        return {"success": False, "error": str(e)}

    return _push_to_salesforce(record, f"Price List: {price_list.name}")


@frappe.whitelist()
def preview_price_list_payload(name):
    """Return exactly what sync_price_list would POST, without sending it."""
    price_list = frappe.get_doc("Price List", name)
    price_list.check_permission("read")

    return {"records": [_build_price_list_record(price_list)]}
