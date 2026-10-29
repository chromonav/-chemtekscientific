import json

import frappe
from frappe.utils import cint, strip_html, validate_email_address


class ContactAPIError(Exception):
    """A request problem the caller can fix; carries the HTTP status to return."""

    def __init__(self, message, http_status_code=400):
        super().__init__(message)
        self.http_status_code = http_status_code


def _clean(value):
    """Strip a string; empty/whitespace-only becomes None. Non-strings pass through."""
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _split_full_name(full_name):
    """(first_name, middle_name, last_name) from a full name.

    First word is the first name, last word is the last name, anything between
    is the middle name: "Asha Patel" -> Asha / None / Patel,
    "Asha K Patel" -> Asha / K / Patel, "Asha" -> Asha / None / None.
    """
    parts = full_name.split()
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else None
    middle = " ".join(parts[1:-1]) or None
    return first, middle, last


def _ensure_contact_is_new(full_name, customer):
    """Refuse to create a Contact whose id is already taken.

    Contact ids are "<first middle last>-<customer>". Frappe silently turns a
    clash into "<id>-1", "<id>-2", ... which is how duplicates appear, so the
    id is built the same way here and a clash is a 409 that names the existing
    contact (send it as `contact` to update it instead).
    """
    contact_id = f"{' '.join(full_name.split())}-{customer.strip()}"
    existing = frappe.db.exists("Contact", contact_id)
    if existing:
        raise ContactAPIError(
            f"Contact '{existing}' already exists for this customer. "
            "Send it as `contact` to update it.",
            409,
        )



def _resolve_customer(customer, sales_force_customer_code):
    """The Customer docname the contact must be linked to.

    `customer` is the ERPNext Customer name; `sales_force_customer_code` is the
    alternative key used by the Salesforce integration (see customer_api).
    """
    if customer:
        if not frappe.db.exists("Customer", customer):
            raise ContactAPIError(f"Customer '{customer}' not found", 404)
        return customer

    if sales_force_customer_code:
        matches = frappe.get_all(
            "Customer",
            filters={"custom_salesforce_customer_code": sales_force_customer_code},
            pluck="name",
            limit=2,
        )
        if not matches:
            raise ContactAPIError(
                f"No Customer found for sales_force_customer_code '{sales_force_customer_code}'",
                404,
            )
        if len(matches) > 1:
            raise ContactAPIError(
                f"More than one Customer has sales_force_customer_code '{sales_force_customer_code}'",
                409,
            )
        return matches[0]

    raise ContactAPIError("customer or sales_force_customer_code is required")


def _load_contact_for_update(contact, customer):
    """The Contact doc to update and the Customer it is linked to.

    `customer` is optional. When given, the contact must be linked to it; when
    omitted, the contact's single Customer link is used.
    """
    if not frappe.db.exists("Contact", contact):
        raise ContactAPIError(f"Contact '{contact}' not found", 404)

    doc = frappe.get_doc("Contact", contact)
    linked = [l.link_name for l in doc.links if l.link_doctype == "Customer"]

    if customer:
        if customer not in linked:
            raise ContactAPIError(
                f"Contact '{contact}' is not linked to Customer '{customer}'", 409
            )
        return doc, customer

    if len(linked) != 1:
        raise ContactAPIError(
            f"Contact '{contact}' is linked to {len(linked)} customers; "
            "send `customer` to say which",
            409,
        )
    return doc, linked[0]


def _set_primary_email(doc, email_id):
    row = next(
        (r for r in doc.email_ids if (r.email_id or "").lower() == email_id.lower()),
        None,
    ) or doc.append("email_ids", {"email_id": email_id})

    for r in doc.email_ids:
        r.is_primary = 1 if r is row else 0


def _set_primary_number(doc, number, flag):
    """Make `number` the primary for `flag` ("is_primary_phone" or
    "is_primary_mobile_no"). One row can carry both flags, so a number sent as
    both `phone` and `mobile_no` is stored once. Contact.validate() derives the
    `phone` / `mobile_no` fields from these rows."""
    row = next((r for r in doc.phone_nos if r.phone == number), None) or doc.append(
        "phone_nos", {"phone": number}
    )

    for r in doc.phone_nos:
        r.set(flag, 1 if r is row else 0)


def _serialize(doc, customer):
    return {
        "name": doc.name,
        "full_name": doc.full_name,
        "first_name": doc.first_name,
        "middle_name": doc.middle_name,
        "last_name": doc.last_name,
        "department": doc.department,
        "email_id": doc.email_id,
        "phone": doc.phone,
        "mobile_no": doc.mobile_no,
        "link_doctype": "Customer",
        "link_name": customer,
    }


def _fail(message, http_status_code):
    frappe.local.response["http_status_code"] = http_status_code
    return {"success": False, "message": message}


CONTACT_FIELDS = frozenset(
    {
        "customer",
        "sales_force_customer_code",
        "contact",
        "full_name",
        "email_id",
        "mobile_no",
        "phone",
        "department",
    }
)


def _upsert_contact(**values):
    email_id = _clean(values.get("email_id"))
    if email_id and not validate_email_address(email_id):
        raise ContactAPIError(f"'{email_id}' is not a valid email address")

    phone = _clean(values.get("phone"))
    mobile_no = _clean(values.get("mobile_no"))

    contact = _clean(values.get("contact"))
    full_name = _clean(values.get("full_name"))
    if "full_name" in values and values["full_name"] is not None and not full_name:
        raise ContactAPIError("full_name cannot be blank")
    customer = _clean(values.get("customer"))
    sales_force_customer_code = _clean(values.get("sales_force_customer_code"))
    wants_customer = bool(customer or sales_force_customer_code)

    if contact:
        # The contact id fully identifies the record, so a customer is only
        # needed here to assert it is the expected one.
        customer = (
            _resolve_customer(customer, sales_force_customer_code) if wants_customer else None
        )
        doc, customer = _load_contact_for_update(contact, customer)
        action = "updated"
    else:
        if not full_name:
            raise ContactAPIError("full_name is required to create a Contact")
        customer = _resolve_customer(customer, sales_force_customer_code)
        _ensure_contact_is_new(full_name, customer)
        doc = frappe.new_doc("Contact")
        doc.append("links", {"link_doctype": "Customer", "link_name": customer})
        action = "created"

    # Only overwrite what the caller actually sent, so a partial update does
    # not blank out fields maintained on the ERPNext side.
    if full_name:
        doc.first_name, doc.middle_name, doc.last_name = _split_full_name(full_name)

    department = _clean(values.get("department"))
    if department is not None:
        doc.department = department

    if email_id:
        _set_primary_email(doc, email_id)
    if phone:
        _set_primary_number(doc, phone, "is_primary_phone")
    if mobile_no:
        _set_primary_number(doc, mobile_no, "is_primary_mobile_no")

    if action == "created":
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)

    return {
        "action": action,
        "message": f"Contact {action} successfully",
        "data": _serialize(doc, customer),
    }


def _error_details(error):
    if isinstance(error, ContactAPIError):
        return str(error), error.http_status_code
    if isinstance(error, (frappe.ValidationError, frappe.LinkValidationError, frappe.MandatoryError)):
        return strip_html(str(error)), 400

    frappe.log_error(frappe.get_traceback(), "Contact Upsert API Error")
    return str(error), 500


def _return_error(error):
    frappe.db.rollback()
    message, http_status_code = _error_details(error)
    return _fail(message, http_status_code)


def _upsert_batch_contact(values):
    try:
        result = _upsert_contact(**values)
        frappe.db.commit()
        return {"success": True, **result}
    except Exception as e:
        frappe.db.rollback()
        message, http_status_code = _error_details(e)
        return {"success": False, "message": message, "http_status_code": http_status_code}


def _parse_contacts(contacts):
    if isinstance(contacts, str):
        try:
            contacts = json.loads(contacts)
        except (TypeError, ValueError):
            raise ContactAPIError("contacts must be a JSON array")
    if not isinstance(contacts, list) or not contacts:
        raise ContactAPIError("contacts must be a non-empty JSON array")

    for index, values in enumerate(contacts):
        if not isinstance(values, dict):
            raise ContactAPIError(f"contacts[{index}] must be an object")
        unsupported = set(values) - CONTACT_FIELDS
        if unsupported:
            names = ", ".join(sorted(unsupported))
            raise ContactAPIError(f"contacts[{index}] has unsupported fields: {names}")
    return contacts


@frappe.whitelist(methods=["POST"])
def upsert_contact(
    customer=None,
    sales_force_customer_code=None,
    contact=None,
    full_name=None,
    email_id=None,
    mobile_no=None,
    phone=None,
    department=None,
    contacts=None,
):
    """Create or update one Contact, or process a `contacts` batch.

    A single create requires `full_name` and either `customer` or
    `sales_force_customer_code`; a single update requires `contact`. A batch
    is a non-empty JSON array of those same objects. Batch contacts are
    independent: a failure rolls back only its contact, while earlier and
    later successful contacts are committed.
    """
    if contacts is not None:
        try:
            contacts = _parse_contacts(contacts)
        except Exception as e:
            return _return_error(e)

        results = [_upsert_batch_contact(values) for values in contacts]
        return {
            "success": all(result["success"] for result in results),
            "total": len(results),
            "success_count": sum(1 for result in results if result["success"]),
            "failed_count": sum(1 for result in results if not result["success"]),
            "results": results,
        }

    try:
        result = _upsert_contact(
            customer=customer,
            sales_force_customer_code=sales_force_customer_code,
            contact=contact,
            full_name=full_name,
            email_id=email_id,
            mobile_no=mobile_no,
            phone=phone,
            department=department,
        )
        return {"success": True, **result}
    except Exception as e:
        return _return_error(e)
