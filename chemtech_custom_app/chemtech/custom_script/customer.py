import frappe


def _holder_of(code, exclude=None):
    """The customer already using this account code, if any."""
    filters = {"account_code": code}
    if exclude:
        filters["name"] = ["!=", exclude]
    return frappe.db.get_value("Customer", filters, "name")


def generate_account_code(customer_name, city, exclude=None):
    """First three letters of the name plus the city.

    Exactly one customer may hold a given code -- Salesforce stores it as its
    handle on the ERPNext customer, so a clash is rejected rather than worked
    around with a numeric suffix.
    """
    # Strip anything non-alphanumeric first: "3p Instrument" must not yield a
    # code with a space in it, since Salesforce stores this as a key.
    name_part = "".join(c for c in (customer_name or "") if c.isalnum())
    city_part = "".join(c for c in (city or "") if c.isalnum())

    code = (name_part[:3] + city_part[:3]).upper()
    if not code:
        frappe.throw(
            "Cannot build an account code without a customer name or city.",
            title="Account Code Required",
        )

    holder = _holder_of(code, exclude)
    if holder:
        frappe.throw(
            f"Account code {code} is already used by customer {holder}. "
            "Change the customer name or city so the code differs.",
            title="Duplicate Account Code",
        )

    return code


def set_account_code(doc, method=None):
    # Generated once and then left alone: the code is an external identifier,
    # so renaming a customer must not move it to a different value.
    if doc.account_code:
        return

    doc.account_code = generate_account_code(
        doc.customer_name, doc.get("custom_city"), exclude=doc.name
    )
