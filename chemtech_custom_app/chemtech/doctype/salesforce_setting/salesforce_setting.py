# Copyright (c) 2025, abc and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, add_to_date


class SalesforceSetting(Document):
	pass


def _fetch_new_token():
	"""Call Salesforce OAuth2 token endpoint and persist the result."""
	import requests

	doc = frappe.get_single("Salesforce Setting")

	if not doc.salesforce_url:
		frappe.throw("Salesforce URL is not set.")
	if not doc.client_id:
		frappe.throw("Client ID is not set.")
	if not doc.client_secret:
		frappe.throw("Client Secret is not set.")

	url = doc.salesforce_url.rstrip("/") + "/services/oauth2/token"

	response = requests.post(
		url,
		params={
			"grant_type": "client_credentials",
			"client_id": doc.client_id,
			"client_secret": doc.client_secret,
		},
		timeout=30,
	)

	if response.status_code != 200:
		frappe.throw(f"Salesforce API error {response.status_code}: {response.text}")

	data = response.json()
	access_token = data.get("access_token")

	if not access_token:
		frappe.throw(f"No access_token in response: {data}")

	# expires_in is in seconds; Salesforce default is 3600. Use 300s buffer.
	expires_in = int(data.get("expires_in", 3600))
	expiry = add_to_date(now_datetime(), seconds=expires_in - 300)

	frappe.db.set_single_value("Salesforce Setting", "access_token", access_token)
	frappe.db.set_single_value("Salesforce Setting", "token_expiry", expiry)

	return access_token


@frappe.whitelist()
def get_access_token(selected_date=None):
	"""Manually fetch a fresh token (called from the button)."""
	if selected_date:
		frappe.db.set_single_value("Salesforce Setting", "selected_date", selected_date)
	return _fetch_new_token()


@frappe.whitelist()
def get_valid_access_token():
	"""Return the stored token if still valid, otherwise auto-refresh."""
	doc = frappe.get_single("Salesforce Setting")

	token = doc.access_token
	expiry = doc.token_expiry

	if token and expiry and now_datetime() < frappe.utils.get_datetime(expiry):
		return token

	# Token missing or expired — fetch a new one automatically
	return _fetch_new_token()
