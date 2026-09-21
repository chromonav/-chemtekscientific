import frappe
import requests


ADDRESS_FIELDS = ["address_line1", "address_line2", "city", "pincode", "state", "country"]


def _linked_addresses(customer_name):
    """Every Address linked to the customer, oldest first."""
    return frappe.get_all(
        "Dynamic Link",
        filters={
            "link_doctype": "Customer",
            "link_name": customer_name,
            "parenttype": "Address",
        },
        pluck="parent",
        order_by="creation asc",
    )


def _pick_address(customer_name, address_type):
    """The address of the given type, falling back to the oldest linked one.

    Addresses written by the Salesforce API are typed Billing/Shipping, but
    older records were created by hand and may carry any type, so a customer
    with a single untyped address still syncs something useful.
    """
    linked = _linked_addresses(customer_name)
    if not linked:
        return None

    typed = frappe.db.get_value(
        "Address", {"name": ["in", linked], "address_type": address_type}, "name"
    )
    return typed or linked[0]


def _address_values(customer_name, address_type, prefix):
    name = _pick_address(customer_name, address_type)
    if not name:
        return {}

    addr = frappe.db.get_value("Address", name, ADDRESS_FIELDS, as_dict=True)
    if not addr:
        return {}

    # Salesforce keeps the street as one textarea, so both ERPNext lines go in
    # separated by a newline -- otherwise address_line2 is lost on the way out.
    street = "\n".join(filter(None, [addr.address_line1, addr.address_line2]))

    return {
        f"{prefix}Street": street,
        f"{prefix}City": addr.city or "",
        f"{prefix}PostalCode": addr.pincode or "",
        f"{prefix}State": addr.state or "",
        f"{prefix}Country": addr.country or "",
    }


def _build_account_record(doc):
    record = {
        "Name": doc.customer_name or "",
        # ERP_Cust_Code__c carries the account code we generate. SF_Cust_Code__c
        # is Salesforce's own code and is not createable, so it is never sent.
        "ERP_Cust_Code__c": doc.get("account_code") or "",
        "Phone": doc.mobile_no or "",
        "Fax": doc.get("custom_fax") or "",
        "Website": doc.website or "",
        "GST_Category__c": doc.get("gst_category") or "",
        "GSTIN_UIN__c": doc.get("gstin") or doc.tax_id or "",
        "PAN_No__c": doc.get("pan") or "",
        "Territory__c": doc.get("territory") or "",
        "Industry": doc.industry or "",
        "Description": doc.get("customer_details") or "",
        # Restricted picklists: an unset value has to go as null, since "" is
        # not one of the allowed entries.
        "Account_Type__c": doc.get("custom_account_type") or None,
        "Customer_Type__c": doc.customer_type or None,
        "Customer_Group__c": doc.get("customer_group") or None,
        "Payment_Terms__c": doc.payment_terms or None,
    }
    record.update(_address_values(doc.name, "Billing", "Billing"))
    record.update(_address_values(doc.name, "Shipping", "Shipping"))
    return record


def sync_customer_to_salesforce(doc, method=None):
    """Push a Customer record to the Salesforce Account endpoint."""
    if doc.flags.get("ignore_salesforce_sync"):
        return

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
            return {"success": False, "error": f"Status {response.status_code}: {response.text}"}

        frappe.log_error(
            message=f"Payload: {frappe.as_json(payload)}\n\nResponse: {response.text}",
            title=f"Salesforce Sync Success | Customer: {doc.name}",
        )
        return {"success": True, "response": response.text}

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            title=f"Salesforce Sync Error | Customer: {doc.name}",
        )
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def sync_customer(name):
    """Push one customer on demand -- the form's "Sync to Salesforce" button."""
    doc = frappe.get_doc("Customer", name)
    doc.check_permission("read")

    return sync_customer_to_salesforce(doc)
