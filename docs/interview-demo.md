# Five-minute interview demo: SEO automation that leads to decisions

## First 30 seconds: Lead with the business outcome

> "I built a workflow to stop teams spending hours on repetitive exports, catch important search and conversion problems earlier, and help them decide what to fix. It connects search visibility, on-site activity, and behavioural friction into one verified reporting process. This public example uses synthetic data to protect client information."

## Minute 1: Show the architecture

Open the flow diagram in the [README](../README.md). Explain that each source is collected separately, then dates and metrics are validated before anything is reported. Give a concrete example: an incomplete GSC date can create a false traffic drop, so the workflow refuses it.

## Minutes 2 and 3: Run the n8n workflow

Import [`n8n-import-demo.json`](../workflows/n8n-import-demo.json) into n8n. Run **START | Run Synthetic End-to-End Demo**. Highlight these nodes in order:

1. **02 | Validate Source Dates + Metric Contracts:** wrong event names, immature dates and capped API responses fail immediately.
2. **05 | CRM Adapter (Simulated) + Reconciliation:** the fixture has 84 GA4 form event occurrences and 62 distinct mock contacts. The workflow flags the difference without treating either number as the other.
3. **06 | Clarity Organic / Paid Mobile Friction:** a meaningful rise in affected sessions triggers a UX investigation recommendation.
4. **08 | Simulate Idempotent Sheets Upserts + Readback:** repeat writes do not create duplicate records; a stored value must match the source.
5. **09 | Publish Decision-Ready Demo Output:** show the actual prioritized recommendation list.

Say explicitly: "These values are a synthetic scenario. In the private implementation, the source connections and Google Sheets read-back were tested against live APIs."

## Minute 4: Prove that failure cases were designed

Run:

```bash
python -m unittest discover -s tests -v
```

Choose a test to explain: missing GSC dates, a wrong GA4 lead event, a conflicting duplicate, or a Clarity field outside its accepted range. The solution blocks silent errors before stakeholders make decisions from inaccurate numbers.

## Minute 5: Business outcome and ownership

> "The value is the time reallocated from compiling dashboards to fixing organic landing pages and prospectus friction. A five-hour manual week reduced to one hour of review would free four hours, but that's a planning estimate, not a result I have measured. My next measurement is tracking time spent on reporting and time-to-detection of confirmed issues."

## If asked: "Is the CRM live?"

> "The public CRM adapter is a simulation, clearly labelled. In the underlying work I did not have CRM access, so I did not claim verified lead creation or revenue. I built the data contract and reconciliation logic so the integration can be authenticated and tested once a CRM owner authorizes it. The search, analytics, behavioural and reporting systems were independently validated."

## If asked: "What did you personally build?"

Show the working pipeline, the deterministic test outputs, failure handling, visual n8n node map, metric definitions, and the decisions in the final output. Explain the design choices, including why GA4 events and unique CRM contacts must be kept separate. State which systems were validated privately and which connectors are simulated publicly.

## Safe screen-sharing rules

Use this repository, its synthetic fixture, and a non-work n8n account. Do not open your employer's credentials, dashboards, contact databases, source code, configuration screens, customer-specific analytics, or restricted workflow URLs without permission.
