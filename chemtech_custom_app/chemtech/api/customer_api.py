import frappe


@frappe.whitelist(methods=["POST"])
def upsert_customer(customer_name=None, account_code=None, customer_type=None, customer_group=None,
                     territory=None, gst_category=None, gstin=None, pan=None, tax_id=None,
                     mobile_no=None, email_id=None, website=None, industry=None, payment_terms=None,
                     customer_details=None, name=None):
    """
    Create or update a Customer.
    If `name` is provided, update the existing Customer with that name.
    Otherwise, create a new Customer using `customer_name`.
    Returns the document name.
    """
    if name:
        doc = frappe.get_doc("Customer", name)
        if customer_name:
            doc.customer_name = customer_name
        if account_code is not None:
            doc.account_code = account_code
        if customer_type:
            doc.customer_type = customer_type
        if customer_group is not None:
            doc.customer_group = customer_group
        if territory is not None:
            doc.territory = territory
        if gst_category is not None:
            doc.gst_category = gst_category
        if gstin is not None:
            doc.gstin = gstin
        if pan is not None:
            doc.pan = pan
        if tax_id is not None:
            doc.tax_id = tax_id
        if mobile_no is not None:
            doc.mobile_no = mobile_no
        if email_id is not None:
            doc.email_id = email_id
        if website is not None:
            doc.website = website
        if industry is not None:
            doc.industry = industry
        if payment_terms is not None:
            doc.payment_terms = payment_terms
        if customer_details is not None:
            doc.customer_details = customer_details
        doc.flags.ignore_salesforce_sync = True
        doc.save(ignore_permissions=True)
    else:
        if not customer_name:
            frappe.throw("customer_name is required to create a new Customer.")
        if not account_code:
            frappe.throw("account_code is required to create a new Customer.")
        doc = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": customer_name,
            "account_code": account_code,
            "customer_type": customer_type or "Company",
            "customer_group": customer_group or "Commercial",
            "territory": territory or "India",
            "gst_category": gst_category or "Unregistered",
            "gstin": gstin or "",
            "pan": pan or "",
            "tax_id": tax_id or "",
            "mobile_no": mobile_no or "",
            "email_id": email_id or "",
            "website": website or "",
            "industry": industry or "",
            "payment_terms": payment_terms or "",
            "customer_details": customer_details or "",
        })
        doc.flags.ignore_salesforce_sync = True
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    return {"name": doc.name}
