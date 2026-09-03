# Copyright (c) 2026, abc and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Pricebook(Document):
	def validate(self):
		self.validate_duplicate_products()

	def validate_duplicate_products(self):
		"""Salesforce keys a pricebook entry on ProductCode, so two rows for the
		same product would collide on the far side rather than fail here."""
		seen = set()
		for row in self.entries:
			if row.product_code in seen:
				frappe.throw(
					_("Row {0}: {1} appears more than once. Each product may only be priced once per pricebook.").format(
						row.idx, frappe.bold(row.product_code)
					)
				)
			seen.add(row.product_code)
