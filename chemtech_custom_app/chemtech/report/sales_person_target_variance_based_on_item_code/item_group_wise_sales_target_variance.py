# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _

from erpnext.accounts.doctype.monthly_distribution.monthly_distribution import (
	get_periodwise_distribution_data,
)
from erpnext.accounts.report.financial_statements import get_period_list
from erpnext.accounts.utils import get_fiscal_year


def get_data_column(filters, partner_doctype):
	data = []
	period_list = get_period_list(
		filters.fiscal_year,
		filters.fiscal_year,
		"",
		"",
		"Fiscal Year",
		filters.period,
		company=filters.company,
	)

	rows = get_data(filters, period_list, partner_doctype)
	columns = get_columns(filters, period_list, partner_doctype)

	if not rows:
		return columns, data

	for key, value in rows.items():
		#value.update({frappe.scrub(partner_doctype): key[0], "item_group": key[1],"item": key[2],"brand":key[3],"customer":key[4]})
		if filters.get('based_on')==None:
			value.update({frappe.scrub(partner_doctype): key[0], "item": key[1],"brand": key[2],"customer": key[3]})
		if filters.get('based_on')=="Item":
			value.update({frappe.scrub(partner_doctype): key[0], "item": key[1]})
		if filters.get('based_on')=="Brand":
			value.update({frappe.scrub(partner_doctype): key[0], "brand": key[1]})
		if filters.get('based_on')=="Customer":
			value.update({frappe.scrub(partner_doctype): key[0], "customer": key[1]})


		data.append(value)

	return columns, data


def get_data(filters, period_list, partner_doctype):
	sales_field = frappe.scrub(partner_doctype)
	sales_users_data = get_parents_data(filters, partner_doctype)
	print(f"""\n\n\n\n sales_user_data == {sales_users_data}\n\n\n""")

	if not sales_users_data:
		return
	sales_users, item_groups = [], []
	item_name,brand,customer  = [], [],[]
	item_sale_person = []
	brand_sale_person = []
	cust_sale_person = []

	for d in sales_users_data:
		print(f""" d = {d}""")
		if filters.get('based_on')== None and d.parent :
			print("hiiiiiiiiii")
			if d.parent :
				print("--------d.parent----",d.parent)
				sales_users.append(d.parent)
				#item_sale_person.append(d.parent)

			if d.item:
				if d.item not in item_name:
					item_name.append(d.item)

			if d.brand:		
				if d.brand not in brand:
					brand.append(d.brand)

			if d.customer:
				if d.customer not in customer:
					customer.append(d.customer)
		print(f"""\n\n\n in none if sales user = {sales_users}\n\n\n\n""")
		if filters.get('based_on')=="Item" and d.parent and d.item:
			if d.parent not in sales_users:
				#sales_users.append(d.parent)
				item_sale_person.append(d.parent)

			if d.item:
				if d.item not in item_name:
					item_name.append(d.item)

		if filters.get('based_on')=="Brand" and d.parent and d.brand:
			if d.parent not in sales_users:
				#sales_users.append(d.parent)
				brand_sale_person.append(d.parent)

			if d.brand:		
				if d.brand not in brand:
					brand.append(d.brand)

		if filters.get('based_on')=="Customer" and d.parent and d.customer:
			if d.parent not in sales_users:
				cust_sale_person.append(d.parent)
			
			if d.customer:
				if d.customer not in customer:
					customer.append(d.customer)


	
	date_field = "transaction_date" if filters.get("doctype") == "Sales Order" else "posting_date"

	
	if filters.get('based_on')==None:
		actual_data = get_all_actual_data(filters, item_name,brand,customer, sales_users, date_field, sales_field)
	
		item_var = prepare_data(filters, sales_users_data, actual_data, date_field, period_list, sales_field)
		return item_var

	if filters.get('based_on')=='Item':
		actual_data = get_actual_data(filters, item_name,brand,customer, item_sale_person, date_field, sales_field)
	
		item_var = prepare_item_data(filters, sales_users_data, actual_data, date_field, period_list, sales_field)
		return item_var

	if filters.get('based_on')=='Brand':
		actual_data = get_actual_data(filters, item_name,brand,customer, brand_sale_person, date_field, sales_field)
	
		brand_var = prepare_brand_data(filters, sales_users_data, actual_data, date_field, period_list, sales_field)
		return brand_var

	if filters.get('based_on')=='Customer':
		actual_data = get_actual_data(filters, item_name,brand,customer, cust_sale_person, date_field, sales_field)
	
		cust_var = prepare_customer_data(filters, sales_users_data, actual_data, date_field, period_list, sales_field)
		return cust_var


	#return prepare_data(filters, sales_users_data, actual_data, date_field, period_list, sales_field)


def get_columns(filters, period_list, partner_doctype):
	fieldtype, options = "Currency", "currency"

	if filters.get("target_on") == "Quantity":
		fieldtype, options = "Float", ""

	columns = [
		{
			"fieldname": frappe.scrub(partner_doctype),
			"label": _(partner_doctype),
			"fieldtype": "Link",
			"options": partner_doctype,
			"width": 150,
		},
		
	]
	if filters.get("based_on")=="Item":
		columns.append({"fieldname": "item","label": _("Item"),})
	if filters.get("based_on")=="Brand":
		columns.append({"fieldname": "brand","label": _("Brand"),})
	if filters.get("based_on")=="Customer":
		columns.append({"fieldname": "customer","label": _("Customer"),})
	if filters.get("based_on")==None:
		columns.extend([
			{"fieldname": "item","label": _("Item"),},
			{"fieldname": "brand","label": _("Brand"),},
			{"fieldname": "customer","label": _("Customer"),},
			])

	for period in period_list:
		target_key = "target_{}".format(period.key)
		variance_key = "variance_{}".format(period.key)

		columns.extend(
			[
				{
					"fieldname": target_key,
					"label": _("Target ({})").format(period.label),
					"fieldtype": fieldtype,
					"options": options,
					"width": 150,
				},
				{
					"fieldname": period.key,
					"label": _("Achieved ({})").format(period.label),
					"fieldtype": fieldtype,
					"options": options,
					"width": 150,
				},
				{
					"fieldname": variance_key,
					"label": _("Variance ({})").format(period.label),
					"fieldtype": fieldtype,
					"options": options,
					"width": 150,
				},
			]
		)

	columns.extend(
		[
			{
				"fieldname": "total_target",
				"label": _("Total Target"),
				"fieldtype": fieldtype,
				"options": options,
				"width": 150,
			},
			{
				"fieldname": "total_achieved",
				"label": _("Total Achieved"),
				"fieldtype": fieldtype,
				"options": options,
				"width": 150,
			},
			{
				"fieldname": "total_variance",
				"label": _("Total Variance"),
				"fieldtype": fieldtype,
				"options": options,
				"width": 150,
			},
		]
	)

	
	return columns
def prepare_data(filters, sales_users_data, actual_data, date_field, period_list, sales_field):
	rows = {}

	target_qty_amt_field = "target_qty" if filters.get("target_on") == "Quantity" else "target_amount"

	qty_or_amount_field = "stock_qty" if filters.get("target_on") == "Quantity" else "base_net_amount"
	for d in sales_users_data:
		key = (d.parent, d.item,d.brand,d.customer)
		dist_data = get_periodwise_distribution_data(
			d.distribution_id, period_list, filters.get("period")
		)

		if key not in rows:
			rows.setdefault(key, {"total_target": 0, "total_achieved": 0, "total_variance": 0})

		details = rows[key]
		for period in period_list:
			p_key = period.key
			if p_key not in details:
				details[p_key] = 0

			target_key = "target_{}".format(p_key)
			variance_key = "variance_{}".format(p_key)
			details[target_key] = (d.get(target_qty_amt_field) * dist_data.get(p_key)) / 100
			details[variance_key] = 0
			details["total_target"] += details[target_key]

			for r in actual_data:
				
				if (
					r.get(sales_field) == d.parent
					and period.from_date <= r.get(date_field)
					and r.get(date_field) <= period.to_date
				):
					details[p_key] += r.get(qty_or_amount_field, 0)
					details[variance_key] = details.get(p_key) - details.get(target_key)

			details["total_achieved"] += details.get(p_key)
			details["total_variance"] = details.get("total_achieved") - details.get("total_target")
	return rows


def prepare_item_data(filters, sales_users_data, actual_data, date_field, period_list, sales_field):
	rows = {}

	target_qty_amt_field = "target_qty" if filters.get("target_on") == "Quantity" else "target_amount"

	qty_or_amount_field = "stock_qty" if filters.get("target_on") == "Quantity" else "base_net_amount"
	
	for d in sales_users_data:
		if d.item:
			key = (d.parent, d.item)
			dist_data = get_periodwise_distribution_data(
				d.distribution_id, period_list, filters.get("period")
			)

			if key not in rows:
				rows.setdefault(key, {"total_target": 0, "total_achieved": 0, "total_variance": 0})

			details = rows[key]
			for period in period_list:
				p_key = period.key
				if p_key not in details:
					details[p_key] = 0

				target_key = "target_{}".format(p_key)
				variance_key = "variance_{}".format(p_key)
				details[target_key] = (d.get(target_qty_amt_field) * dist_data.get(p_key)) / 100
				details[variance_key] = 0
				details["total_target"] += details[target_key]
				

				for r in actual_data:
					if (
						r.get(sales_field) == d.parent
						and r.item_code == d.item
						and period.from_date <= r.get(date_field)
						and r.get(date_field) <= period.to_date
					):

						details[p_key] += r.get(qty_or_amount_field, 0)
						details[variance_key] = details.get(p_key) - details.get(target_key)

				details["total_achieved"] += details.get(p_key)

				details["total_variance"] = details.get("total_achieved") - details.get("total_target")
	return rows

def prepare_brand_data(filters, sales_users_data, actual_data, date_field, period_list, sales_field):
	rows = {}

	target_qty_amt_field = "target_qty" if filters.get("target_on") == "Quantity" else "target_amount"

	qty_or_amount_field = "stock_qty" if filters.get("target_on") == "Quantity" else "base_net_amount"
	
	for d in sales_users_data:
		if d.brand:
			key = (d.parent, d.brand)
			dist_data = get_periodwise_distribution_data(
				d.distribution_id, period_list, filters.get("period")
			)

			if key not in rows:
				rows.setdefault(key, {"total_target": 0, "total_achieved": 0, "total_variance": 0})

			details = rows[key]
			for period in period_list:
				p_key = period.key
				if p_key not in details:
					details[p_key] = 0

				target_key = "target_{}".format(p_key)
				variance_key = "variance_{}".format(p_key)
				details[target_key] = (d.get(target_qty_amt_field) * dist_data.get(p_key)) / 100
				details[variance_key] = 0
				details["total_target"] += details[target_key]
				

				for r in actual_data:
					if (
						r.get(sales_field) == d.parent
						and r.brand == d.brand
						and period.from_date <= r.get(date_field)
						and r.get(date_field) <= period.to_date
					):

						details[p_key] += r.get(qty_or_amount_field, 0)
						details[variance_key] = details.get(p_key) - details.get(target_key)

				details["total_achieved"] += details.get(p_key)

				details["total_variance"] = details.get("total_achieved") - details.get("total_target")
	return rows

def prepare_customer_data(filters, sales_users_data, actual_data, date_field, period_list, sales_field):
	rows = {}

	target_qty_amt_field = "target_qty" if filters.get("target_on") == "Quantity" else "target_amount"

	qty_or_amount_field = "stock_qty" if filters.get("target_on") == "Quantity" else "base_net_amount"
	
	for d in sales_users_data:
		if d.customer:
			key = (d.parent, d.customer)
			dist_data = get_periodwise_distribution_data(
				d.distribution_id, period_list, filters.get("period")
			)

			if key not in rows:
				rows.setdefault(key, {"total_target": 0, "total_achieved": 0, "total_variance": 0})

			details = rows[key]
			for period in period_list:
				p_key = period.key
				if p_key not in details:
					details[p_key] = 0

				target_key = "target_{}".format(p_key)
				variance_key = "variance_{}".format(p_key)
				details[target_key] = (d.get(target_qty_amt_field) * dist_data.get(p_key)) / 100
				details[variance_key] = 0
				details["total_target"] += details[target_key]
				

				for r in actual_data:
					if (
						r.get(sales_field) == d.parent
						and r.customer == d.customer
						and period.from_date <= r.get(date_field)
						and r.get(date_field) <= period.to_date
					):

						details[p_key] += r.get(qty_or_amount_field, 0)
						details[variance_key] = details.get(p_key) - details.get(target_key)

				details["total_achieved"] += details.get(p_key)

				details["total_variance"] = details.get("total_achieved") - details.get("total_target")
	return rows



#def get_actual_data(filters, item_groups,item_name,brand,customer, sales_users_or_territory_data, date_field, sales_field):
def get_all_actual_data(filters, item_name,brand,customer, sales_users_or_territory_data, date_field, sales_field):
	fiscal_year = get_fiscal_year(fiscal_year=filters.get("fiscal_year"), as_dict=1)
	dates = [fiscal_year.year_start_date, fiscal_year.year_end_date]
	f_from_date = fiscal_year.year_start_date
	f_to_date = fiscal_year.year_end_date
	company = filters.get('company')

	select_field = "`tab{0}`.{1}".format(filters.get("doctype"), sales_field)
	child_table = "`tab{0}`".format(filters.get("doctype") + " Item")
	sales_p = sales_users_or_territory_data

	if sales_field == "sales_person":
		select_field = "`tabSales Team`.sales_person"
		child_table = "`tab{0}`, `tabSales Team`".format(filters.get("doctype") + " Item")
		
		cond = """`tabSales Team`.parent = `tab{0}`.name and
			`tabSales Team`.sales_person in ({1}) """.format(
			filters.get("doctype"), ",".join(["%s"] * len(sales_p))
		)
	else:
		cond = "`tab{0}`.{1} in ({2})".format(
			filters.get("doctype"), sales_field, ",".join(["%s"] * len(sales_p))
		)
	filters_items_group = " "
	if (filters.get('item_groups')):
		filters_items_group = "and `tab{child_doc}`.item_group in ({item_groups}) "

	if filters.get('based_on')==None:
		if filters.get('doctype')=='Sales Order':
			data = frappe.db.sql(
			""" SELECT 
					soi.item_code,soi.stock_qty,soi.base_net_amount,so.sales_person,so.transaction_date
				FROM 
					`tabSales Order` so 
				INNER JOIN
					`tabSales Order Item`soi  
				ON soi.parent=so.name 
				WHERE 
					so.docstatus = 1 
					AND so.sales_person in %(sales_person)s
					AND so.transaction_date between %(f_from_date)s and %(f_to_date)s

				""",{
					'company':company,
					'item_name':item_name,
					'sales_person':sales_users_or_territory_data,
					'f_from_date':f_from_date,
					'f_to_date':f_to_date

					},as_dict=1,debug=1)
			return data
		if filters.get('doctype')=='Sales Invoice':
			data = frappe.db.sql(
			""" SELECT 
					*
				FROM 
					`tabSales Invoice` si 
				INNER JOIN
					`tabSales Invoice Item`sii  
				ON sii.parent=si.name 
				WHERE 
					si.docstatus = 1 
					AND si.sales_person in %(sales_person)s
					AND si.posting_date between %(f_from_date)s and %(f_to_date)s

				""",{
					'sales_person':sales_users_or_territory_data,
					'f_from_date':f_from_date,
					'f_to_date':f_to_date

					},as_dict=1,debug=1)
			return data
		if filters.get('doctype')=='Delivery Note':
			data = frappe.db.sql(
			""" SELECT 
					dni.item_code,dni.stock_qty,dni.base_net_amount,dn.sales_person,dn.posting_date
				FROM 
					`tabDelivery Note` dn 
				INNER JOIN
					`tabDelivery Note Item`dni  
				ON dni.parent=dn.name 
				WHERE 
					dn.docstatus = 1 
					AND dn.sales_person in %(sales_person)s
					AND dn.posting_date between %(f_from_date)s and %(f_to_date)s

				""",{
					'sales_person':sales_users_or_territory_data,
					'f_from_date':f_from_date,
					'f_to_date':f_to_date

					},as_dict=1,debug=1)
			return data
	

def get_actual_data(filters, item_name,brand,customer, sales_users_or_territory_data, date_field, sales_field):
	fiscal_year = get_fiscal_year(fiscal_year=filters.get("fiscal_year"), as_dict=1)
	dates = [fiscal_year.year_start_date, fiscal_year.year_end_date]
	
	f_from_date = fiscal_year.year_start_date
	f_to_date = fiscal_year.year_end_date
	company = filters.get('company')

	select_field = "`tab{0}`.{1}".format(filters.get("doctype"), sales_field)
	child_table = "`tab{0}`".format(filters.get("doctype") + " Item")
	sales_p = sales_users_or_territory_data

	if sales_field == "sales_person":
		select_field = "`tabSales Team`.sales_person"
		child_table = "`tab{0}`, `tabSales Team`".format(filters.get("doctype") + " Item")
		
		cond = """`tabSales Team`.parent = `tab{0}`.name and
			`tabSales Team`.sales_person in ({1}) """.format(
			filters.get("doctype"), ",".join(["%s"] * len(sales_p))
		)
	else:
		cond = "`tab{0}`.{1} in ({2})".format(
			filters.get("doctype"), sales_field, ",".join(["%s"] * len(sales_p))
		)
	filters_items_group = " "
	if (filters.get('item_groups')):
		filters_items_group = "and `tab{child_doc}`.item_group in ({item_groups}) "

	if filters.get('based_on')==None:
		
		if filters.get('doctype')=='Sales Order':
			data = frappe.db.sql(
			""" SELECT 
					soi.item_code,soi.stock_qty,soi.base_net_amount,so.sales_person,so.transaction_date
				FROM 
					`tabSales Order` so 
				INNER JOIN
					`tabSales Order Item`soi  
				ON soi.parent=so.name 
				WHERE 
					so.docstatus = 1 
					AND so.sales_person in %(sales_person)s
					AND so.transaction_date between %(f_from_date)s and %(f_to_date)s

				""",{
					'company':company,
					'item_name':item_name,
					'sales_person':sales_users_or_territory_data,
					'f_from_date':f_from_date,
					'f_to_date':f_to_date

					},as_dict=1,debug=1)
			return data

	if filters.get('based_on')=='Item':

		if filters.get('doctype')=='Sales Order':
			data = frappe.db.sql(
			""" SELECT 
					soi.item_code,soi.stock_qty,soi.base_net_amount,so.sales_person,so.transaction_date
				FROM 
					`tabSales Order` so 
				INNER JOIN
					`tabSales Order Item`soi  
				ON soi.parent=so.name 
				WHERE 
					so.docstatus = 1 
					AND soi.item_code in %(item_name)s
					AND so.sales_person in %(sales_person)s
					AND so.transaction_date between %(f_from_date)s and %(f_to_date)s

				""",{
					'company':company,
					'item_name':item_name,
					'sales_person':sales_users_or_territory_data,
					'f_from_date':f_from_date,
					'f_to_date':f_to_date

					},as_dict=1,debug=1)
			return data

		if filters.get('doctype')=='Sales Invoice':
			data = frappe.db.sql(
			""" SELECT 
					sii.item_code,sii.stock_qty,sii.base_net_amount,si.sales_person,si.posting_date
				FROM 
					`tabSales Invoice` si 
				INNER JOIN
					`tabSales Invoice Item`sii  
				ON sii.parent=si.name 
				WHERE 
					si.docstatus = 1 
					AND sii.item_code in %(item_name)s
					AND si.sales_person in %(sales_person)s
					AND si.posting_date between %(f_from_date)s and %(f_to_date)s

				""",{
					'item_name':item_name,
					'sales_person':sales_users_or_territory_data,
					'f_from_date':f_from_date,
					'f_to_date':f_to_date

					},as_dict=1,debug=1)
			return data

		if filters.get('doctype')=='Delivery Note':
			data = frappe.db.sql(
			""" SELECT 
					dni.item_code,dni.stock_qty,dni.base_net_amount,dn.sales_person,dn.posting_date
				FROM 
					`tabDelivery Note` dn 
				INNER JOIN
					`tabDelivery Note Item`dni  
				ON dni.parent=dn.name 
				WHERE 
					dn.docstatus = 1 
					AND dni.item_code in %(item_name)s
					AND dn.sales_person in %(sales_person)s
					AND dn.posting_date between %(f_from_date)s and %(f_to_date)s

				""",{
					'item_name':item_name,
					'sales_person':sales_users_or_territory_data,
					'f_from_date':f_from_date,
					'f_to_date':f_to_date

					},as_dict=1,debug=1)
			return data
		
	if filters.get('based_on')=='Brand':
		if filters.get('doctype')=='Sales Order':
			data = frappe.db.sql(
			""" SELECT 
					soi.brand,soi.stock_qty,soi.base_net_amount,so.sales_person,so.transaction_date
				FROM 
					`tabSales Order` so 
				INNER JOIN
					`tabSales Order Item`soi  
				ON soi.parent=so.name 
				WHERE 
					so.docstatus = 1 
					AND soi.brand in %(brand)s
					AND so.sales_person in %(sales_person)s
					AND so.transaction_date between %(f_from_date)s and %(f_to_date)s

				""",{
					'brand':brand,
					'sales_person':sales_users_or_territory_data,
					'f_from_date':f_from_date,
					'f_to_date':f_to_date

					},as_dict=1,debug=1)
			return data
		if filters.get('doctype')=='Sales Invoice':
			data = frappe.db.sql(
			""" SELECT 
					sii.brand,sii.stock_qty,sii.base_net_amount,si.sales_person,si.posting_date
				FROM 
					`tabSales Invoice` si 
				INNER JOIN
					`tabSales Invoice Item`sii  
				ON sii.parent=si.name 
				WHERE 
					si.docstatus = 1 
					AND sii.brand in %(brand)s
					AND si.sales_person in %(sales_person)s
					AND si.posting_date between %(f_from_date)s and %(f_to_date)s

				""",{
					'brand':brand,
					'sales_person':sales_users_or_territory_data,
					'f_from_date':f_from_date,
					'f_to_date':f_to_date

					},as_dict=1,debug=1)
			return data
		
		if filters.get('doctype')=='Delivery Note':
			data = frappe.db.sql(
			""" SELECT 
					dni.brand,dni.stock_qty,dni.base_net_amount,dn.sales_person,dn.posting_date
				FROM 
					`tabDelivery Note` dn 
				INNER JOIN
					`tabDelivery Note Item`dni  
				ON dni.parent=dn.name 
				WHERE 
					dn.docstatus = 1 
					AND dni.brand in %(brand)s
					AND dn.sales_person in %(sales_person)s
					AND dn.posting_date between %(f_from_date)s and %(f_to_date)s

				""",{
					'brand':brand,
					'sales_person':sales_users_or_territory_data,
					'f_from_date':f_from_date,
					'f_to_date':f_to_date

					},as_dict=1,debug=1)
			return data

	if filters.get('based_on')=='Customer':
		if filters.get('doctype')=='Sales Order':
			data = frappe.db.sql(
			""" SELECT 
					so.customer,soi.stock_qty,soi.base_net_amount,so.sales_person,so.transaction_date
				FROM 
					`tabSales Order` so 
				INNER JOIN
					`tabSales Order Item`soi  
				ON soi.parent=so.name 
				WHERE 
					so.docstatus = 1 
					AND so.customer in %(customer)s
					AND so.sales_person in %(sales_person)s
					AND so.transaction_date between %(f_from_date)s and %(f_to_date)s

				""",{
					'customer':customer,
					'sales_person':sales_users_or_territory_data,
					'f_from_date':f_from_date,
					'f_to_date':f_to_date

					},as_dict=1,debug=1)
			return data

		if filters.get('doctype')=='Sales Invoice':
			data = frappe.db.sql(
			""" SELECT 
					si.customer,sii.stock_qty,sii.base_net_amount,si.sales_person,si.posting_date
				FROM 
					`tabSales Invoice` si 
				INNER JOIN
					`tabSales Invoice Item`sii  
				ON sii.parent=si.name 
				WHERE 
					si.docstatus = 1 
					AND si.customer in %(customer)s
					AND si.sales_person in %(sales_person)s
					AND si.posting_date between %(f_from_date)s and %(f_to_date)s

				""",{
					'customer':customer,
					'sales_person':sales_users_or_territory_data,
					'f_from_date':f_from_date,
					'f_to_date':f_to_date

					},as_dict=1,debug=1)
			return data
		
		if filters.get('doctype')=='Delivery Note':
			data = frappe.db.sql(
			""" SELECT 
					dn.customer,dni.stock_qty,dni.base_net_amount,dn.sales_person,dn.posting_date
				FROM 
					`tabDelivery Note` dn 
				INNER JOIN
					`tabDelivery Note Item`dni  
				ON dni.parent=dn.name 
				WHERE 
					dn.docstatus = 1 
					AND dn.customer in %(customer)s
					AND dn.sales_person in %(sales_person)s
					AND dn.posting_date between %(f_from_date)s and %(f_to_date)s

				""",{
					'customer':customer,
					'sales_person':sales_users_or_territory_data,
					'f_from_date':f_from_date,
					'f_to_date':f_to_date

					},as_dict=1,debug=1)
			return data


def get_parents_data(filters, partner_doctype):
	filters_dict = {"parenttype": partner_doctype}

	target_qty_amt_field = "target_qty" if filters.get("target_on") == "Quantity" else "target_amount"

	if filters.get("fiscal_year"):
		filters_dict["fiscal_year"] = filters.get("fiscal_year")
	
	return frappe.get_all(
		"Target Detail",
		filters=filters_dict,
		fields=["parent","item","brand", "customer",target_qty_amt_field, "fiscal_year", "distribution_id"],
		#fields=["parent", "item_group","item","brand", "customer",target_qty_amt_field, "fiscal_year", "distribution_id"],
	)
