import frappe


def _find_customer(sales_force_customer_code, customer_name=None):
    """Locate the Customer this Salesforce record refers to.

    Matches on the Salesforce code first. Failing that, an existing customer of
    the same name that has never been stamped with a code is adopted, so a
    record that predates the integration is linked rather than duplicated.
    """
    match = frappe.db.get_value(
        "Customer",
        {"custom_salesforce_customer_code": sales_force_customer_code},
        "name",
    )
    if match:
        return match, False

    if customer_name:
        unclaimed = frappe.db.get_value(
            "Customer",
            {
                "customer_name": customer_name,
                # "is not set" resolves to ifnull(...)='' -- an IN list would
                # never match the NULL that untouched customers carry.
                "custom_salesforce_customer_code": ["is", "not set"],
            },
            "name",
        )
        if unclaimed:
            return unclaimed, True

    return None, False


@frappe.whitelist(methods=["POST"])
def upsert_customer(
    sales_force_customer_code=None,
    customer_name=None,
    city=None,
    customer_type=None,
    customer_group=None,
    territory=None,
    disabled=None,
    gst_category=None,
    gstin=None,
    account_type=None,
    pan=None,
    tax_id=None,
    mobile_no=None,
    email_id=None,
    website=None,
    industry=None,
    payment_terms=None,
    customer_details=None,
    fax=None,
    salesforce_address=None,
):
    """Create or update a Customer keyed on the Salesforce customer code.

    `sales_force_customer_code` is the match key and is stored on the Customer.
    A city is required because the ERPNext account code is derived from the
    customer name and city. The generated account code is returned so Salesforce
    can store it.

    `salesforce_address` is stored on the Customer as a single Small Text field.
    """
    try:
        if not sales_force_customer_code:
            frappe.throw("sales_force_customer_code is required")

        sales_force_customer_code = str(sales_force_customer_code).strip()
        existing, adopted = _find_customer(sales_force_customer_code, customer_name)

        if existing:
            doc = frappe.get_doc("Customer", existing)
            action = "adopted" if adopted else "updated"
            if adopted:
                doc.custom_salesforce_customer_code = sales_force_customer_code
        else:
            if not customer_name:
                frappe.throw("customer_name is required to create a new Customer")
            doc = frappe.new_doc("Customer")
            doc.custom_salesforce_customer_code = sales_force_customer_code
            action = "created"

        # custom_city is mandatory on the doctype and feeds the account code, so
        # a create must carry it; an update may leave the stored one alone.
        resolved_city = (city or "").strip()
        if resolved_city:
            doc.custom_city = resolved_city
        elif not doc.get("custom_city"):
            # Also catches an existing customer that predates the field, which
            # would otherwise fail with a bare mandatory-field error on save.
            frappe.throw("city is required to create a new Customer")

        if customer_name:
            doc.customer_name = customer_name

        # Only overwrite what the caller actually sent, so a partial update does
        # not blank out fields maintained on the ERPNext side.
        optional = {
            "customer_type": customer_type,
            "customer_group": customer_group,
            "territory": territory,
            "gst_category": gst_category,
            "custom_account_type": account_type,
            "gstin": gstin,
            "pan": pan,
            "tax_id": tax_id,
            "mobile_no": mobile_no,
            "email_id": email_id,
            "website": website,
            "industry": industry,
            "payment_terms": payment_terms,
            "customer_details": customer_details,
            "custom_fax": fax,
            "custom_salesforce_address": salesforce_address,
        }
        if disabled is not None:
            optional["disabled"] = frappe.utils.cint(disabled)

        for fieldname, value in optional.items():
            if value is not None:
                doc.set(fieldname, value)

        if action == "created":
            doc.customer_type = doc.customer_type or "Company"
            doc.customer_group = doc.customer_group or "Commercial"
            doc.territory = doc.territory or "India"

        # The record originated in Salesforce; pushing it straight back would be
        # an echo of what they just sent us.
        doc.flags.ignore_salesforce_sync = True

        if action == "created":
            doc.insert(ignore_permissions=True)
        else:
            doc.save(ignore_permissions=True)

        frappe.db.commit()

        return {
            "success": True,
            "message": f"Customer {action} successfully",
            "action": action,
            "data": {
                "name": doc.name,
                "account_code": doc.account_code,
                "customer_name": doc.customer_name,
                "sales_force_customer_code": doc.custom_salesforce_customer_code,
                "city": doc.custom_city,
                "salesforce_address": doc.get("custom_salesforce_address"),
            },
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Customer Upsert API Error")
        return {"success": False, "message": str(e)}
