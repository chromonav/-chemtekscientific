import frappe
import requests
from frappe import _
from frappe.utils import add_days, get_datetime, getdate, nowdate


ENDPOINT_PATH = "/services/apexrest/v1/pricebook-gateway"


def _push_to_salesforce(record, label):
    """POST one pricebook record to the gateway. Never raises: failures are
    logged and returned as {"success": False, "error": ...}."""

    from chemtech_custom_app.chemtech.doctype.salesforce_setting.salesforce_setting import (
        get_valid_access_token,
    )

    try:
        sf_setting = frappe.get_single("Salesforce Setting")
        instance_url = sf_setting.salesforce_url.rstrip("/")
        access_token = get_valid_access_token()

        endpoint = f"{instance_url}{ENDPOINT_PATH}"
        payload = {"records": [record]}

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
                title=f"Salesforce Sync Failed | {label}",
            )
            return {"success": False, "error": f"Status {response.status_code}: {response.text}"}

        frappe.log_error(
            message=f"Payload: {frappe.as_json(payload)}\n\nResponse: {response.text}",
            title=f"Salesforce Sync Success | {label}",
        )
        return {"success": True, "response": response.text}

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            title=f"Salesforce Sync Error | {label}",
        )
        return {"success": False, "error": str(e)}


def _is_effective(row, today):
    """True when the Item Price has started and has not expired."""
    return not (row.valid_from and getdate(row.valid_from) > today) and not (
        row.valid_upto and getdate(row.valid_upto) < today
    )


def _build_item_price_entry(row, today):
    """One Item Price row -> PricebookEntries record. Item Price has no active
    flag, so a price is active while it is within its validity window."""
    return {
        "ProductCode": row.item_code or "",
        "UnitPrice": float(row.price_list_rate or 0),
        "IsActive": _is_effective(row, today),
    }


def _resolve_modified_range(from_date, to_date):
    """(start, end) datetimes covering from_date..to_date inclusive, or None
    when no range was given. Both dates must be given together."""
    if not from_date and not to_date:
        return None
    if not (from_date and to_date):
        frappe.throw(_("Both From Date and To Date are required"))

    from_date, to_date = getdate(from_date), getdate(to_date)
    if from_date > to_date:
        frappe.throw(_("From Date cannot be after To Date"))

    # Half-open on the next midnight so the whole of To Date is included.
    return get_datetime(from_date), get_datetime(add_days(to_date, 1))


def _build_price_list_record(price_list, modified_range=None):
    """Price List + the Item Prices linked to it -> gateway record.

    With `modified_range`, only items having an Item Price modified in that
    range are sent. All Item Prices of those items are still considered, so the
    price chosen per item is the one ERPNext applies today, not merely the
    newest among the modified rows.
    """
    filters = {"price_list": price_list.name}
    if modified_range:
        start, end = modified_range
        changed_items = frappe.get_all(
            "Item Price",
            filters=[
                ["price_list", "=", price_list.name],
                ["modified", ">=", start],
                ["modified", "<", end],
            ],
            pluck="item_code",
            distinct=True,
        )
        if not changed_items:
            return {
                "Name": price_list.price_list_name or price_list.name or "",
                "IsActive": bool(price_list.enabled),
                "Description": price_list.get("custom_description") or "",
                "PricebookEntries": [],
            }
        filters["item_code"] = ["in", changed_items]

    item_prices = frappe.get_all(
        "Item Price",
        filters=filters,
        fields=["item_code", "price_list_rate", "valid_from", "valid_upto"],
        order_by="item_code asc, valid_from desc, modified desc",
    )

    # Salesforce keys an entry on ProductCode, so only one Item Price per item
    # can be sent. Item Prices pile up per item (re-entered prices, UOM or
    # validity variants); pick the one ERPNext would apply today: the newest
    # valid_from that has started and not expired. An item with no currently
    # effective price falls back to its newest row, sent as inactive.
    today = getdate(nowdate())
    chosen = {}
    for row in item_prices:
        current = chosen.get(row.item_code)
        if current is not None and _is_effective(current, today):
            continue
        if current is None or _is_effective(row, today):
            chosen[row.item_code] = row

    return {
        "Name": price_list.price_list_name or price_list.name or "",
        "IsActive": bool(price_list.enabled),
        "Description": price_list.get("custom_description") or "",
        "PricebookEntries": [_build_item_price_entry(row, today) for row in chosen.values()],
    }


SYNC_DONE_EVENT = "pricebook_sync_done"


def _sync_job_id(price_list_name):
    return f"pricebook_sync::{price_list_name}"


def _not_selling_message(price_list):
    """Why this Price List must not go to Salesforce, or None when it may.
    Only selling Price Lists are synced."""
    if not price_list.selling:
        return _("Price List {0} is not marked as Selling, so it is not synced to Salesforce.").format(
            price_list.name
        )
    return None


def run_price_list_sync(price_list_name, from_date, to_date, notify_user):
    """Background job: build the record, push it, and tell `notify_user` how it went.

    Never raises; every outcome is published on SYNC_DONE_EVENT so the form
    that started the sync can report it.
    """
    try:
        price_list = frappe.get_doc("Price List", price_list_name)
        not_selling = _not_selling_message(price_list)
        if not_selling:
            frappe.publish_realtime(
                SYNC_DONE_EVENT,
                {"price_list": price_list_name, "success": False, "error": not_selling},
                user=notify_user,
            )
            return

        record = _build_price_list_record(price_list, _resolve_modified_range(from_date, to_date))

        if from_date and not record["PricebookEntries"]:
            result = {
                "success": True,
                "synced": 0,
                "message": _("No Item Prices were modified between {0} and {1}; nothing was sent.").format(
                    from_date, to_date
                ),
            }
        else:
            result = _push_to_salesforce(record, f"Price List: {price_list.name}")
            if result.get("success"):
                result["synced"] = len(record["PricebookEntries"])
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), title=f"Salesforce Sync Error | Price List: {price_list_name}")
        result = {"success": False, "error": str(e)}

    frappe.publish_realtime(
        SYNC_DONE_EVENT,
        {"price_list": price_list_name, **result},
        user=notify_user,
    )


@frappe.whitelist()
def sync_price_list(name, from_date=None, to_date=None):
    """Queue a push of one Price List and its Item Prices — the Price List
    form's "Sync to Salesforce" button.

    `from_date`/`to_date` (inclusive) limit the push to items whose Item Price
    was modified in that range; omit both to push every Item Price.

    Returns at once with `{"queued": True}`; the outcome arrives later as a
    SYNC_DONE_EVENT realtime message to the requesting user. A sync that is
    already queued or running for the same Price List is not started twice.
    """
    price_list = frappe.get_doc("Price List", name)
    price_list.check_permission("read")

    not_selling = _not_selling_message(price_list)
    if not_selling:
        return {"success": False, "error": not_selling}

    # Reject bad dates now, while the user is still looking at the dialog.
    try:
        _resolve_modified_range(from_date, to_date)
    except frappe.ValidationError as e:
        return {"success": False, "error": str(e)}

    job = frappe.enqueue(
        "chemtech_custom_app.chemtech.custom_script.salesforce_pricebook_sync.run_price_list_sync",
        queue="long",
        job_id=_sync_job_id(price_list.name),
        deduplicate=True,
        price_list_name=price_list.name,
        from_date=from_date,
        to_date=to_date,
        notify_user=frappe.session.user,
    )
    if job is None:
        return {
            "success": False,
            "error": _("A sync for this Price List is already in progress. Try again once it finishes."),
        }

    return {"success": True, "queued": True}


@frappe.whitelist()
def preview_price_list_payload(name, from_date=None, to_date=None):
    """Return exactly what sync_price_list would POST, without sending it."""
    price_list = frappe.get_doc("Price List", name)
    price_list.check_permission("read")

    not_selling = _not_selling_message(price_list)
    if not_selling:
        return {"records": [], "message": not_selling}

    return {"records": [_build_price_list_record(price_list, _resolve_modified_range(from_date, to_date))]}
