# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from chemtech_custom_app.chemtech.report.sales_person_target_variance_based_on_item_code.item_group_wise_sales_target_variance import (
	get_data_column,
)

#/home/indictrans/projects/chemtek/frappe-bench/apps/chemtech_custom_app/chemtech_custom_app/chemtech/report/sales_person_target_variance_based_on_item_code/item_group_wise_sales_target_variance.py
# from erpnext.selling.report.sales_partner_target_variance_based_on_item_group.item_group_wise_sales_target_variance import (
# 	get_data_column,
# )


def execute(filters=None):
	data = []

	return get_data_column(filters, "Sales Person")
