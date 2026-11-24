"""Public-safe regression suite: all source inputs are synthetic."""
import copy
import json
import unittest
from pathlib import Path

from src.pipeline import (
    DataQualityError, clarity_findings, crm_diagnostic, day_range, dedupe_rows,
    post_cohorts, run_pipeline, upsert_and_verify, validate_clarity,
    validate_source_rows,
)

ROOT = Path(__file__).resolve().parents[1]


def sample():
    return json.loads((ROOT / "examples" / "demo_input.json").read_text())


class TestSourceValidation(unittest.TestCase):
    def test_demo_passes(self):
        self.assertEqual(run_pipeline(sample())["status"], "PASS")

    def test_14_final_gsc_dates(self):
        gsc, _, days = validate_source_rows(sample())
        self.assertEqual(len(gsc), 14)
        self.assertEqual(len(days), 7)

    def test_missing_gsc_day_fails_closed(self):
        data = sample()
        data["gsc"]["daily"].pop()
        with self.assertRaisesRegex(DataQualityError, "GSC missing"):
            run_pipeline(data)

    def test_gsc_pending_date_rejected(self):
        data = sample()
        data["gsc"]["daily"][0]["status"] = "pending"
        with self.assertRaisesRegex(DataQualityError, "not finalized"):
            run_pipeline(data)

    def test_wrong_ga4_event_rejected(self):
        data = sample()
        data["ga4"]["daily"][0]["event_name"] = "page_view"
        with self.assertRaisesRegex(DataQualityError, "unapproved GA4 event"):
            run_pipeline(data)

    def test_ga4_pending_date_rejected(self):
        data = sample()
        data["ga4"]["daily"][0]["status"] = "pending"
        with self.assertRaisesRegex(DataQualityError, "not matured"):
            run_pipeline(data)

    def test_gsc_truncation_rejected(self):
        data = sample()
        data["gsc"]["truncated"] = True
        with self.assertRaisesRegex(DataQualityError, "truncation"):
            run_pipeline(data)

    def test_ga4_truncation_rejected(self):
        data = sample()
        data["ga4"]["truncated"] = True
        with self.assertRaisesRegex(DataQualityError, "truncation"):
            run_pipeline(data)

    def test_identical_retry_collapses(self):
        d = sample()["gsc"]["daily"]
        self.assertEqual(len(dedupe_rows(d + [copy.deepcopy(d[0])], ("date",))), 14)

    def test_conflicting_duplicate_rejected(self):
        d = sample()["gsc"]["daily"]
        dup = copy.deepcopy(d[0]); dup["clicks"] += 1
        with self.assertRaisesRegex(DataQualityError, "conflicting duplicate"):
            dedupe_rows(d + [dup], ("date",))

    def test_day_range_is_inclusive(self):
        self.assertEqual(day_range("2026-10-01", "2026-10-03"), ["2026-10-01", "2026-10-02", "2026-10-03"])


class TestBusinessSignals(unittest.TestCase):
    def test_synthetic_clicks_decline_25_percent(self):
        x = run_pipeline(sample())
        self.assertEqual(x["kpis"]["gsc_organic_clicks"]["previous"], 1600)
        self.assertEqual(x["kpis"]["gsc_organic_clicks"]["current"], 1200)
        self.assertEqual(x["kpis"]["gsc_organic_clicks"]["change_pct"], -25.0)

    def test_event_count_explicitly_not_crm_leads(self):
        x = run_pipeline(sample())
        self.assertEqual(x["kpis"]["ga4_prospectus_form_submit_events"]["current"], 84)
        self.assertEqual(x["crm_diagnostic"]["unique_example_contacts"], 62)
        self.assertEqual(x["crm_diagnostic"]["status"], "needs_follow_up")
        self.assertIn("not a live CRM connection", x["crm_diagnostic"]["adapter"])

    def test_critical_alerts_emitted(self):
        x = run_pipeline(sample())
        metrics = {a["metric"] for a in x["alerts"]}
        self.assertIn("gsc_organic_clicks", metrics)
        self.assertIn("ga4_prospectus_form_submit_events", metrics)
        self.assertIn("dead_click_session_pct", metrics)

    def test_clarity_percentages_not_counts(self):
        x = run_pipeline(sample())
        organic = [r for r in x["clarity"]["friction_flags"] if r.get("segment") == "OrganicSearch/Mobile" and r["metric"] == "dead_click_session_pct"]
        self.assertEqual(len(organic), 1)
        self.assertEqual(organic[0]["now_pct"], 19.0)
        self.assertEqual(organic[0]["change_pp"], 9.0)

    def test_clarity_api_row_cap_rejected(self):
        data = sample()["clarity_snapshots"]
        data = (data * 125)[:1000]
        with self.assertRaisesRegex(DataQualityError, "1000-row"):
            validate_clarity(data)

    def test_clarity_rate_over_100_rejected(self):
        data = sample()["clarity_snapshots"]
        data[0]["dead_click_session_pct"] = 133
        with self.assertRaisesRegex(DataQualityError, "dead_click_session_pct"):
            validate_clarity(data)

    def test_clarity_unverified_rejected(self):
        data = sample()["clarity_snapshots"]
        data[0]["verified"] = False
        with self.assertRaisesRegex(DataQualityError, "not verified"):
            validate_clarity(data)

    def test_low_sample_suppresses_clarity_alert(self):
        rows = sample()["clarity_snapshots"]
        for r in rows:
            if r["channel"] == "OrganicSearch" and r["device"] == "Mobile":
                r["sessions"] = 99
        x = clarity_findings(validate_clarity(rows))
        self.assertFalse(any(r["segment"] == "OrganicSearch/Mobile" for r in x["friction_flags"]))

    def test_two_snapshots_required(self):
        rows = sample()["clarity_snapshots"]
        with self.assertRaisesRegex(DataQualityError, "two snapshots"):
            clarity_findings(validate_clarity([r for r in rows if r["captured_on"] == "2026-10-14"]))

    def test_crm_rejects_live_data(self):
        data = sample()
        data["crm_fixture"]["mode"] = "production"
        with self.assertRaisesRegex(DataQualityError, "synthetic CRM"):
            run_pipeline(data)

    def test_business_savings_is_assumption(self):
        x = run_pipeline(sample())
        self.assertEqual(x["time_savings_scenario"]["estimated_hours_reallocated_per_week"], 4.0)
        self.assertIn("not measured", x["time_savings_scenario"]["classification"])

    def test_no_private_data_accepted(self):
        data = sample(); data["dataset_kind"] = "real_client"
        with self.assertRaisesRegex(DataQualityError, "private production"):
            run_pipeline(data)


class TestOperations(unittest.TestCase):
    def test_all_28_day_cohorts_complete_for_old_post(self):
        x = post_cohorts(sample())
        older = next(r for r in x if r["post_id"] == "POST-101")
        self.assertEqual({v["status"] for v in older["cohorts"].values()}, {"complete"})

    def test_new_post_has_immature_14_28(self):
        x = post_cohorts(sample())
        newer = next(r for r in x if r["post_id"] == "POST-202")
        self.assertEqual(newer["cohorts"]["7"]["status"], "complete")
        self.assertEqual(newer["cohorts"]["14"]["status"], "awaiting_maturity")
        self.assertEqual(newer["cohorts"]["28"]["status"], "awaiting_maturity")

    def test_missing_mature_historical_dates_explicit(self):
        d = sample()
        d["page_gsc_daily"] = [r for r in d["page_gsc_daily"] if not (r["post_id"] == "POST-101" and r["date"] == "2026-10-01")]
        older = next(r for r in post_cohorts(d) if r["post_id"] == "POST-101")
        self.assertEqual(older["cohorts"]["28"]["status"], "missing_historical_coverage")

    def test_stable_idempotent_upsert(self):
        row = {"row_key": "2026-10-14|organic", "value": 44}
        a = upsert_and_verify([row])
        b = upsert_and_verify([row], [row])
        self.assertEqual(a["rows_in_store"], b["rows_in_store"])

    def test_duplicate_storage_keys_rejected(self):
        row = {"row_key": "same", "value": 2}
        with self.assertRaisesRegex(DataQualityError, "pre-existing duplicate"):
            upsert_and_verify([row], [row, row])

    def test_output_fixture_reproducible(self):
        expected = json.loads((ROOT / "examples" / "demo_output.json").read_text())
        self.assertEqual(run_pipeline(sample()), expected)


if __name__ == "__main__":
    unittest.main()
