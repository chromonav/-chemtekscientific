import json

import frappe
from frappe.utils import flt, getdate, nowdate


def _as_list(value):
	"""Accept a list, a JSON string, or a single dict and return a list of dicts."""
	if not value:
		return []
	if isinstance(value, str):
		try:
			value = json.loads(value)
		except (ValueError, TypeError):
			frappe.throw("items must be a JSON array.")
	if isinstance(value, dict):
		value = [value]
	if not isinstance(value, list):
		frappe.throw("items must be a JSON array.")
	return value


def _resolve_customer(customer_name=None, current=None):
	"""Customer is keyed by name - either the document id or the customer_name field."""
	if customer_name:
		if frappe.db.exists("Customer", customer_name):
			return customer_name
		found = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
		if found:
			return found
		frappe.throw(f"No Customer found for customer_name {customer_name!r}.")
	if current:
		return current
	frappe.throw("customer_name is required.")


def _resolve_company(company_name=None, current=None):
	"""Company is keyed by name."""
	if company_name:
		if frappe.db.exists("Company", company_name):
			return company_name
		found = frappe.db.get_value("Company", {"company_name": company_name}, "name")
		if found:
			return found
		frappe.throw(f"No Company found for company_name {company_name!r}.")
	if current:
		return current
	default = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
	if default:
		return default
	frappe.throw("company_name is required.")


def _resolve_contact(contact_name=None, customer=None):
	"""
	Contact ids in ERPNext are "<full name>-<linked party>", so a contact called
	Suraj on customer ABC is the Contact "Suraj-ABC". Build that id from the
	incoming contact_name and the resolved customer.
	"""
	if not contact_name:
		return None

	contact_id = f"{contact_name}-{customer}"
	if frappe.db.exists("Contact", contact_id):
		return contact_id

	frappe.throw(
		f"Contact {contact_id!r} does not exist. Create the Contact against customer "
		f"{customer!r} first, or send an existing Contact id as contact_name."
	)


def _resolve_link(doctype, value, label):
	"""Validate a Link value up front so the error names the field, not the field id."""
	if not value:
		return None
	if not frappe.db.exists(doctype, value):
		frappe.throw(f"{label} {value!r} does not exist as a {doctype}.")
	return value


def _set_taxes(doc):
	"""
	Put a Sales Taxes and Charges Template - and its actual tax rows - on the order.

	Two things ERPNext will not do for a server-side call:
	  * it links a template but only expands it into rows from the browser form
	    (Accounts Settings > "Add Taxes From Taxes And Charges Template" is off), so
	    an API-created order would carry no GST at all;
	  * taxes_and_charges is mandatory on Sales Order on this site.

	When the caller does not name a template we work one out exactly the way the
	Sales Order form does - see _derive_taxes.
	"""
	from erpnext.controllers.accounts_controller import get_taxes_and_charges

	rows = None	
	template, rows = _derive_taxes(doc)

	if not template:
		available = frappe.get_all(
			"Sales Taxes and Charges Template",
			filters={"company": doc.company, "disabled": 0},
			pluck="name",
		)
		frappe.throw(
			f"No Sales Taxes and Charges Template could be worked out for company "
			f"{doc.company!r}, and it is mandatory on Sales Order. Map its templates to "
			"an enabled Tax Category, or mark one template as Default, or send "
			"`taxes_and_charges` in the payload. Templates on this company: "
			+ (", ".join(repr(a) for a in available) or "none configured")
		)

	doc.taxes_and_charges = template
	doc.set("taxes", [])
	for row in rows or get_taxes_and_charges("Sales Taxes and Charges Template", template):
		doc.append("taxes", row)


def _derive_taxes(doc):
	"""
	Work out the tax template the same way the Sales Order form does, in order:

	  1. India Compliance - picks In State vs Out of State from the place of supply.
	     This is the call the form makes when the customer or address changes, and it
	     hands back the tax rows too.
	  2. ERPNext party defaults - Tax Rule, then the customer's Tax Category.
	  3. The template marked Default on the company.

	Returns (template_name, rows) - rows may be None, in which case the caller
	expands the template itself.
	"""
	from erpnext.accounts.party import get_party_details

	party = get_party_details(
		party=doc.customer,
		party_type="Customer",
		company=doc.company,
		doctype="Sales Order",
		posting_date=doc.transaction_date,
		ignore_permissions=True,
	) or {}

	if not doc.customer_address and party.get("customer_address"):
		doc.customer_address = party.get("customer_address")

	# 1. India Compliance, state aware
	gst = _get_gst_details(doc, party)
	if gst.get("place_of_supply"):
		doc.place_of_supply = gst["place_of_supply"]
	if gst.get("taxes_and_charges"):
		return gst["taxes_and_charges"], gst.get("taxes")

	# 2. ERPNext party defaults
	if party.get("taxes_and_charges"):
		return party["taxes_and_charges"], party.get("taxes")

	# 3. company default
	default = frappe.db.get_value(
		"Sales Taxes and Charges Template",
		{"is_default": 1, "company": doc.company, "disabled": 0},
		"name",
	)
	if default:
		return default, None

	return None, None


def _get_gst_details(doc, party):
	"""Ask India Compliance which GST template the form would pick. {} if unavailable."""
	try:
		from india_compliance.gst_india.overrides.transaction import get_gst_details
	except ImportError:
		return {}

	address = doc.customer_address or party.get("customer_address")

	return (
		get_gst_details(
			{
				"customer": doc.customer,
				"customer_address": address,
				"party_address": address,
				"company_gstin": party.get("company_gstin"),
				"company_address": party.get("company_address"),
				"billing_address_gstin": party.get("billing_address_gstin"),
				"gst_category": party.get("gst_category"),
			},
			"Sales Order",
			doc.company,
			update_place_of_supply=True,
		)
		or {}
	)


def _find_sales_order(name=None, custom_sales_order_salesforce_=None):
	"""Locate an existing Sales Order by ERPNext name or by the Salesforce key."""
	if name:
		if not frappe.db.exists("Sales Order", name):
			frappe.throw(f"Sales Order {name} does not exist.")
		return name

	if custom_sales_order_salesforce_:
		return frappe.db.get_value(
			"Sales Order",
			{"custom_sales_order_salesforce_": custom_sales_order_salesforce_, "docstatus": ["<", 2]},
			"name",
			order_by="creation desc",
		)

	return None


def _set_items(doc, items):
	"""
	Replace the items table from {"item_code", "qty", "rate", "discount_percentage"}.
	ERPNext fetches item_name, uom, hsn, item_tax_template and taxes on validate.

	When a discount is sent, the price given is treated as the list price and `rate`
	is left blank so ERPNext computes the discounted rate itself.
	"""
	if not items:
		frappe.throw("At least one item is required.")

	doc.set("items", [])
	for row in items:
		item_code = row.get("item_code")
		if not item_code:
			frappe.throw("item_code is required for every item.")
		if not frappe.db.exists("Item", item_code):
			frappe.throw(f"Item {item_code} does not exist.")

		qty = flt(row.get("qty"))
		if qty <= 0:
			frappe.throw(f"qty must be greater than zero for item {item_code}.")

		line = {"item_code": item_code, "qty": qty}
		if row.get("delivery_date"):
			line["delivery_date"] = getdate(row.get("delivery_date"))
		if row.get("warehouse"):
			line["warehouse"] = row.get("warehouse")

		rate = row.get("rate")
		price_list_rate = row.get("price_list_rate")
		discount = flt(row.get("discount_percentage"))

		if discount < 0 or discount > 100:
			frappe.throw(f"discount_percentage must be between 0 and 100 for item {item_code}.")

		if discount:
			# ERPNext derives rate = price_list_rate x (1 - discount%), and only does so
			# while `rate` is still blank (see erpnext/controllers/taxes_and_totals.py).
			# So the price we are given is the list price, and rate is left for ERPNext.
			list_price = price_list_rate if price_list_rate not in (None, "") else rate
			if list_price not in (None, ""):
				line["price_list_rate"] = flt(list_price)
			line["discount_percentage"] = discount
		else:
			if price_list_rate not in (None, ""):
				line["price_list_rate"] = flt(price_list_rate)
			if rate not in (None, ""):
				line["rate"] = flt(rate)

		doc.append("items", line)


@frappe.whitelist(methods=["POST"])
def upsert_sales_order(
	custom_sales_order_salesforce_=None,
	name=None,
	customer_name=None,
	company_name=None,
	contact_name=None,
	branch_name=None,
	quote_id=None,
	opportunity_id=None,
	payment_terms=None,
	order_start_date=None,
	delivery_date=None,
	activation_date=None,
	activated_by=None,
	stock_delivery=None,
	validity=None,
	availability=None,
	description=None,
	sales_person=None,
	set_warehouse=None,
	items=None,
):
	"""
	Create or update a draft Sales Order from a Salesforce Order payload.

	`custom_sales_order_salesforce_` is the Salesforce Order key and is what makes
	this call idempotent: the first call creates the Sales Order and stores the key
	on it, every later call with the same key updates that same document.

	`customer_name` and `company_name` are the business keys - the Customer and
	Company are looked up by name, not by account code or abbreviation.

	`contact_name` is the person's name; the Contact id is built as
	"<contact_name>-<customer>" the way ERPNext names Contacts.

	`order_start_date` maps to the Sales Order date. `delivery_date` falls back to it
	when omitted, since ERPNext requires one.

	`taxes_and_charges` is a Sales Taxes and Charges Template name. Pass it to get GST
	rows: ERPNext only expands a template into tax rows in the browser form, so a
	server-side call produces no tax unless we expand it here.

	`items` is a list of {"item_code", "qty", "rate", "discount_percentage"}. Item
	name, UOM, HSN, item tax template and all totals are left to ERPNext.

	Returns the document name.
	"""
	if not (custom_sales_order_salesforce_ or name):
		frappe.throw("custom_sales_order_salesforce_ is required.")

	items = _as_list(items)
	target = _find_sales_order(name, custom_sales_order_salesforce_)

	if target:
		doc = frappe.get_doc("Sales Order", target)
		if doc.docstatus != 0:
			frappe.throw(f"Sales Order {doc.name} is not a draft and cannot be updated.")
	else:
		doc = frappe.new_doc("Sales Order")

	if custom_sales_order_salesforce_:
		doc.custom_sales_order_salesforce_ = custom_sales_order_salesforce_

	# On a new doc frappe pre-fills company from the user default, so the document's
	# own value must never outrank an explicit company_name from the caller.
	current = None if doc.is_new() else doc
	previous_customer = current and current.customer
	previous_company = current and current.company
	doc.customer = _resolve_customer(customer_name, previous_customer)
	doc.company = _resolve_company(company_name, previous_company)

	if previous_customer and previous_customer != doc.customer:
		# Addresses and contact belong to the party that was on the order before.
		# Leaving them attached fails validation with "Billing Address does not
		# belong to <customer>", so clear them and let the new party's details load.
		for field in (
			"customer_address",
			"address_display",
			"shipping_address_name",
			"shipping_address",
			"contact_person",
			"contact_display",
			"contact_email",
			"contact_mobile",
			"contact_phone",
		):
			doc.set(field, None)

	if previous_company and previous_company != doc.company:
		# Same story for the selling company: its address, GSTIN, warehouse and tax
		# template all belong to the company that was on the order before.
		for field in (
			"company_address",
			"company_address_display",
			"company_gstin",
			"company_contact_person",
			"set_warehouse",
			"taxes_and_charges",
			"cost_center",
		):
			doc.set(field, None)
		doc.set("taxes", [])

	doc.transaction_date = getdate(
		order_start_date or doc.transaction_date or nowdate()
	)
	# ERPNext makes delivery_date mandatory on a Sales order - fall back to the order date.
	doc.delivery_date = getdate(delivery_date or doc.delivery_date or doc.transaction_date)

	contact_person = _resolve_contact(contact_name, doc.customer)
	if contact_person:
		doc.contact_person = contact_person

	if branch_name:
		doc.custom_branch = _resolve_link("Branch", branch_name, "branch_name")
	if payment_terms:
		doc.payment_terms_template = _resolve_link(
			"Payment Terms Template", payment_terms, "payment_terms"
		)
	if sales_person:
		doc.sales_person = _resolve_link("Sales Person", sales_person, "sales_person")
	if set_warehouse:
		doc.set_warehouse = _resolve_link("Warehouse", set_warehouse, "set_warehouse")

	if opportunity_id:
		doc.custom_opportunity_salesforce = opportunity_id
	if quote_id:
		doc.custom_quote_salesforce = quote_id
	if activation_date:
		doc.custom_activate_date = getdate(activation_date)
	if activated_by:
		doc.custom_activated_by = activated_by
	if stock_delivery:
		doc.custom_stock_delivery = stock_delivery
	if validity:
		doc.custom_validity = validity
	if availability:
		doc.custom_availability = availability
	if description:
		doc.custom_description = description

	_set_taxes(doc)

	if items or doc.is_new():
		_set_items(doc, items)

	doc.flags.ignore_salesforce_sync = True
	was_new = doc.is_new()
	if was_new:
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)

	frappe.db.commit()

	action = "created" if was_new else "updated"
	return {
		"success": True,
		"action": action,
		"message": f"Sales Order {doc.name} {action} successfully.",
		"name": doc.name,
		"custom_sales_order_salesforce_": doc.get("custom_sales_order_salesforce_"),
		"customer": doc.customer,
		"company": doc.company,
		"docstatus": doc.docstatus,
		"status": doc.status,
		"taxes_and_charges": doc.taxes_and_charges,
		"place_of_supply": doc.get("place_of_supply"),
		"net_total": flt(doc.net_total),
		"total_taxes_and_charges": flt(doc.total_taxes_and_charges),
		"grand_total": flt(doc.grand_total),
	}


@frappe.whitelist(methods=["POST"])
def submit_sales_order(custom_sales_order_salesforce_=None, name=None):
	"""Submit a draft Sales Order, found by Salesforce key or ERPNext name."""
	target = _find_sales_order(name, custom_sales_order_salesforce_)
	if not target:
		frappe.throw("Sales Order not found.")

	doc = frappe.get_doc("Sales Order", target)
	if doc.docstatus == 0:
		doc.flags.ignore_salesforce_sync = True
		doc.submit()
		frappe.db.commit()
	return {
		"success": True,
		"action": "submitted",
		"message": f"Sales Order {doc.name} submitted successfully.",
		"name": doc.name,
		"docstatus": doc.docstatus,
		"status": doc.status,
		"grand_total": flt(doc.grand_total),
	}


@frappe.whitelist(methods=["POST"])
def cancel_sales_order(custom_sales_order_salesforce_=None, name=None):
	"""Cancel a submitted Sales Order, found by Salesforce key or ERPNext name."""
	target = _find_sales_order(name, custom_sales_order_salesforce_)
	if not target:
		frappe.throw("Sales Order not found.")

	doc = frappe.get_doc("Sales Order", target)
	if doc.docstatus == 1:
		doc.flags.ignore_salesforce_sync = True
		doc.cancel()
		frappe.db.commit()
	return {
		"success": True,
		"action": "cancelled",
		"message": f"Sales Order {doc.name} cancelled successfully.",
		"name": doc.name,
		"docstatus": doc.docstatus,
		"status": doc.status,
	}
