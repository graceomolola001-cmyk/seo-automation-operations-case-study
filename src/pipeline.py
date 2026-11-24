"""Deterministic SEO operations demo. No network calls or real client data.

Sources modeled: finalized Google Search Console days, matured GA4 event rows,
rolling 24h Microsoft Clarity device/channel segments, and a simulated CRM adapter.
Run: python -m src.pipeline --input examples/demo_input.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any


class DataQualityError(ValueError):
    """Refuse to report success when source coverage or integrity is uncertain."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DataQualityError(message)


def day_range(start: str, end: str) -> list[str]:
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    require(b >= a, "end date is earlier than start date")
    return [(a + timedelta(days=x)).isoformat() for x in range((b - a).days + 1)]


def dedupe_rows(rows: list[dict], key_fields: tuple[str, ...]) -> list[dict]:
    """Identical retries are fine. Conflicting values for the same business key fail."""
    indexed = {}
    for row in rows:
        key = tuple(row.get(f) for f in key_fields)
        require(all(x is not None for x in key), f"missing unique key {key_fields}")
        if key in indexed and indexed[key] != row:
            raise DataQualityError(f"conflicting duplicate record: {key}")
        indexed[key] = row
    return [indexed[k] for k in sorted(indexed)]


def validate_source_rows(data: dict) -> tuple[list[dict], list[dict], list[str]]:
    window = data["reporting_window"]
    previous = day_range(window["previous_start"], window["previous_end"])
    current = day_range(window["current_start"], window["current_end"])
    require(len(previous) == len(current) == 7, "both periods must contain exactly 7 days")
    require(previous[-1] < current[0], "reporting windows overlap")
    expected = set(previous + current)
    require(data.get("gsc", {}).get("truncated") is False, "GSC response truncation not ruled out")
    require(data.get("ga4", {}).get("truncated") is False, "GA4 response truncation not ruled out")
    gsc = dedupe_rows(data["gsc"]["daily"], ("date",))
    ga4 = dedupe_rows(data["ga4"]["daily"], ("date", "event_name"))
    require({r["date"] for r in gsc} == expected, "GSC missing/unexpected days")
    require({r["date"] for r in ga4} == expected, "GA4 missing/unexpected days")
    require(len(ga4) == 14, "GA4 has missing or duplicate event-date pairs")
    for row in gsc:
        require(row.get("status") == "final", "GSC data is not finalized")
        for field in ("clicks", "impressions"):
            require(type(row.get(field)) is int and row[field] >= 0, f"invalid GSC {field}")
        require(row["clicks"] <= row["impressions"], "GSC clicks exceed impressions")
    for row in ga4:
        require(row.get("status") == "matured", "GA4 date is not matured")
        require(row.get("event_name") == "prospectus_form_submit", "unknown or unapproved GA4 event")
        for field in ("organic_sessions", "event_count"):
            require(type(row.get(field)) is int and row[field] >= 0, f"invalid GA4 {field}")
    return gsc, ga4, current


def weekly_sums(rows: list[dict], current: list[str], field: str) -> dict:
    current_set = set(current)
    here = sum(row[field] for row in rows if row["date"] in current_set)
    prior = sum(row[field] for row in rows if row["date"] not in current_set)
    change = None if prior == 0 else round(100 * (here - prior) / prior, 1)
    return {"previous": prior, "current": here, "change_pct": change}


def validate_clarity(snapshots: list[dict]) -> list[dict]:
    require(snapshots, "Clarity snapshots missing")
    require(len(snapshots) < 1000, "Clarity may have hit its 1000-row API cap")
    valid_channels = {"OrganicSearch", "PaidSearch"}
    valid_devices = {"Mobile", "PC", "Tablet"}
    output = dedupe_rows(snapshots, ("captured_on", "channel", "device"))
    for row in output:
        require(row["channel"] in valid_channels and row["device"] in valid_devices, "unexpected Clarity segment")
        require(type(row["sessions"]) is int and row["sessions"] >= 0, "invalid Clarity session count")
        require(row.get("verified") is True, "Clarity snapshot is not verified")
        for field in ("dead_click_session_pct", "rage_click_session_pct", "quickback_session_pct", "scroll_depth_pct"):
            value = row.get(field)
            require(type(value) in (float, int) and 0 <= value <= 100, f"invalid Clarity {field}")
        require(type(row.get("script_error_count")) is int and row["script_error_count"] >= 0, "invalid script error events")
    return output


def clarity_findings(rows: list[dict]) -> dict:
    days = sorted({r["captured_on"] for r in rows})
    require(len(days) >= 2, "Clarity needs two snapshots to detect change")
    before, after = days[-2:]
    previous = {(r["channel"], r["device"]): r for r in rows if r["captured_on"] == before}
    current = {(r["channel"], r["device"]): r for r in rows if r["captured_on"] == after}
    review = []
    for key in sorted(current):
        now, was = current[key], previous.get(key)
        if not was or min(now["sessions"], was["sessions"]) < 100:
            continue
        difference = round(now["dead_click_session_pct"] - was["dead_click_session_pct"], 1)
        if now["dead_click_session_pct"] >= 15 and difference >= 5:
            review.append({"segment": "/".join(key), "metric": "dead_click_session_pct", "now_pct": now["dead_click_session_pct"], "previous_pct": was["dead_click_session_pct"], "change_pp": difference, "sessions": now["sessions"], "action": "Inspect recordings/heatmaps for unresponsive controls and form issues"})
        if now["script_error_count"] >= 10:
            review.append({"segment": "/".join(key), "metric": "script_error_count", "events": now["script_error_count"], "sessions": now["sessions"], "action": "Reproduce affected scripts in the browser and validate form submission"})
    return {"previous_capture": before, "current_capture": after, "friction_flags": review, "scope": "sitewide channel x device, rolling 24h"}


def crm_diagnostic(data: dict, event_count: int) -> dict:
    """CRM adapter is synthetic. Never treat GA4 eventCount as unique leads."""
    crm = data["crm_fixture"]
    require(crm.get("mode") == "synthetic_fixture", "only synthetic CRM data allowed in public demo")
    contacts = dedupe_rows(crm["contacts"], ("contact_id",))
    valid_status = {"new", "contacted", "applied", "enrolled"}
    require(all(c.get("stage") in valid_status for c in contacts), "unknown CRM lead stage")
    return {"adapter": "simulated; not a live CRM connection", "unique_example_contacts": len(contacts), "ga4_prospectus_event_occurrences": event_count, "event_to_contact_gap": event_count - len(contacts), "status": "needs_follow_up", "interpretation": "Directional audit only. One person can trigger multiple GA4 events; a CRM contact is a different measurement unit."}


def post_cohorts(data: dict) -> list[dict]:
    rows = dedupe_rows(data["page_gsc_daily"], ("date", "post_id"))
    seen = set()
    output = []
    as_of = date.fromisoformat(data["reporting_window"]["as_of"])
    for post in data["posts"]:
        post_id = post["post_id"]
        require(post_id not in seen, "duplicate post id")
        seen.add(post_id)
        published = date.fromisoformat(post["publish_date"])
        result = {"post_id": post_id, "url": post["path"], "cohorts": {}}
        for days in (7, 14, 28):
            dates = day_range(published.isoformat(), (published + timedelta(days=days - 1)).isoformat())
            recorded = {r["date"]: r for r in rows if r["post_id"] == post_id and r["date"] in dates}
            mature = (published + timedelta(days=days + 1)) <= as_of  # conservative 2-day finalization lag
            if not mature:
                result["cohorts"][str(days)] = {"status": "awaiting_maturity"}
            elif set(recorded) != set(dates):
                result["cohorts"][str(days)] = {"status": "missing_historical_coverage", "days_available": len(recorded)}
            else:
                result["cohorts"][str(days)] = {"status": "complete", "clicks": sum(r["clicks"] for r in recorded.values()), "impressions": sum(r["impressions"] for r in recorded.values())}
        output.append(result)
    return output


def upsert_and_verify(rows: list[dict], existing: list[dict] | None = None) -> dict:
    """In-memory Google Sheets analogue; stable keys, idempotent re-run, readback QA."""
    current = {r["row_key"]: dict(r) for r in (existing or [])}
    require(len(current) == len(existing or []), "pre-existing duplicate row keys")
    for row in rows:
        require("row_key" in row and "value" in row, "invalid storage payload")
        current[row["row_key"]] = dict(row)
    for row in rows:
        require(current[row["row_key"]] == row, "readback mismatch")
    require(len(current) == len(set(current)), "duplicate storage keys")
    return {"verified": True, "rows_in_store": len(current), "written_keys": sorted({r["row_key"] for r in rows}), "storage_mode": "in-memory simulation"}


def illustrative_efficiency(data: dict) -> dict:
    model = data["illustrative_efficiency_model"]
    before, after = float(model["manual_hours_per_week"]), float(model["review_hours_per_week"])
    require(before >= after >= 0, "invalid illustrative effort estimate")
    return {"estimated_hours_reallocated_per_week": round(before - after, 2), "classification": "user-editable assumption, not measured staff savings", "baseline_hours_assumed": before, "qa_hours_assumed": after}


def run_pipeline(data: dict) -> dict:
    require(data.get("dataset_kind") == "synthetic", "do not run public demo on private production exports")
    gsc, ga4, current_dates = validate_source_rows(data)
    clarity = clarity_findings(validate_clarity(data["clarity_snapshots"]))
    clicks = weekly_sums(gsc, current_dates, "clicks")
    impressions = weekly_sums(gsc, current_dates, "impressions")
    sessions = weekly_sums(ga4, current_dates, "organic_sessions")
    events = weekly_sums(ga4, current_dates, "event_count")
    alerts = []
    if clicks["change_pct"] is not None and clicks["change_pct"] <= -20:
        alerts.append({"severity": "review", "metric": "gsc_organic_clicks", "change_pct": clicks["change_pct"], "action": "Inspect query and page changes; check indexing and search demand"})
    if events["change_pct"] is not None and events["change_pct"] <= -20:
        alerts.append({"severity": "review", "metric": "ga4_prospectus_form_submit_events", "change_pct": events["change_pct"], "action": "Inspect the GA4 event, prospectus form journey and lead-quality data separately"})
    for issue in clarity["friction_flags"]:
        alerts.append({"severity": "investigate", "metric": issue["metric"], "segment": issue["segment"], "action": issue["action"]})
    storage_rows = [{"row_key": "weekly|clicks|" + current_dates[-1], "value": clicks}, {"row_key": "weekly|events|" + current_dates[-1], "value": events}]
    result = {
        "status": "PASS", "data_kind": "SYNTHETIC DEMO: zero client data", "report_period_end": current_dates[-1],
        "kpis": {"gsc_organic_clicks": clicks, "gsc_impressions": impressions, "ga4_organic_sessions": sessions, "ga4_prospectus_form_submit_events": events},
        "quality_checks": {"gsc_dates_finalized": True, "ga4_event_confirmed": "prospectus_form_submit", "source_date_coverage_complete": True, "source_truncation": False, "deduplication": "stable keys and conflicting duplicate rejection", "storage": upsert_and_verify(storage_rows)},
        "clarity": clarity, "crm_diagnostic": crm_diagnostic(data, events["current"]),
        "posts": post_cohorts(data), "alerts": alerts,
        "recommended_decisions": [a["action"] for a in alerts[:3]],
        "time_savings_scenario": illustrative_efficiency(data),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a synthetic SEO automation evidence pack")
    parser.add_argument("--input", default="examples/demo_input.json", help="synthetic JSON fixture")
    parser.add_argument("--out", help="optional output JSON path")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    output = json.dumps(run_pipeline(data), indent=2, ensure_ascii=False) + "\n"
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
