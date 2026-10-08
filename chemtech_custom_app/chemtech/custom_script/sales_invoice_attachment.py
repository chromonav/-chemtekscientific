import frappe

# Attachment Type (child row) -> Sales Invoice status field
STATUS_FIELDS = {
    "POD": "custom_pod_status",
    "GRN": "custom_grn_status",
}


def update_attachment_status(doc, method=None):
    """Set each row's status from its file, then roll up per attachment type.

    A parent status is "Yes" only when at least one row of that type exists and
    every row of that type has an attachment. Otherwise "No".
    """
    rows_by_type = {attachment_type: [] for attachment_type in STATUS_FIELDS}

    for row in doc.get("custom_attachments") or []:
        row.status = "Attached" if row.attachment else "Not Attached"
        if row.attachment_type in rows_by_type:
            rows_by_type[row.attachment_type].append(row)

    for attachment_type, fieldname in STATUS_FIELDS.items():
        rows = rows_by_type[attachment_type]
        all_attached = bool(rows) and all(r.status == "Attached" for r in rows)
        doc.set(fieldname, "Yes" if all_attached else "No")
