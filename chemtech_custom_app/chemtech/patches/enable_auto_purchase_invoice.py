import frappe


def execute():
	"""Keep existing behaviour: the auto Purchase Invoice was always on before the
	Selling Settings switch existed. Writes the Singles row directly because this
	patch runs before the custom field is synced (the field's own default only
	applies once Selling Settings is saved)."""
	frappe.db.set_single_value("Selling Settings", "custom_auto_create_purchase_invoice", 1)
