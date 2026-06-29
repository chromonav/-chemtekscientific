import frappe
import requests


def _build_product_record(doc):
    return {
        "Name": doc.item_name,
        "Description": doc.description or "",
        "ProductCode": doc.name,
        "IsActive": not bool(doc.disabled),
        "UOM__c": doc.stock_uom or "",
        "Pack__c": str(doc.get("pack") or ""),
        "HSN_SAC__c": doc.get("gst_hsn_code") or "",
        "Category__c": doc.item_group or "",
        "CAS_Number__c": doc.get("cas_number") or "",
        "Brand__c": doc.brand or "",
        "Sub_Category__c": doc.get("custom_sub_category") or "",
    }


def sync_item_to_salesforce(doc, method=None):
    """Push an Item record to the Salesforce Product2 endpoint."""
    if doc.flags.get("ignore_salesforce_sync"):
        return

    from chemtech_custom_app.chemtech.doctype.salesforce_setting.salesforce_setting import (
        get_valid_access_token,
    )

    try:
        sf_setting = frappe.get_single("Salesforce Setting")
        instance_url = sf_setting.salesforce_url.rstrip("/")
        access_token = get_valid_access_token()

        endpoint = f"{instance_url}/services/apexrest/v1/data-gateway/Product2"
        payload = {"records": [_build_product_record(doc)]}

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
                title=f"Salesforce Sync Failed | Item: {doc.name}",
            )
        else:
            frappe.log_error(
                message=f"Payload: {frappe.as_json(payload)}\n\nResponse: {response.text}",
                title=f"Salesforce Sync Success | Item: {doc.name}",
            )

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            title=f"Salesforce Sync Error | Item: {doc.name}",
        )
