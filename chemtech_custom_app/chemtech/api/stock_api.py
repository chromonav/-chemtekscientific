import frappe


def _as_list(value):
    """Accept None, a single string, a comma separated string, or a JSON list."""
    if value is None:
        return []
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        value = frappe.parse_json(value) if value.startswith("[") else value.split(",")
    return list(dict.fromkeys(str(v).strip() for v in value if v and str(v).strip()))


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_stock_balance(item_code=None, warehouse=None, company=None):
    """Return stock qty (Bin `actual_qty`, same as Stock Balance report `Balance Qty`)
    of one item in the given warehouses and/or companies.

    Args:
        item_code: Item Code incl. pack size (e.g. "PSR48553-4L").
        warehouse: Warehouse name(s) - single, comma separated string, or JSON list.
        company: Company name(s) - single, comma separated string, or JSON list.
            At least one of warehouse / company is required. If both are given,
            only warehouses that match both are counted.

    Response (inside "message"):
        {
          "item_code": "PSR48553-4L",
          "found": true,
          "total_qty": 12.0,
          "warehouses": [
            {"warehouse": "Finished Goods - PRCPL", "company": "Puresynth ...", "qty": 12.0}
          ]
        }
    """
    item_code = (item_code or "").strip()
    if not item_code:
        frappe.throw("item_code is required", frappe.ValidationError)

    warehouses = _as_list(warehouse)
    companies = _as_list(company)
    if not warehouses and not companies:
        frappe.throw("warehouse or company is required", frappe.ValidationError)

    bin_ = frappe.qb.DocType("Bin")
    wh = frappe.qb.DocType("Warehouse")
    query = (
        frappe.qb.from_(bin_)
        .inner_join(wh)
        .on(wh.name == bin_.warehouse)
        .select(bin_.warehouse, wh.company, bin_.actual_qty.as_("qty"))
        .where(bin_.item_code == item_code)
    )
    if warehouses:
        query = query.where(bin_.warehouse.isin(warehouses))
    if companies:
        query = query.where(wh.company.isin(companies))

    rows = query.run(as_dict=True)
    total = sum(r.qty or 0 for r in rows)

    return {
        "item_code": item_code,
        "found": bool(frappe.db.exists("Item", item_code)),
        "total_qty": total,
        "warehouses": [
            {"warehouse": r.warehouse, "company": r.company, "qty": r.qty or 0}
            for r in rows
        ],
    }
