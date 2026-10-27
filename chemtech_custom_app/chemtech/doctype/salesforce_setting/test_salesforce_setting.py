# Copyright (c) 2025, abc and contributors
# See license.txt

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from chemtech_custom_app.chemtech.custom_script import salesforce_item_sync as sync

TOKEN_FN = (
	"chemtech_custom_app.chemtech.doctype.salesforce_setting.salesforce_setting.get_valid_access_token"
)


def _item(name, product_group="Regular", **extra):
	return frappe._dict(
		name=name,
		item_name=f"Item {name}",
		description="",
		disabled=0,
		stock_uom="Nos",
		item_group="Products",
		brand=None,
		custom_product_group=product_group,
		flags=frappe._dict(),
		**extra,
	)


def _response(ok=True, status=200, text='{"results": []}'):
	return MagicMock(ok=ok, status_code=status, text=text, json=lambda: json.loads(text))


def _get_doc(items):
	"""frappe.get_doc stand-in: Items by name, real doc for anything else (e.g. the settings single)."""
	by_name = {i.name: i for i in items}
	real = frappe.get_doc

	def get_doc(doctype, name=None, *args, **kwargs):
		return by_name[name] if doctype == "Item" else real(doctype, name, *args, **kwargs)

	return get_doc


class TestBulkItemSync(FrappeTestCase):
	def _sync(self, docs, response):
		with patch.object(sync.requests, "post", return_value=response) as post, patch(
			TOKEN_FN, return_value="tok"
		), patch.object(sync.frappe, "log_error") as log_error:
			result = sync.sync_items_to_salesforce(docs)
		return result, post, log_error

	def test_all_items_go_in_one_request(self):
		result, post, log_error = self._sync([_item("A"), _item("B"), _item("C")], _response())

		self.assertEqual(post.call_count, 1)
		records = post.call_args.kwargs["json"]["records"]
		self.assertEqual([r["ProductCode"] for r in records], ["A", "B", "C"])
		self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer tok")
		self.assertTrue(result["success"])
		self.assertEqual(result["synced"], 3)
		# Salesforce response is stored in the Error Log
		self.assertIn("Success", log_error.call_args.kwargs["title"])
		self.assertIn('{"results": []}', log_error.call_args.kwargs["message"])

	def test_npd_and_ignored_items_are_skipped(self):
		ignored = _item("C")
		ignored.flags.ignore_salesforce_sync = True

		result, post, _ = self._sync([_item("A"), _item("B", "NPD"), ignored], _response())

		records = post.call_args.kwargs["json"]["records"]
		self.assertEqual([r["ProductCode"] for r in records], ["A"])
		self.assertEqual(result["synced"], 1)
		self.assertEqual(result["skipped"], ["B", "C"])

	def test_only_skipped_items_makes_no_request(self):
		result, post, _ = self._sync([_item("B", "NPD")], _response())

		post.assert_not_called()
		self.assertTrue(result["success"])
		self.assertEqual(result["synced"], 0)

	def test_http_error_fails_every_item_and_is_logged(self):
		result, _, log_error = self._sync(
			[_item("A"), _item("B")], _response(ok=False, status=401, text="bad token")
		)

		self.assertFalse(result["success"])
		self.assertEqual(result["synced"], 0)
		self.assertEqual([f["item"] for f in result["failed"]], ["A", "B"])
		self.assertIn("401", result["failed"][0]["error"])
		self.assertIn("Failed", log_error.call_args.kwargs["title"])
		self.assertIn("bad token", log_error.call_args.kwargs["message"])

	def test_partial_failure_is_matched_to_the_right_item(self):
		body = json.dumps(
			{
				"results": [
					{"success": False, "errors": ["bad picklist value"]},
					{"success": True, "errors": []},
				]
			}
		)
		result, _, log_error = self._sync([_item("A"), _item("B")], _response(text=body))

		self.assertFalse(result["success"])
		self.assertEqual(result["synced"], 1)
		self.assertEqual(result["failed"], [{"item": "A", "error": "bad picklist value"}])
		self.assertIn("Partial Failure", log_error.call_args.kwargs["title"])
		self.assertIn("bad picklist value", log_error.call_args.kwargs["message"])

	def test_failure_mapping_skips_npd_items_in_the_request(self):
		body = json.dumps({"results": [{"success": True}, {"success": False, "errors": ["x"]}]})
		result, _, _ = self._sync([_item("A"), _item("N", "NPD"), _item("C")], _response(text=body))

		self.assertEqual(result["failed"], [{"item": "C", "error": "x"}])
		self.assertEqual(result["skipped"], ["N"])

	def test_token_failure_is_reported_and_logged(self):
		with patch(TOKEN_FN, side_effect=frappe.ValidationError("no client credentials user enabled")), patch.object(
			sync.requests, "post"
		) as post, patch.object(sync.frappe, "log_error") as log_error:
			result = sync.sync_items_to_salesforce([_item("A")])

		post.assert_not_called()
		self.assertFalse(result["success"])
		self.assertIn("no client credentials user enabled", result["failed"][0]["error"])
		self.assertIn("Error", log_error.call_args.kwargs["title"])

	def test_single_item_wrapper_keeps_old_contract(self):
		with patch.object(sync.requests, "post", return_value=_response()), patch(TOKEN_FN, return_value="t"), patch.object(
			sync.frappe, "log_error"
		):
			ok = sync.sync_item_to_salesforce(_item("A"))
			skipped = sync.sync_item_to_salesforce(_item("B", "NPD"))

		self.assertTrue(ok["success"])
		self.assertIn("response", ok)
		self.assertIsNone(skipped)

	def test_enqueue_dedupes_checks_permission_and_queues_once(self):
		doc = MagicMock()
		with patch.object(sync.frappe, "get_doc", return_value=doc), patch.object(
			sync.frappe, "enqueue"
		) as enqueue:
			out = sync.enqueue_bulk_item_sync('["A", "B", "A", ""]')

		self.assertEqual(out, {"queued": 2})
		self.assertEqual(doc.check_permission.call_count, 2)
		enqueue.assert_called_once()
		self.assertEqual(enqueue.call_args.kwargs["item_names"], ["A", "B"])
		self.assertEqual(enqueue.call_args.kwargs["requested_by"], frappe.session.user)

	def test_enqueue_rejects_empty_selection(self):
		with patch.object(sync.frappe, "enqueue") as enqueue:
			for empty in ("[]", '[""]'):
				with self.assertRaises(frappe.ValidationError):
					sync.enqueue_bulk_item_sync(empty)
		enqueue.assert_not_called()

	def test_enqueue_stops_when_user_cannot_read_an_item(self):
		doc = MagicMock()
		doc.check_permission.side_effect = frappe.PermissionError
		with patch.object(sync.frappe, "get_doc", return_value=doc), patch.object(
			sync.frappe, "enqueue"
		) as enqueue:
			with self.assertRaises(frappe.PermissionError):
				sync.enqueue_bulk_item_sync('["A"]')
		enqueue.assert_not_called()

	def test_job_publishes_counts_to_requesting_user(self):
		items = [_item("A"), _item("B", "NPD"), _item("C")]
		with patch.object(sync.frappe, "get_doc", side_effect=_get_doc(items)), patch.object(
			sync, "sync_items_to_salesforce", wraps=sync.sync_items_to_salesforce
		), patch.object(sync.requests, "post", return_value=_response()), patch(
			TOKEN_FN, return_value="t"
		), patch.object(sync.frappe, "log_error"), patch.object(
			sync.frappe, "publish_realtime"
		) as publish:
			sync._sync_items_in_background(["A", "B", "C"], "user@example.com")

		event, payload = publish.call_args.args
		self.assertEqual(event, "salesforce_item_bulk_sync_complete")
		self.assertEqual(
			payload, {"requested": 3, "synced": 2, "skipped": 1, "failed": []}
		)
		self.assertEqual(publish.call_args.kwargs["user"], "user@example.com")

	def test_job_reports_failure_count_when_salesforce_rejects(self):
		items = [_item("A"), _item("B", "NPD"), _item("C")]
		with patch.object(sync.frappe, "get_doc", side_effect=_get_doc(items)), patch.object(
			sync.requests, "post", return_value=_response(ok=False, status=500, text="boom")
		), patch(TOKEN_FN, return_value="t"), patch.object(sync.frappe, "log_error"), patch.object(
			sync.frappe, "publish_realtime"
		) as publish:
			sync._sync_items_in_background(["A", "B", "C"], "user@example.com")

		payload = publish.call_args.args[1]
		self.assertEqual(len(payload["failed"]), 2)
		self.assertEqual(payload["synced"], 0)
		self.assertIn("500", payload["failed"][0]["error"])

	def test_job_survives_item_load_failure(self):
		with patch.object(sync.frappe, "get_doc", side_effect=frappe.DoesNotExistError("gone")), patch.object(
			sync.frappe, "log_error"
		), patch.object(sync.frappe, "publish_realtime") as publish:
			sync._sync_items_in_background(["A"], "user@example.com")

		payload = publish.call_args.args[1]
		self.assertEqual(payload["failed"], [{"item": "A", "error": "gone"}])
