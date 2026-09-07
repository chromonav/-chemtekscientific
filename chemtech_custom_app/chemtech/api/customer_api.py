import frappe

from india_compliance.gst_india.constants import STATE_NUMBERS


# Mandatory on Address here; address_line2 is made required by a Property
# Setter on this site, so it counts even though stock ERPNext leaves it optional.
ADDRESS_REQUIRED = ("address_line1", "address_line2", "city", "country")


def _normalize_state(state):
    """Match a state name to india_compliance's canonical spelling.

    Addresses in India are rejected outright unless the state is one of the 38
    known names, so a near-miss from Salesforce is corrected here rather than
    surfacing as a validation error further down.
    """
    if not state:
        return None

    cleaned = str(state).strip()
    for canonical in STATE_NUMBERS:
        if canonical.lower() == cleaned.lower():
            return canonical

    return cleaned


def _find_address(customer, address_type):
    """The customer's existing address of this type, or None."""
    linked = frappe.get_all(
        "Dynamic Link",
        filters={
            "link_doctype": "Customer",
            "link_name": customer,
            "parenttype": "Address",
        },
        pluck="parent",
    )
    if not linked:
        return None

    return frappe.db.get_value(
        "Address", {"name": ["in", linked], "address_type": address_type}, "name"
    )


def _upsert_address(customer_doc, address_type, values):
    """Create or update one address for the customer.

    Returns a short status string so the caller can report what happened, since
    an incomplete address is skipped rather than failing the whole upsert.
    """
    values = {k: v for k, v in values.items() if v is not None}
    if not any(str(v).strip() for v in values.values()):
        return "not provided"

    values["state"] = _normalize_state(values.get("state"))
    if values.get("state") in STATE_NUMBERS and not values.get("country"):
        values["country"] = "India"

    existing = _find_address(customer_doc.name, address_type)

    if existing:
        doc = frappe.get_doc("Address", existing)
    else:
        doc = frappe.new_doc("Address")
        doc.address_type = address_type
        doc.address_title = customer_doc.customer_name
        doc.append("links", {"link_doctype": "Customer", "link_name": customer_doc.name})

    for fieldname, value in values.items():
        doc.set(fieldname, value)

    missing = [f for f in ADDRESS_REQUIRED if not doc.get(f)]
    if missing:
        # Salesforce sends state-only addresses, which cannot form a valid
        # Address. Skip it instead of rejecting the customer.
        return f"skipped, missing {', '.join(missing)}"

    doc.flags.ignore_salesforce_sync = True
    doc.save(ignore_permissions=True) if existing else doc.insert(ignore_permissions=True)
    return "updated" if existing else "created"


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


def _split_street(street):
    """Salesforce sends one Street textarea; ERPNext wants two lines."""
    if not street:
        return None, None

    lines = [ln.strip() for ln in str(street).splitlines() if ln.strip()]
    if not lines:
        return None, None

    return lines[0], " ".join(lines[1:]) or None


@frappe.whitelist(methods=["POST"])
def upsert_customer(
    sales_force_customer_code=None,
    customer_name=None,
    city=None,
    customer_type=None,
    customer_group=None,
    territory=None,
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
    billing_street=None,
    billing_city=None,
    billing_state=None,
    billing_postal_code=None,
    billing_country=None,
    shipping_street=None,
    shipping_city=None,
    shipping_state=None,
    shipping_postal_code=None,
    shipping_country=None,
):
    """Create or update a Customer keyed on the Salesforce customer code.

    `sales_force_customer_code` is the match key and is stored on the Customer.
    A city is required because the ERPNext account code is derived from the
    customer name and city; it can come from `city` or, failing that,
    `billing_city`. The generated account code is returned so Salesforce can
    store it.

    Billing and shipping addresses are written to linked Address records.
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
        # Salesforce puts the city on the billing address, so accept it there.
        resolved_city = (city or billing_city or "").strip()
        if resolved_city:
            doc.custom_city = resolved_city
        elif not doc.get("custom_city"):
            # Also catches an existing customer that predates the field, which
            # would otherwise fail with a bare mandatory-field error on save.
            frappe.throw("city (or billing_city) is required to create a new Customer")

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
        }
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

        addresses = {
            "billing": _upsert_address(doc, "Billing", {
                "address_line1": _split_street(billing_street)[0],
                "address_line2": _split_street(billing_street)[1],
                "city": billing_city,
                "state": billing_state,
                "pincode": billing_postal_code,
                "country": billing_country,
            }),
            "shipping": _upsert_address(doc, "Shipping", {
                "address_line1": _split_street(shipping_street)[0],
                "address_line2": _split_street(shipping_street)[1],
                "city": shipping_city,
                "state": shipping_state,
                "pincode": shipping_postal_code,
                "country": shipping_country,
            }),
        }

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
                "addresses": addresses,
            },
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Customer Upsert API Error")
        return {"success": False, "message": str(e)}
