def set_account_code(doc, method):
    customer_name = doc.customer_name or ""
    state = doc.custom_state or ""

    doc.account_code = (
        customer_name[:3].upper()
        + state[:3].upper()
    )