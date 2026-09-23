import frappe


def _holder_of(code, exclude=None):
    """The customer already using this account code, if any."""
    filters = {"account_code": code}
    if exclude:
        filters["name"] = ["!=", exclude]
    return frappe.db.get_value("Customer", filters, "name")


def generate_account_code(customer_name, city, exclude=None):
    """Generate account code based on customer name and city.

    Customer name rules:
    1. 3 or more words:
       - First letter of first 3 words.
       - Ignore the 4th and subsequent words.
       Example: "ABC Trading Private Limited" -> ATP

    2. 2 words:
       - First 2 letters of first word.
       - First 1 letter of second word.
       Example: "ABC Traders" -> ABT

    3. 1 word:
       - First 3 letters of the word.
       Example: "ABC" -> ABC
    """

    # Split customer name into words and remove non-alphanumeric
    # characters from each word.
    words = [
        "".join(c for c in word if c.isalnum())
        for word in (customer_name or "").split()
    ]
    words = [word for word in words if word]

    if len(words) >= 3:
        # First letter from first three words
        name_part = "".join(word[0] for word in words[:3])

    elif len(words) == 2:
        # First 2 letters from first word + first letter from second word
        name_part = words[0][:2] + words[1][:1]

    elif len(words) == 1:
        # First 3 letters from the only word
        name_part = words[0][:3]

    else:
        name_part = ""

    # First 3 letters of city
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
