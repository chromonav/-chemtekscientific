import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_purchase_invoice


def validate_inter_company_transfer(doc, method=None):
	"""Block submit of a Sales Invoice to an internal customer when no Supplier is
	set up to represent this company -- the auto Purchase Invoice on submit would
	otherwise fail with the same error, after the invoice is already submitted.
	"""
	if not doc.is_internal_customer:
		return

	supplier = frappe.db.get_value(
		"Supplier",
		{"disabled": 0, "is_internal_supplier": 1, "represents_company": doc.company},
		"name",
	)
	if not supplier:
		frappe.throw(
			f"No Internal Supplier found representing company {doc.company}. "
			"Create a Supplier with 'Is Internal Supplier' checked and "
			f"'Represents Company' set to {doc.company} before submitting this invoice."
		)


def make_purchase_invoice_for_internal_customer(doc, method=None):
	"""On submit of a Sales Invoice billed to an internal customer, auto-create the
	mirror Purchase Invoice as a draft for the company the customer represents,
	with the matching internal Supplier for doc.company.

	Runs at most once per Sales Invoice: inter_company_invoice_reference is the
	same link ERPNext's own manual "Create Inter Company Purchase Invoice" button
	sets. ERPNext only back-fills that link on the Sales Invoice once the mirrored
	Purchase Invoice is itself submitted (see update_linked_doc in sales_invoice.py),
	but our Purchase Invoice is deliberately left as a draft -- so it must be set
	here, immediately, or a resubmit/amend would create a second Purchase Invoice.
	"""
	if not doc.is_internal_customer or doc.inter_company_invoice_reference:
		return

	purchase_invoice = make_inter_company_purchase_invoice(doc.name)
	# _reset_price_list_for_company(purchase_invoice)
	_reset_taxes_for_company(purchase_invoice)
	# Site-specific mandatory fields on Purchase Invoice (custom_purchase_type,
	# bill_no, bill_date) describe the supplier's own invoice paperwork, which
	# doesn't exist yet for an auto-generated draft; the user fills these in

	purchase_invoice.bill_no= doc.name
	purchase_invoice.bill_date= doc.posting_date

	purchase_invoice.insert(ignore_permissions=True, ignore_mandatory=True)

	frappe.db.set_value(
		"Sales Invoice", doc.name, "inter_company_invoice_reference", purchase_invoice.name
	)
	doc.inter_company_invoice_reference = purchase_invoice.name

	frappe.msgprint(
		f"Draft Purchase Invoice {purchase_invoice.name} auto-created for "
		f"company {purchase_invoice.company} against Supplier {purchase_invoice.supplier}.",
		alert=True,
	)


# def _reset_price_list_for_company(purchase_invoice):
# 	"""make_inter_company_transaction sets buying_price_list to the Sales
# 	Invoice's own selling_price_list (sales_invoice.py update_details) -- a
# 	Selling-side list, not a real buying one. Re-derive it the same way a
# 	manually created Purchase Invoice would: the Supplier's default_price_list,
# 	falling back to Buying Settings' default, same as set_price_list() in
# 	erpnext/accounts/party.py.
# 	"""
# 	price_list = frappe.db.get_value(
# 		"Supplier", purchase_invoice.supplier, "default_price_list"
# 	) or frappe.db.get_default("buying_price_list")
# 	if price_list and price_list != purchase_invoice.buying_price_list:
# 		purchase_invoice.buying_price_list = price_list
# 		purchase_invoice.price_list_currency = frappe.db.get_value(
# 			"Price List", price_list, "currency"
# 		)


def _reset_taxes_for_company(purchase_invoice):
	"""make_inter_company_purchase_invoice copies header and item tax fields
	verbatim from the Sales Invoice, but the draft Purchase Invoice belongs to
	a different company (the internal customer's represented company), so two
	things go stale:

	1. company_gstin is still the Sales Invoice's own GSTIN (fetched from its
	   company_address), not this Purchase Invoice's billing_address GSTIN --
	   Frappe only refreshes Link fetch_from fields on validate/insert, which
	   hasn't happened yet. India Compliance's after_mapping hook runs inside
	   make_inter_company_purchase_invoice while that stale value is still in
	   place; since it happens to equal supplier_gstin, India Compliance reads
	   it as an internal transfer with matching GSTINs and wipes
	   taxes_and_charges/taxes to empty.
	2. item_tax_template/item_tax_rate are Item Tax Template links, which are
	   scoped to a company -- the copied template belongs to the Sales
	   Invoice's company, so item_tax_rate resolves to {} (get_item_tax_map
	   filters accounts by company) and item-level taxes silently drop out.

	Fix both by correcting company_gstin before re-running India Compliance's
	GST template lookup, and by clearing the item tax fields before
	set_missing_values() re-derives them against purchase_invoice.company.
	"""
	try:
		from india_compliance.gst_india.overrides.transaction import get_gst_details
	except ImportError:
		get_gst_details = None

	if get_gst_details and purchase_invoice.get("billing_address"):
		purchase_invoice.company_gstin = frappe.db.get_value(
			"Address", purchase_invoice.billing_address, "gstin"
		)
		gst_details = get_gst_details(
			purchase_invoice.as_dict(),
			"Purchase Invoice",
			purchase_invoice.company,
			update_place_of_supply=True,
		)
		if gst_details:
			purchase_invoice.update(gst_details)

	for item in purchase_invoice.items:
		item.item_tax_template = None
		item.item_tax_rate = "{}"
	purchase_invoice.set_missing_values()
	purchase_invoice.calculate_taxes_and_totals()
