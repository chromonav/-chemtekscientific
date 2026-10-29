import frappe


def validate_unique_contact(doc, method=None):
    """Refuse a new Contact whose id is already taken.

    Contact.autoname builds "<first middle last>-<first linked party>" and, on a
    clash, silently appends "-1", "-2", ... which is how duplicate contacts
    appear. Naming happens after before_insert, so the id is predicted the same
    way here and a clash is rejected instead of suffixed.
    """
    name = doc._get_full_name()
    if not name:
        return

    for link in doc.links:
        name = f"{name}-{link.link_name.strip()}"
        break

    existing = frappe.db.exists("Contact", name)
    if existing:
        frappe.throw(
            f"Contact {existing!r} already exists. Open it and edit it instead of "
            "creating a duplicate.",
            title="Duplicate Contact",
        )
