# Integration contracts and architecture

The public n8n workflow is self-contained so any reviewer can import and test it. These contracts describe the corresponding authenticated production design. This document contains no access tokens, property IDs or client URLs.

## 1. Google Search Console (GSC)

**Role:** Organic search clicks, impressions, pages and queries.

- Read API: Search Analytics query. Use a verified Search Console property.
- Set explicit reporting dates and time zone. GSC data has an ingestion delay.
- Retrieve daily, page-by-date and query-by-date results.
- Treat API limits and missing date coverage as blockers. Query-level privacy thresholds can affect row availability; do not promise exact completeness beyond what the source returns.
- Normalize business keys as `date|search_type` and `date|path|search_type`; upsert on those keys.
- Verify daily totals and stored rows by reading them back.

## 2. Google Analytics 4

**Role:** Organic Search sessions and `prospectus_form_submit` event occurrences.

- Read API: GA4 Data API `runReport`.
- Filter `sessionDefaultChannelGroup = Organic Search` and the approved event name.
- Use the property's reporting time zone; flag incomplete/maturing dates.
- Prevent accidental multiplication of GA4 metrics when joining landing pages and events.
- Store unique keys such as `date|channel` and `date|channel|landing_path`.
- Measure form **event occurrences**. Deduplication and event-fire correctness require separate tracking tests. Unique CRM leads and enrolments are different KPIs.

## 3. Microsoft Clarity

**Role:** Behavioural friction by source channel and device.

- Read API: project live-insights export.
- Prefer `Device × Channel` rather than complete tracking-query URLs. Per-URL results may reach the service's row cap and cannot be treated as a complete dataset.
- One daily rolling 24h capture is sufficient for this reporting design.
- Retain dead-click and rage-click **sessions affected percentage**, script-error **event count**, quickbacks and scroll depth. Preserve each metric's unit.
- Compare two comparable captures before triggering an alert. Require a minimum number of sessions to avoid noisy flags.
- The export API supplies aggregated metrics; review actual page heatmaps and individual recordings in the authorized Clarity dashboard.

## 4. WordPress or public CMS

**Role:** Discover published posts, canonical paths and original publication dates. Public read-only WordPress REST API access is sufficient for the post tracker.

For a post published on day 1, compute 7-day, 14-day and 28-day GSC cohorts once those dates are mature. Return `awaiting_maturity` for future windows and `missing_historical_coverage` for past windows with incomplete source data. Never silently treat either as zero.

## 5. Google Sheets and Google Chat

**Role:** Persistent reporting store and stakeholder notifications.

- Use stable unique keys, so a retry updates a row rather than inserting a duplicate.
- After writing, fetch saved rows and confirm values, keys and expected row counts. A successful HTTP response by itself does not establish data correctness.
- Store source timestamps, data status, source row counts and check outcomes in an execution log.
- Notify stakeholders only when alert conditions trigger; send a scheduled weekly summary, with a clear reporting period and next actions.
- A separate failure handler logs errors even when Chat delivery fails.

## 6. CRM boundary: simulated in this public repo

The synthetic fixture models a lead table with a unique `contact_id`, date and stage (`new`, `contacted`, `applied`, `enrolled`). The mock data is processed and reconciled against GA4 form event occurrences.

**Production implementation contract, pending access and authorization:**

1. Authenticate to the approved CRM using its documented API and scopes.
2. Fetch contacts or accepted form submissions in a defined local reporting period, handling pagination and rate limits.
3. Normalize identity without exposing raw names, phone numbers or email addresses in analytics stores. Prefer approved CRM-generated IDs.
4. Deduplicate by stable CRM identifier; keep update history for pipeline stages.
5. Reconcile at the correct measurement level: accepted submissions, unique contacts, applications and enrolments are separately defined.
6. Detect delayed or missing syncs, alert the owner and record a QA status.

**Verification rule:** The mock workflow demonstrates the contract and flags a directional gap. It does **not** prove a live CRM API integration or verified lead-to-enrolment attribution. Those require consent, credentials, event mapping and access to contact-level source records.
