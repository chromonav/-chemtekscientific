# Copyright (c) 2022, abc and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate
class VisitPlan(Document):
	pass
	# @frappe.whitelist()
	# def get_customer_subsc(visit_date, docname=None):
	#     postdate = getdate(visit_date)
	#     print ("********",postdate.weekday())
