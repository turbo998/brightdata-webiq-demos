#!/usr/bin/env python3
"""
Bright Data — Solutions Architect Assignment · Task 2  (v3, merged best-of)
==========================================================================
ONE single flow:  discover links → collect links → push to Web Scraper → get output

  Stage 1 · Browser API : open amazon.com, search "lenovo thinkpad" (real search
                          box, with a /s?k= URL fallback if the layout A/B-shifts)
  Stage 2 · Browser API : collect every Product Detail Page (PDP) URL → /dp/<ASIN>
  Stage 3 · Web Scraper : push the PDP URLs to the Amazon "Products by URL" dataset
  Stage 4 · Web Scraper : poll the snapshot until it is "ready"
  Stage 5 · Web Scraper : download the structured product JSON

Run:
    pip install -r requirements.txt
    python -m playwright install chromium      # only for a local fallback
    cp .env.example .env                        # then fill in credentials
    python amazon_flow.py --keyword "lenovo thinkpad" --max-pdps 5

Why two products chained?
  • Browser API     = a real cloud Chrome you drive with Playwright. It unblocks the
    interactive part (search box, JS-rendered results) and yields the PDP URLs.
  • Web Scraper API = a managed parser that turns each PDP URL into clean structured
    JSON (title, price, ASIN, rating, …). No selectors to write or maintain.

Why the ASYNC /trigger endpoint (not /scrape)?
  • /scrape  (sync)  — real-time, capped ~20 URLs/request. Good for a quick lookup.
  • /trigger (async) — for >20 URLs, discovery flows, webhook/S3 delivery. Returns a
    snapshot_id you poll, then download. This is the pattern you actually ship, so the
    same code scales from 5 URLs to thousands without changes.

Endpoints verified against docs.brightdata.com (June 2026):
  • Browser API : wss://<USER>:<PASS>@brd.superproxy.io:9222  (connect_over_cdp)
  • dataset_id  : gd_l7q7dkf244hwjntr0  (Amazon "Products by URL" — confirm in your dashboard)
  • Trigger     : POST {BASE}/trigger?dataset_id=<id>&include_errors=true&format=json
  • Progress    : GET  {BASE}/progress/<snapshot_id>
  • Download    : GET  {BASE}/snapshot/<snapshot_id>?format=json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests
from playwright.sync_api import sync_playwright

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars also work without it.

# --------------------------------------------------------------------------- #
# Configuration (env first, safe placeholders otherwise)                       #
# --------------------------------------------------------------------------- #
BROWSER_AUTH = os.environ.get(
    "BROWSER_AUTH", "brd-customer-<id>-zone-<zone>:<password>"
)
BRIGHTDATA_API_TOKEN = os.environ.get("BRIGHTDATA_API_TOKEN", "YOUR_API_TOKEN")
AMAZON_DATASET_ID = os.environ.get("AMAZON_DATASET_ID", "gd_l7q7dkf244hwjntr0")

BROWSER_HOST = os.environ.get("BROWSER_HOST", "brd.superproxy.io")
BROWSER_PORT = os.environ.get("BROWSER_PORT", "9222")
CDP_ENDPOINT = f"wss://{BROWSER_AUTH}@{BROWSER_HOST}:{BROWSER_PORT}"

API_BASE = "https://api.brightdata.com/datasets/v3"
AUTH_HEADER = {"Authorization": f"Bearer {BRIGHTDATA_API_TOKEN}"}
OUTPUT_DIR = Path(__file__).parent / "output"


def log(stage: str, msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] [{stage:<7}] {msg}", flush=True)


def _get_with_retry(url: str, *, params=None, tries: int = 4, timeout: int = 60):
    """GET with simple exponential backoff — production observability hygiene."""
    delay = 2
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(url, headers=AUTH_HEADER, params=params, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if attempt == tries:
                raise
            log("retry", f"{e.__class__.__name__} on GET — retry {attempt}/{tries} in {delay}s")
            time.sleep(delay)
            delay *= 2


# --------------------------------------------------------------------------- #
# STAGE 1 + 2 · Browser API: search Amazon, collect PDP URLs                    #
# --------------------------------------------------------------------------- #
def _collect_asins_on_page(page) -> list[str]:
    """Harvest ASINs from a rendered Amazon search-results page."""
    page.wait_for_selector('div[data-component-type="s-search-result"]', timeout=60_000)
    asins = page.eval_on_selector_all(
        'div[data-component-type="s-search-result"][data-asin]',
        "els => els.map(e => e.getAttribute('data-asin')).filter(Boolean)",
    )
    # Belt-and-suspenders: also harvest /dp/<ASIN> hrefs anywhere on the page.
    hrefs = page.eval_on_selector_all(
        "a[href*='/dp/']", "els => els.map(e => e.getAttribute('href'))"
    )
    for h in hrefs:
        m = re.search(r"/dp/([A-Z0-9]{10})", h or "")
        if m:
            asins.append(m.group(1))
    return asins


def discover_pdp_urls(keyword: str, max_pages: int = 1) -> list[str]:
    """
    Collect unique PDP URLs across `max_pages` of Amazon results.

    The Browser API allows ONE navigation per session, so we open a fresh page
    per results page: page 1 uses the real search box (with a /s?k= fallback),
    pages 2+ go straight to /s?k=<kw>&page=N. Set max_pages high to collect ALL.
    """
    print("\n" + "=" * 72)
    print(f"STAGE 1·2 — Browser API: search Amazon for '{keyword}', collect PDP URLs "
          f"(up to {max_pages} page(s))")
    print("=" * 72)

    seen: set[str] = set()
    pdp_urls: list[str] = []
    pages_done = 0
    with sync_playwright() as pw:
        log("browser", "connecting to Bright Data Browser API over CDP ...")
        browser = pw.chromium.connect_over_cdp(CDP_ENDPOINT)
        try:
            for pg in range(1, max_pages + 1):
                page = browser.new_page()  # fresh session = one navigation per page
                page.set_default_navigation_timeout(120_000)  # unblocking takes time
                try:
                    if pg == 1:
                        log("browser", "navigating to https://www.amazon.com ...")
                        page.goto("https://www.amazon.com", wait_until="domcontentloaded")
                        try:
                            page.fill("#twotabsearchtextbox", keyword, timeout=15_000)
                            page.click("#nav-search-submit-button", timeout=15_000)
                            log("browser", f"typed '{keyword}' and submitted (page 1)")
                        except Exception:
                            url = f"https://www.amazon.com/s?k={quote_plus(keyword)}"
                            log("browser", f"search box not found — navigating to {url}")
                            page.goto(url, wait_until="domcontentloaded")
                    else:
                        url = f"https://www.amazon.com/s?k={quote_plus(keyword)}&page={pg}"
                        log("browser", f"fetching results page {pg} ...")
                        page.goto(url, wait_until="domcontentloaded")

                    new = 0
                    for asin in _collect_asins_on_page(page):
                        if asin and asin not in seen:
                            seen.add(asin)
                            pdp_urls.append(f"https://www.amazon.com/dp/{asin}")
                            new += 1
                    pages_done = pg
                    log("browser", f"page {pg}: +{new} new PDP URLs (total {len(pdp_urls)})")
                    if new == 0 and pg > 1:
                        log("browser", "no new results — stopping pagination")
                        break
                finally:
                    page.close()
            log("browser", f"collected {len(pdp_urls)} unique PDP URLs across {pages_done} page(s)")
            return pdp_urls
        finally:
            browser.close()
            log("browser", "Browser API session closed")


# --------------------------------------------------------------------------- #
# STAGE 3 · Web Scraper API: trigger collection                                #
# --------------------------------------------------------------------------- #
def trigger_scrape(pdp_urls: list[str]) -> str:
    print("\n" + "=" * 72)
    print("STAGE 3 — Web Scraper API: push PDP URLs to 'Amazon Products by URL'")
    print("=" * 72)

    payload = [{"url": u} for u in pdp_urls]
    log("scraper", f"triggering dataset {AMAZON_DATASET_ID} with {len(payload)} URLs ...")
    resp = requests.post(
        f"{API_BASE}/trigger",
        params={"dataset_id": AMAZON_DATASET_ID, "include_errors": "true", "format": "json"},
        headers={**AUTH_HEADER, "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    snapshot_id = resp.json()["snapshot_id"]
    log("scraper", f"snapshot_id = {snapshot_id}")
    return snapshot_id


# --------------------------------------------------------------------------- #
# STAGE 4 · Web Scraper API: poll progress                                     #
# --------------------------------------------------------------------------- #
def wait_until_ready(snapshot_id: str, poll_every: int = 10, timeout_s: int = 600) -> None:
    print("\n" + "=" * 72)
    print("STAGE 4 — Web Scraper API: poll snapshot progress until 'ready'")
    print("=" * 72)

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = _get_with_retry(f"{API_BASE}/progress/{snapshot_id}").json().get("status")
        log("scraper", f"status = {status}")
        if status == "ready":
            return
        if status == "failed":
            raise RuntimeError(f"snapshot {snapshot_id} failed")
        time.sleep(poll_every)
    raise TimeoutError(f"snapshot {snapshot_id} not ready after {timeout_s}s")


# --------------------------------------------------------------------------- #
# STAGE 5 · Web Scraper API: download structured records                       #
# --------------------------------------------------------------------------- #
def download_results(snapshot_id: str) -> list[dict]:
    print("\n" + "=" * 72)
    print("STAGE 5 — Web Scraper API: download structured product JSON")
    print("=" * 72)

    data = _get_with_retry(f"{API_BASE}/snapshot/{snapshot_id}", params={"format": "json"}, timeout=120).json()
    data = data if isinstance(data, list) else [data]
    log("scraper", f"downloaded {len(data)} product records")
    return data


# --------------------------------------------------------------------------- #
# Single flow: stitch all five stages together                                 #
# --------------------------------------------------------------------------- #
def run(keyword: str, max_pdps: int, max_pages: int = 1) -> int:
    if "<id>" in BROWSER_AUTH or BRIGHTDATA_API_TOKEN == "YOUR_API_TOKEN":
        sys.exit(
            "✗ Set credentials first (copy .env.example → .env, or export):\n"
            "    BROWSER_AUTH='brd-customer-<id>-zone-<zone>:<password>'\n"
            "    BRIGHTDATA_API_TOKEN='<api-token>'"
        )

    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ---- discover → collect ----
    pdp_urls = discover_pdp_urls(keyword, max_pages=max_pages)
    if not pdp_urls:
        sys.exit("✗ No PDP URLs found — check that the search rendered results.")

    if max_pdps and len(pdp_urls) > max_pdps:
        log("flow", f"capping {len(pdp_urls)} → {max_pdps} PDPs for the demo (set --max-pdps 0 for all)")
        pdp_urls = pdp_urls[:max_pdps]

    (OUTPUT_DIR / f"pdp_urls_{stamp}.json").write_text(json.dumps(pdp_urls, indent=2))
    print("\n  PDP URLs handed to the Web Scraper:")
    for u in pdp_urls:
        print(f"    • {u}")

    # ---- push → poll → download ----
    snapshot_id = trigger_scrape(pdp_urls)
    wait_until_ready(snapshot_id)
    products = download_results(snapshot_id)

    out_path = OUTPUT_DIR / f"amazon_products_{stamp}.json"
    out_path.write_text(json.dumps(products, ensure_ascii=False, indent=2))

    print("\n" + "=" * 72)
    print(f"RESULT — {len(products)} products  (single flow complete ✓)")
    print("=" * 72)
    for prod in products[:10]:
        title = (prod.get("title") or "")[:50]
        price = prod.get("final_price") or prod.get("price") or "?"
        cur = prod.get("currency", "")
        print(f"  • {str(prod.get('asin','?')):<12} | {str(price):>8} {cur} | ★{prod.get('rating','?')} | {title}")
    if len(products) > 10:
        print(f"      ... and {len(products) - 10} more")
    print(f"\n  Full JSON → {out_path}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Bright Data Amazon single-flow demo (v3)")
    ap.add_argument("--keyword", default=os.environ.get("SEARCH_KEYWORD", "lenovo thinkpad"))
    ap.add_argument("--max-pdps", type=int, default=int(os.environ.get("MAX_PDPS", "5")),
                    help="cap PDPs pushed to the scraper (0 = all). Keeps the live demo fast.")
    ap.add_argument("--max-pages", type=int, default=int(os.environ.get("MAX_PAGES", "1")),
                    help="how many Amazon results pages to crawl (1 = first page; raise to collect all).")
    args = ap.parse_args()
    raise SystemExit(run(args.keyword, args.max_pdps, args.max_pages))


if __name__ == "__main__":
    main()
