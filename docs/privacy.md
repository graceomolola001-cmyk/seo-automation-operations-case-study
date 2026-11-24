# Public-safe reconstruction and security

This project is a **sanitized reconstruction of an SEO reporting design**, built for interviews, portfolio review and technical testing.

- All domains, paths, blog posts, dates, people, CRM contacts, traffic figures and events in `examples/` are synthetic.
- n8n workflows in this repo have **no credentials**, live HTTP calls, real webhook URLs, account IDs or linked client resources.
- Company/private client names, real report screenshots, business performance, infrastructure endpoints, internal spreadsheet IDs and Chat space IDs are excluded.
- Production API logic is represented by provider-level integration contracts in `docs/integrations.md`.
- Data from the example CRM fixture is invented and contains fake contact IDs only, no personal data.
- `/scripts/security_scan.py` checks the bundle for common leaked-secret patterns and known-private URL markers before public publication. It supplements human inspection and does not guarantee perfect sanitization.

## Before sharing or adding more files

1. Run `python scripts/security_scan.py .`.
2. Inspect every diff in GitHub for identifiers and private analytics.
3. Do not add `.env`, raw n8n exports, CRM lists or screenshots from live client accounts.
4. Obtain explicit permission for real deployment names, brands, performance numbers or recordings.

The intent is to demonstrate engineering decisions without implying ownership of client assets.
