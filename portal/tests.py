import json
import tempfile
from pathlib import Path

from django.test import TestCase
from django.urls import reverse

from . import views
from .services import Database


class DuplicateUpvoteFlowTests(TestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._tmp_dir = tempfile.TemporaryDirectory()
		cls._original_db = views._services["db"]

		test_db_path = Path(cls._tmp_dir.name) / "reports_test.db"
		test_db = Database(test_db_path)
		test_db.create_database()
		views._services["db"] = test_db

	@classmethod
	def tearDownClass(cls):
		views._services["db"] = cls._original_db
		cls._tmp_dir.cleanup()
		super().tearDownClass()

	def setUp(self):
		self.db = views._services["db"]

	def _create_report(self, description="Large pothole near bus stand", location="MG Road"):
		self.db.save_report(
			description,
			location,
			{
				"Issue": "Road Damage",
				"Priority": "Medium",
				"Department": "Public Works Department (PWD)",
				"Confidence": "High",
				"Advice": "Mark hazard and avoid lane.",
				"Risk Score": 45,
				"Reason": "Detected road damage keywords.",
				"Suggested Action": "Patch road surface within 48 hours.",
			},
		)
		return self.db.get_reports()[0][0]

	def test_preview_analysis_flags_duplicate(self):
		report_id = self._create_report()

		payload = {
			"description": "Large pothole near bus stand on MG Road causing traffic risk.",
			"location": "MG Road",
		}
		response = self.client.post(
			reverse("portal:preview_analysis"),
			data=json.dumps(payload),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 200)
		body = response.json()
		self.assertTrue(body["duplicate"]["duplicate"])
		self.assertEqual(body["duplicate"]["report_id"], report_id)
		self.assertGreaterEqual(body["duplicate"]["similarity"], 55)

	def test_preview_analysis_same_description_different_location_not_duplicate(self):
		self._create_report(
			description="Large pothole near bus stand on central road causing traffic risk.",
			location="Kakkanad, Kochi",
		)

		payload = {
			"description": "Large pothole near bus stand on central road causing traffic risk.",
			"location": "Mylapore, Chennai",
		}
		response = self.client.post(
			reverse("portal:preview_analysis"),
			data=json.dumps(payload),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 200)
		body = response.json()
		self.assertFalse(body["duplicate"]["duplicate"])

	def test_upvote_report_increments_vote_count(self):
		report_id = self._create_report()

		response = self.client.post(
			reverse("portal:upvote_report"),
			data=json.dumps({"report_id": report_id}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 200)
		body = response.json()
		self.assertTrue(body["success"])
		self.assertEqual(body["report_id"], report_id)
		self.assertEqual(body["upvotes"], 2)

	def test_upvote_report_requires_valid_existing_id(self):
		not_found_response = self.client.post(
			reverse("portal:upvote_report"),
			data=json.dumps({"report_id": 999999}),
			content_type="application/json",
		)
		self.assertEqual(not_found_response.status_code, 404)

		bad_request_response = self.client.post(
			reverse("portal:upvote_report"),
			data=json.dumps({"report_id": "abc"}),
			content_type="application/json",
		)
		self.assertEqual(bad_request_response.status_code, 400)

	def test_submit_report_auto_upvotes_duplicate_without_creating_new_row(self):
		report_id = self._create_report(
			description="Large pothole near bus stand on MG Road causing traffic risk",
			location="MG Road",
		)
		before_rows = len(self.db.get_reports())

		response = self.client.post(
			reverse("portal:submit_report"),
			data=json.dumps({
				"description": "Large pothole near bus stand on MG Road causing traffic risk",
				"location": "MG Road",
				"ai_correct": True,
			}),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 200)
		body = response.json()
		self.assertTrue(body["success"])
		self.assertTrue(body["auto_upvoted"])
		self.assertEqual(body["report_id"], report_id)
		self.assertEqual(body["upvotes"], 2)

		after_rows = len(self.db.get_reports())
		self.assertEqual(before_rows, after_rows)
