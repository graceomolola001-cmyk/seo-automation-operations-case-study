"""Integration tests with a genuine local HTTP server, entirely fictional contacts."""
import unittest
from src.crm_http_demo import fetch_contacts, local_mock_crm, run_local_demo
from src.pipeline import DataQualityError


class TestCRMHTTPIntegration(unittest.TestCase):
    def test_real_http_transport_and_four_pages(self):
        out = run_local_demo()
        self.assertEqual(out["api_pages_fetched"], 4)
        self.assertEqual(out["unique_contacts"], 62)
        self.assertIn("SYNTHETIC", out["mode"])

    def test_single_page_http(self):
        with local_mock_crm([{"contact_id": "FAKE-01", "stage": "new"}]) as host:
            records, pages = fetch_contacts(host)
        self.assertEqual(pages, 1)
        self.assertEqual(records[0]["contact_id"], "FAKE-01")

    def test_duplicates_identical_paginated_contacts_collapse(self):
        row = {"contact_id": "FAKE-01", "stage": "new"}
        with local_mock_crm([row, row]) as host:
            records, _ = fetch_contacts(host)
        self.assertEqual(len(records), 1)

    def test_conflicting_http_contacts_rejected(self):
        with local_mock_crm([{"contact_id": "FAKE-01", "stage": "new"}, {"contact_id": "FAKE-01", "stage": "applied"}]) as host:
            with self.assertRaisesRegex(DataQualityError, "conflicting duplicate"):
                fetch_contacts(host)

    def test_page_limit_fails_closed(self):
        rows = [{"contact_id": f"FAKE-{i}", "stage": "new"} for i in range(21)]
        with local_mock_crm(rows) as host:
            with self.assertRaisesRegex(DataQualityError, "max_pages"):
                fetch_contacts(host, max_pages=1)

    def test_external_url_blocked(self):
        with self.assertRaisesRegex(DataQualityError, "local loopback"):
            fetch_contacts("https://crm.example.invalid")


if __name__ == "__main__":
    unittest.main()
