import frappe
import requests

ENDPOINT_PATH = "/services/apexrest/v1/pricebook-gateway"


def _build_entry_record(row):
    """One PricebookEntries row.

    `UnitPrice` is sent as a float rather than a Decimal/string: the gateway
    reads it as a number, and Frappe's Currency field is a float already.
    """
    return {
        "ProductCode": row.product_code or "",
        "UnitPrice": float(row.rate or 0),
        "IsActive": bool(row.is_active),
    }


def _build_pricebook_record(doc):
    return {
        "Name": doc.pricebook_name or doc.name or "",
        "IsActive": bool(doc.is_active),
        "Description": doc.description or "",
        "PricebookEntries": [_build_entry_record(row) for row in (doc.entries or [])],
    }


def sync_pricebook_to_salesforce(doc, method=None):
    """Push a Pricebook, with its entries, to the Salesforce pricebook gateway.

    Wired from hooks.py on after_insert and on_update, the same way Customer and
    Item are. Never raises: a failed sync is logged, it does not block the save.
    """
    if doc.flags.get("ignore_salesforce_sync"):
        return

    from chemtech_custom_app.chemtech.doctype.salesforce_setting.salesforce_setting import (
        get_valid_access_token,
    )

    try:
        sf_setting = frappe.get_single("Salesforce Setting")
        instance_url = sf_setting.salesforce_url.rstrip("/")
        access_token = get_valid_access_token()

        endpoint = f"{instance_url}{ENDPOINT_PATH}"
        payload = {"records": [_build_pricebook_record(doc)]}

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
                title=f"Salesforce Sync Failed | Pricebook: {doc.name}",
            )
            return {"success": False, "error": f"Status {response.status_code}: {response.text}"}

        frappe.log_error(
            message=f"Payload: {frappe.as_json(payload)}\n\nResponse: {response.text}",
            title=f"Salesforce Sync Success | Pricebook: {doc.name}",
        )
        return {"success": True, "response": response.text}

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            title=f"Salesforce Sync Error | Pricebook: {doc.name}",
        )
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def sync_pricebook(name):
    """Push one pricebook on demand — the form's "Sync to Salesforce" button.

    The doc_events hook covers save; this is for re-pushing without editing.
    """
    doc = frappe.get_doc("Pricebook", name)
    doc.check_permission("read")

    return sync_pricebook_to_salesforce(doc)


@frappe.whitelist()
def preview_payload(name):
    """Return exactly what would be POSTed, without sending it.

    Useful when the gateway rejects a record and the question is whether the
    payload or the far side is at fault.
    """
    doc = frappe.get_doc("Pricebook", name)
    doc.check_permission("read")

    return {"records": [_build_pricebook_record(doc)]}
