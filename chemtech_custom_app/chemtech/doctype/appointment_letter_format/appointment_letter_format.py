# Copyright (c) 2022, abc and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class AppointmentLetterFormat(Document):
	def before_save(self):
		self.ctc = (self.basic +self.hra+self.esic+self.provident_fund+self.statutory_bonus)*12