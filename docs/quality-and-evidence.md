# Quality assurance and evidence

## What a technical reviewer can verify now

| Claim | Public verification | Status |
|---|---|---|
| A full workflow can execute | Import `workflows/n8n-import-demo.json` and run Manual Trigger | Reproducible synthetic demonstration |
| Search data checks protect reports | Python source checks and tests reject missing dates, non-final data and API truncation | Covered by automated tests |
| GA4 prospectus events are interpreted safely | Approved event name is asserted; event counts are labelled separately from CRM contacts | Covered by automated tests |
| Duplicate data is prevented | Identical retries collapse; conflicting duplicates cause exceptions | Covered by automated tests |
| Blog cohort dates are handled | 7/14/28-day windows distinguish mature, missing and future dates | Covered by automated tests |
| Clarity signals retain correct units | Tests validate incidence percentages and API row limits | Covered by automated tests |
| Successful writes are verified | In-memory upsert/read-back logic is runnable; private implementation used Google Sheets write + read-back | Public simulation + private production validation |
| CRM lead stages are reconciled | Fictional contacts with IDs and stage fields are processed | Simulation only; no live CRM access |
| Recurring staff time saved | Change time assumptions in synthetic fixture and rerun | Illustrative model; no measured savings |
| Real conversion or revenue lift | Would require approved CRM / enrolment data and attribution | Not claimed |

## Fail-closed decisions

The automation must refuse a success result when:

- GSC or GA4 dates are missing, unfinalized or capped.
- A conversion event name differs from the approved form event.
- A duplicate business key contains conflicting source values.
- Clarity source rows are capped or incidence percentages are invalid.
- A historical blog cohort appears mature but its source dates are incomplete.
- An upsert/read-back record disagrees with the source.

The test suite exercises these cases. Use `python -m unittest discover -s tests -v` to repeat.

## Evidence that should never appear in a public portfolio

- Production credentials, tokens, cloud project identifiers, private n8n URLs and real Google Chat space IDs.
- Raw contact names, emails, phone numbers, CRM exports or prospectus submissions.
- Live client traffic, conversion reports, revenue, course demand, visitor recordings or heatmaps unless independently authorized.
- Employer-specific node exports or client contractual configuration.

## To turn the portfolio into a stronger verified case study later

With written employer or client permission, provide separately sanitized screenshots of successful private n8n runs, masked Sheets QA output, and authorized Google Chat delivery. Measure an actual weekly baseline for manual reporting time and time-to-detection before claiming quantified savings.

Avoid any language suggesting synthetic numbers represent production impact. The Python and n8n demos are fully reproducible; real deployment outcomes remain confidential.
