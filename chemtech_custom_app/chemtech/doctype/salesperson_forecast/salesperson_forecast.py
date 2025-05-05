# Copyright (c) 2025, abc and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SalespersonForecast(Document):
	def validate(self):
		seen = set()
		for row in self.item_sales_qty:
			key = (row.item, row.month)
			if key in seen:
				frappe.throw(f"Duplicate Item '{row.item}' for Month '{row.month}' is not allowed.")
			seen.add(key)

