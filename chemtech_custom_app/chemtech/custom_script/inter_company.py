import re

import frappe
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_purchase_invoice
from erpnext.accounts.party import get_party_account
from frappe.utils import getdate


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
	purchase_invoice.custom_purchase_type= "Operational Purchase"
	_apply_prefix_rule(purchase_invoice)

	purchase_invoice.insert(ignore_permissions=True)
	purchase_invoice.submit()

	frappe.db.set_value(
		"Sales Invoice", doc.name, "inter_company_invoice_reference", purchase_invoice.name
	)
	doc.inter_company_invoice_reference = purchase_invoice.name

	frappe.msgprint(
		f"Submitted Purchase Invoice {purchase_invoice.name} auto-created for "
		f"company {purchase_invoice.company} against Supplier {purchase_invoice.supplier}.",
		alert=True,
	)


def _apply_prefix_rule(purchase_invoice):
	"""Server-side port of the 'Purchase Invoice Prefix Code' client script.

	The Prefix Rule lookup normally runs in the browser (onload / field change),
	which never happens for a Purchase Invoice built in Python. Without it, the
	mapped document keeps the Sales Invoice's custom_prefix and falls back to the
	default PINV-.YY.- series. Resolve the matching Prefix Rule for the PI's own
	company and set custom_prefix + naming_series exactly as the form would.
	"""
	rules = frappe.get_all(
		"Prefix Rule",
		filters={"document_type": "Purchase Invoice", "disabled": 0},
		fields=["name", "prefix"],
	)

	matches = []
	for rule in rules:
		conditions = frappe.get_all(
			"Prefix Condition",
			filters={"parent": rule.name, "parenttype": "Prefix Rule"},
			fields=["field", "value"],
		)
		if all(str(purchase_invoice.get(c.field)) == str(c.value) for c in conditions):
			matches.append((len(conditions), rule))

	if not matches:
		frappe.throw(
			f"No Prefix Rule matches the auto-created Purchase Invoice for company "
			f"{purchase_invoice.company}. Add a Prefix Rule for Purchase Invoice."
		)

	top = max(count for count, _ in matches)
	winners = [rule for count, rule in matches if count == top]
	if len(winners) > 1:
		frappe.throw(
			"Multiple Prefix Rules match the auto-created Purchase Invoice with the same "
			"specificity: " + ", ".join(rule.name for rule in winners)
		)

	prefix = _expand_prefix(winners[0].prefix, purchase_invoice)
	purchase_invoice.custom_prefix = prefix
	purchase_invoice.naming_series = prefix


def _expand_prefix(prefix, doc):
	"""Expand {field:fy|FY|YYYY|YY|MM|DD} placeholders (April-March financial year),
	mirroring expand_prefix() in the client script."""

	def replace(match):
		field, kind = match.group(1), match.group(2)
		value = doc.get(field)
		if not value:
			return match.group(0)
		d = getdate(value)
		fy_start = d.year if d.month >= 4 else d.year - 1
		return {
			"fy": f"{fy_start % 100:02d}-{(fy_start + 1) % 100:02d}",
			"FY": f"{fy_start}-{(fy_start + 1) % 100:02d}",
			"YYYY": str(d.year),
			"YY": f"{d.year % 100:02d}",
			"MM": f"{d.month:02d}",
			"DD": f"{d.day:02d}",
		}[kind]

	return re.sub(r"\{(\w+):(fy|FY|YYYY|YY|MM|DD)\}", replace, prefix)


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


@frappe.whitelist()
def make_inter_company_payment_entry(source_name):
	"""Create the mirror Payment Entry, as a draft, in the other company of an
	inter-company payment.

	Pay to an internal Supplier  -> Receive from the internal Customer, in the
	                                company the Supplier represents.
	Receive from an internal Customer -> Pay to the internal Supplier, in the
	                                company the Customer represents.

	Invoices allocated on the source are swapped for their inter-company
	counterpart (Purchase Invoice <-> Sales Invoice). The new entry points back to
	the source through custom_inter_company_payment_entry, which also blocks a
	second mirror entry for the same source.
	"""
	source = frappe.get_doc("Payment Entry", source_name)
	source.check_permission("read")
	frappe.has_permission("Payment Entry", "create", throw=True)

	if source.docstatus != 1:
		frappe.throw(f"Payment Entry {source.name} must be submitted first.")
	if source.get("custom_inter_company_payment_entry"):
		frappe.throw(f"Payment Entry {source.name} is itself an inter-company mirror entry.")

	if (source.payment_type, source.party_type) == ("Pay", "Supplier"):
		internal_flag, counter_type, counter_party_type = "is_internal_supplier", "Receive", "Customer"
	elif (source.payment_type, source.party_type) == ("Receive", "Customer"):
		internal_flag, counter_type, counter_party_type = "is_internal_customer", "Pay", "Supplier"
	else:
		frappe.throw("Only Pay to a Supplier or Receive from a Customer can be mirrored.")

	existing = frappe.db.get_value(
		"Payment Entry",
		{"custom_inter_company_payment_entry": source.name, "docstatus": ["<", 2]},
		"name",
	)
	if existing:
		frappe.throw(f"Inter-company Payment Entry {existing} already exists for {source.name}.")

	party = frappe.db.get_value(
		source.party_type, source.party, [internal_flag, "represents_company"], as_dict=True
	)
	if not party[internal_flag] or not party.represents_company:
		frappe.throw(
			f"{source.party_type} {source.party} is not an internal {source.party_type.lower()} "
			"representing a company."
		)
	counter_company = party.represents_company

	references = []
	counter_party = None
	for row in source.references:
		invoice = _counterpart_invoice(row, counter_company)
		counter_party = counter_party or invoice.party
		references.append(
			{
				"reference_doctype": invoice.doctype,
				"reference_name": invoice.name,
				"allocated_amount": row.allocated_amount,
			}
		)

	if not counter_party:
		counter_party = _internal_party(counter_party_type, source.company)

	bank_account, mode_of_payment = _counter_bank_account(source, counter_company)
	party_account = get_party_account(counter_party_type, counter_party, counter_company)

	receive = counter_type == "Receive"
	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = counter_type
	pe.company = counter_company
	pe.posting_date = source.posting_date
	pe.mode_of_payment = mode_of_payment
	pe.party_type = counter_party_type
	pe.party = counter_party
	pe.paid_from = party_account if receive else bank_account
	pe.paid_to = bank_account if receive else party_account
	pe.paid_amount = pe.received_amount = source.paid_amount
	# A Bank-type account makes these mandatory; the source's own details are the
	# best available values for the same money movement.
	pe.reference_no = source.reference_no or source.name
	pe.reference_date = source.reference_date or source.posting_date
	pe.custom_inter_company_payment_entry = source.name
	pe.naming_series = _payment_naming_series(counter_type, source.posting_date) or pe.naming_series
	for reference in references:
		pe.append("references", reference)

	pe.insert()
	return pe.name


def _counterpart_invoice(row, counter_company):
	"""Inter-company counterpart of one Payment Entry Reference row."""
	if row.reference_doctype == "Purchase Invoice":
		counter_doctype, party_field = "Sales Invoice", "customer"
		counter_name = frappe.db.get_value(
			"Purchase Invoice", row.reference_name, "inter_company_invoice_reference"
		)
	elif row.reference_doctype == "Sales Invoice":
		counter_doctype, party_field = "Purchase Invoice", "supplier"
		counter_name = frappe.db.get_value(
			"Sales Invoice", row.reference_name, "inter_company_invoice_reference"
		) or frappe.db.get_value(
			"Purchase Invoice",
			{"inter_company_invoice_reference": row.reference_name, "docstatus": 1},
			"name",
		)
	else:
		frappe.throw(
			f"{row.reference_doctype} {row.reference_name} has no inter-company counterpart. "
			"Only Purchase Invoice and Sales Invoice references can be mirrored."
		)

	if not counter_name:
		frappe.throw(
			f"{row.reference_doctype} {row.reference_name} has no inter-company "
			f"{counter_doctype} linked to it."
		)

	counter = frappe.db.get_value(
		counter_doctype, counter_name, ["docstatus", "company", party_field], as_dict=True
	)
	if counter.docstatus != 1:
		frappe.throw(f"{counter_doctype} {counter_name} is not submitted.")
	if counter.company != counter_company:
		frappe.throw(
			f"{counter_doctype} {counter_name} belongs to {counter.company}, "
			f"expected {counter_company}."
		)

	return frappe._dict(doctype=counter_doctype, name=counter_name, party=counter.get(party_field))


def _internal_party(party_type, represents_company):
	"""Internal Customer/Supplier representing `represents_company`, for a Payment
	Entry that has no invoice to take the party from (an advance)."""
	flag = "is_internal_customer" if party_type == "Customer" else "is_internal_supplier"
	party = frappe.db.get_value(
		party_type,
		{flag: 1, "represents_company": represents_company, "disabled": 0},
		"name",
	)
	if not party:
		frappe.throw(
			f"No internal {party_type} found that represents company {represents_company}."
		)
	return party


def _counter_bank_account(source, company):
	"""Bank/cash account of `company` for the mirror entry: the source's Mode of
	Payment when it has an account for this company, else the company default
	Bank, else the default Cash."""
	mode_of_payment = source.mode_of_payment
	account = None
	if mode_of_payment:
		account = frappe.db.get_value(
			"Mode of Payment Account",
			{"parent": mode_of_payment, "company": company},
			"default_account",
		)
	if not account:
		mode_of_payment = None
		default = get_default_bank_cash_account(company, "Bank") or get_default_bank_cash_account(
			company, "Cash"
		)
		account = default and default.get("account")
	if not account:
		frappe.throw(f"Set a default Bank or Cash account on company {company}.")
	return account, mode_of_payment


def _payment_naming_series(payment_type, posting_date):
	"""ACC-REC-/ACC-PAY- series of the posting date's April-March financial year,
	if it is one of Payment Entry's naming series options."""
	date = getdate(posting_date)
	start = date.year if date.month >= 4 else date.year - 1
	series = f"ACC-{'REC' if payment_type == 'Receive' else 'PAY'}-{start % 100:02d}-{(start + 1) % 100:02d}-"
	options = (frappe.get_meta("Payment Entry").get_field("naming_series").options or "").split("\n")
	return series if series in options else None
