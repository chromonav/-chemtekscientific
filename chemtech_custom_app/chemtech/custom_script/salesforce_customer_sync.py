import frappe
import requests


def _get_billing_address(customer_name):
    """Return billing address fields for the customer, or empty strings."""
    address_name = frappe.db.get_value(
        "Dynamic Link",
        {"link_doctype": "Customer", "link_name": customer_name, "parenttype": "Address"},
        "parent",
        order_by="creation asc",
    )
    if not address_name:
        return {}

    addr = frappe.db.get_value(
        "Address",
        address_name,
        ["address_line1", "city", "pincode", "state", "country"],
        as_dict=True,
    )
    if not addr:
        return {}

    return {
        "BillingStreet": addr.address_line1 or "",
        "BillingCity": addr.city or "",
        "BillingPostalCode": addr.pincode or "",
        "BillingState": addr.state or "",
        "BillingCountry": addr.country or "",
    }


def _get_shipping_address(customer_name):
    """Return shipping address fields for the customer, or empty strings."""
    address_names = frappe.db.get_all(
        "Dynamic Link",
        filters={"link_doctype": "Customer", "link_name": customer_name, "parenttype": "Address"},
        fields=["parent"],
        order_by="creation asc",
        limit=2,
    )
    # Use second address as shipping if available, otherwise same as billing
    name = address_names[1].parent if len(address_names) > 1 else (address_names[0].parent if address_names else None)
    if not name:
        return {}

    addr = frappe.db.get_value(
        "Address",
        name,
        ["address_line1", "city", "pincode", "state", "country"],
        as_dict=True,
    )
    if not addr:
        return {}

    return {
        "ShippingStreet": addr.address_line1 or "",
        "ShippingCity": addr.city or "",
        "ShippingPostalCode": addr.pincode or "",
        "ShippingState": addr.state or "",
        "ShippingCountry": addr.country or "",
    }


def _build_account_record(doc):
    record = {
        "Name": doc.customer_name or "",
        "SF_Cust_Code__c": doc.get("sf_cust_code") or "",
        "Phone": doc.mobile_no or "",
        "Fax": doc.get("fax") or "",
        "Website": doc.website or "",
        "ERP_Cust_Code__c": doc.name or "",
        "GST_Category__c": doc.get("gst_category") or "",
        "GSTIN_UIN__c": doc.get("gstin") or doc.tax_id or "",
        "PAN_No__c": doc.get("pan") or "",
        "Account_Type__c": doc.get("account_type") or "",
        "Customer_Type__c": doc.customer_type or "",
        "Payment_Terms__c": doc.payment_terms or "",
        "Industry": doc.industry or "",
        "Description": doc.get("customer_details") or "",
    }
    record.update(_get_billing_address(doc.name))
    record.update(_get_shipping_address(doc.name))
    return record


def sync_customer_to_salesforce(doc, method=None):
    """Push a Customer record to the Salesforce Account endpoint."""
    from chemtech_custom_app.chemtech.doctype.salesforce_setting.salesforce_setting import (
        get_valid_access_token,
    )

    try:
        sf_setting = frappe.get_single("Salesforce Setting")
        instance_url = sf_setting.salesforce_url.rstrip("/")
        access_token = get_valid_access_token()

        endpoint = f"{instance_url}/services/apexrest/v1/data-gateway/Account"
        payload = {"records": [_build_account_record(doc)]}

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
                title=f"Salesforce Sync Failed | Customer: {doc.name}",
            )
        else:
            frappe.log_error(
                message=f"Payload: {frappe.as_json(payload)}\n\nResponse: {response.text}",
                title=f"Salesforce Sync Success | Customer: {doc.name}",
            )

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            title=f"Salesforce Sync Error | Customer: {doc.name}",
        )
