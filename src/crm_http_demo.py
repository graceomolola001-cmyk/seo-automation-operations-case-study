"""Executable CRM *HTTP integration* test against a local synthetic API.

A local HTTP server serves pageable fictional contacts. The adapter fetches
pages over HTTP, validates source contracts and deduplicates by contact_id.
This proves transport, pagination and mapping without implying a live CRM login.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

from src.pipeline import DataQualityError, dedupe_rows, require

ROOT = Path(__file__).resolve().parents[1]


def build_handler(contacts: list[dict]):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlparse(self.path)
            if url.path != "/contacts":
                self.send_error(404, "Not found")
                return
            qs = parse_qs(url.query)
            try:
                page = int(qs.get("page", ["1"])[0])
                limit = int(qs.get("limit", ["20"])[0])
                if not (page >= 1 and 1 <= limit <= 50):
                    raise ValueError()
            except (ValueError, TypeError):
                self.send_error(400, "Invalid pagination")
                return
            offset = (page - 1) * limit
            batch = contacts[offset:offset + limit]
            body = json.dumps({"contacts": batch, "next_page": page + 1 if offset + limit < len(contacts) else None}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass
    return Handler


@contextmanager
def local_mock_crm(contacts: list[dict]):
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(contacts))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def fetch_contacts(base_url: str, max_pages: int = 10) -> tuple[list[dict], int]:
    """Fetch a mock CRM's pages. Credentials never belong in fixture files."""
    require(base_url.startswith("http://127.0.0.1:"), "demo adapter must only call local loopback")
    page = 1
    seen_pages: set[int] = set()
    rows: list[dict] = []
    count = 0
    while page is not None:
        require(page not in seen_pages, "CRM returned repeating page cursor")
        require(count < max_pages, "CRM max_pages reached before final page")
        seen_pages.add(page)
        with urlopen(f"{base_url}/contacts?page={page}&limit=20", timeout=3) as response:
            require(response.status == 200, "CRM non-200 response")
            payload = json.load(response)
        require(isinstance(payload.get("contacts"), list), "CRM response contacts are missing")
        for x in payload["contacts"]:
            require(isinstance(x, dict) and bool(x.get("contact_id")), "CRM contact missing identifier")
            rows.append(x)
        nxt = payload.get("next_page")
        require(nxt is None or (type(nxt) is int and nxt > page), "invalid CRM pagination cursor")
        page = nxt
        count += 1
    return dedupe_rows(rows, ("contact_id",)), count


def run_local_demo() -> dict:
    fixture = json.loads((ROOT / "examples" / "demo_input.json").read_text())
    contacts = fixture["crm_fixture"]["contacts"]
    with local_mock_crm(contacts) as base:
        fetched, pages = fetch_contacts(base)
    return {"mode": "SYNTHETIC local HTTP CRM integration", "api_pages_fetched": pages, "unique_contacts": len(fetched), "stages": sorted({x["stage"] for x in fetched}), "data_protection": "localhost only; no real accounts or personal data"}


if __name__ == "__main__":
    argparse.ArgumentParser(description="Run local paginated synthetic CRM API and client").parse_args()
    print(json.dumps(run_local_demo(), indent=2))
