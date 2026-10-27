import re
from html import unescape

import frappe
import requests
from frappe import _
from frappe.utils import strip_html



def _get_gst_rate(doc):
    """GST rate from the first row of the Item's tax table, as a plain number.

    Only the first `taxes` row is considered, no matter how many are present.
    Returns None when there is no row, no template, or no rate on the template.
    """
    taxes = doc.get("taxes") or []
    if not taxes:
        return None

    template = taxes[0].get("item_tax_template")
    if not template:
        return None

    rate = frappe.db.get_value("Item Tax Template", template, "gst_rate")
    if rate in (None, ""):
        return None

    rate = float(rate)
    return int(rate) if rate.is_integer() else rate


def _plain_text(html_value):
    """Item descriptions are stored as HTML (text editor); Salesforce wants plain text."""
    if not html_value:
        return ""
    # Block-level boundaries become a space so "</p><p>" does not glue words together.
    text = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6])>", " ", html_value)
    text = strip_html(text)
    return " ".join(unescape(text).split())


def _build_product_record(doc):
    return {
        "Name": doc.item_name,
        "Description": _plain_text(doc.description),
        "ProductCode": doc.name,
        "IsActive": not bool(doc.disabled),
        "UOM__c": doc.stock_uom or "",
        "Pack__c": str(doc.get("pack") or ""),
        "HSN_SAC__c": doc.get("gst_hsn_code") or "",
        "Category__c": doc.item_group or "",
        "CAS_Number__c": doc.get("cas_number") or "",
        "Brand__c": doc.brand or "",
        "Sub_Category__c": doc.get("custom_sub_category") or "",
        "GST__c": _get_gst_rate(doc),
        # Restricted picklists on Product2: an unset value has to go as null,
        # since "" is not one of the allowed entries.
        "Record_Type__c": doc.get("custom_product_group") or None,
        "Balance_Qty__c": int(doc.get("custom_balance_quantity") or 0),
        "Raw_Material_Price__c": int(doc.get("custom_raw_material_price") or 0)
    }


def _is_syncable_item(doc):
    return not doc.flags.get("ignore_salesforce_sync") and doc.get("custom_product_group") != "NPD"


def _failed_all(item_names, error):
    return [{"item": name, "error": error} for name in item_names]


def _collect_failures(item_names, data):
    """Match the gateway's per-record `results` (same order as the request) to Items."""
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list) or len(results) != len(item_names):
        return None

    failed = []
    for name, result in zip(item_names, results):
        if not result.get("success"):
            errors = result.get("errors") or []
            failed.append({"item": name, "error": "; ".join(errors) or "Unknown error"})
    return failed


def _result(synced, skipped, failed, response=None):
    result = {
        "success": not failed,
        "synced": synced,
        "skipped": skipped,
        "failed": failed,
        "response": response,
    }
    if failed:
        result["error"] = "; ".join(f"{f['item']}: {f['error']}" for f in failed)
    return result


def sync_items_to_salesforce(docs):
    """Push one or more Item records to the Salesforce Product2 endpoint."""
    syncable_docs = [doc for doc in docs if _is_syncable_item(doc)]
    skipped_items = [doc.name for doc in docs if not _is_syncable_item(doc)]

    if not syncable_docs:
        return _result(0, skipped_items, [])

    from chemtech_custom_app.chemtech.doctype.salesforce_setting.salesforce_setting import (
        get_valid_access_token,
    )

    payload = {"records": [_build_product_record(doc) for doc in syncable_docs]}
    item_names = [doc.name for doc in syncable_docs]

    try:
        sf_setting = frappe.get_single("Salesforce Setting")
        instance_url = sf_setting.salesforce_url.rstrip("/")
        access_token = get_valid_access_token()
        endpoint = f"{instance_url}/services/apexrest/v1/data-gateway/Product2"

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
            error = f"Status {response.status_code}: {response.text}"
            frappe.log_error(
                message=(
                    f"Items: {frappe.as_json(item_names)}\n\n"
                    f"Payload: {frappe.as_json(payload)}\n\nResponse: {error}"
                ),
                title=f"Salesforce Bulk Sync Failed | Items: {len(item_names)}",
            )
            return _result(0, skipped_items, _failed_all(item_names, error))

        try:
            failed = _collect_failures(item_names, response.json())
        except ValueError:
            failed = None
        if failed is None:
            # Response not in the documented shape: the request was accepted, but
            # individual outcomes can't be told apart.
            failed = []

        outcome = "Success" if not failed else "Partial Failure"
        frappe.log_error(
            message=(
                f"Items: {frappe.as_json(item_names)}\n\n"
                f"Payload: {frappe.as_json(payload)}\n\nResponse: {response.text}"
            ),
            title=f"Salesforce Bulk Sync {outcome} | Items: {len(item_names)}",
        )
        return _result(len(item_names) - len(failed), skipped_items, failed, response.text)

    except Exception as e:
        frappe.log_error(
            title=f"Salesforce Bulk Sync Error | Items: {len(item_names)}",
            message=f"Items: {frappe.as_json(item_names)}\n\n{frappe.get_traceback()}",
        )
        return _result(0, skipped_items, _failed_all(item_names, str(e)))


def sync_item_to_salesforce(doc, method=None):
    """Push an Item record to the Salesforce Product2 endpoint."""
    result = sync_items_to_salesforce([doc])
    if result["success"] and not result["synced"]:
        return None
    return result


def _publish_bulk_sync_complete(user, result):
    frappe.publish_realtime(
        "salesforce_item_bulk_sync_complete",
        {
            "requested": result["requested"],
            "synced": result["synced"],
            "skipped": len(result["skipped"]),
            "failed": result["failed"],
        },
        user=user,
        after_commit=True,
    )


def _sync_items_in_background(item_names, requested_by):
    try:
        docs = [frappe.get_doc("Item", name) for name in item_names]
        result = sync_items_to_salesforce(docs)
    except Exception as e:
        frappe.log_error(title="Salesforce Bulk Sync Error | Item load", message=frappe.get_traceback())
        result = _result(0, [], _failed_all(item_names, str(e)))

    result["requested"] = len(item_names)
    _publish_bulk_sync_complete(requested_by, result)


@frappe.whitelist(methods=["POST"])
def enqueue_bulk_item_sync(item_names):
    """Queue selected Items for one Salesforce Product2 bulk request."""
    item_names = frappe.parse_json(item_names)
    if not isinstance(item_names, list) or not item_names:
        frappe.throw(_("Select at least one Item to sync."))

    unique_item_names = list(dict.fromkeys(str(name) for name in item_names if name))
    if not unique_item_names:
        frappe.throw(_("Select at least one Item to sync."))

    for name in unique_item_names:
        frappe.get_doc("Item", name).check_permission("read")

    frappe.enqueue(
        _sync_items_in_background,
        queue="long",
        timeout=300,
        item_names=unique_item_names,
        requested_by=frappe.session.user,
    )
    return {"queued": len(unique_item_names)}


@frappe.whitelist()
def sync_item(name):
    """Push one item on demand -- the form's "Sync to Salesforce" button."""
    doc = frappe.get_doc("Item", name)
    doc.check_permission("read")

    return sync_item_to_salesforce(doc)
