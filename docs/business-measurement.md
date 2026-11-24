# How to prove business impact after launch

Business impact must be measured separately from workflow execution success.

## Before launch

Record a normal week for each of these:

- **Manual reporting hours:** time spent exporting, merging, checking and writing reports.
- **Average detection lag:** hours between a confirmed site/SEO issue starting and the first useful alert.
- **Lead data reconciliation:** percentage of application/CRM entries that can be linked to an authorized form submission with a stable ID.
- **CRO investigation time:** time between a Clarity friction signal and a confirmed root-cause finding.

## After launch

Capture the same metrics after a stable period, with comparable workload. Use run-log history to substantiate which outputs were generated automatically, and keep human QA time in the calculation.

## Example model only

| Measure | Illustrative baseline | Illustrative reviewed process | Interpretation |
|---|---:|---:|---|
| Weekly staff time | 5 hours | 1 hour | 4 hours of **potential** capacity freed weekly |
| Annualized equivalent | 260 hours | 52 hours | 208 hours **if** weekly workload and process remain comparable |

These are **planning assumptions**, not recorded company results. The sample fixture contains the assumptions so reviewers can edit them.

## Responsible conversion measurement

A `prospectus_form_submit` GA4 event indicates an instrumented event occurred. It does not independently prove a CRM contact, qualified application or enrolment. To report lead-to-enrolment conversion, connect an authorized CRM and track lead identity, stage dates and source attribution.

The safest outcome claim before CRM access is available is about **operational reliability**: fewer manual steps, improved consistency of daily collection and faster potential visibility into issues. Quantify only after a measured before-and-after baseline exists.
