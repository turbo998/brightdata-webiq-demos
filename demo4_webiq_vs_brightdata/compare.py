#!/usr/bin/env python3
"""
Demo 4 · Microsoft Web IQ  vs  Bright Data  —  "same question, two different jobs"
==================================================================================
One shopping-agent question, answered by TWO complementary layers:

  LEFT  · Microsoft Web IQ  (grounding API)
          POST https://api.microsoft.ai/v3/search/web    header:  x-apikey: <KEY>
          → fresh, curated, token-optimized PASSAGES from across the web, with
            attribution.  Fast (p95 ~164 ms).  Answers "what does the web SAY?"
          → NOT deterministic price/ASIN, no site targeting, no page interaction.

  RIGHT · Bright Data        (collection + action layer)
          Browser API (real cloud Chrome) → Web Scraper API (managed parser)
          → deterministic, STRUCTURED product records from the exact pages
            (title, price, ASIN, rating, availability), plus interaction + geo.
          → Answers "what is THIS page right now, and can my agent act on it?"

The point of the demo: these are not competitors — they are layers you chain.
Web IQ for discovery / grounding  →  Bright Data for precise collection + action.

Run:
    cp .env.example .env          # fill in WEBIQ_API_KEY  (+ Bright Data creds for --bd-live)
    python compare.py --query "best Lenovo ThinkPad for travel under $1500" \
                      --keyword "lenovo thinkpad"

Bright Data side:
    • default  → reuse the most recent task2_amazon_flow/output/amazon_products_*.json
                 (instant, still real data you collected earlier).
    • --bd-live → run the real Browser-API → Web-Scraper flow now (slower, fully live).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import textwrap
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars also work without it.

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent  # demos/demo4_.. -> demos -> workspace root
TASK2_DIR = WORKSPACE / "task2_amazon_flow"
TASK2_OUTPUT = TASK2_DIR / "output"
SAMPLE_DATA = HERE / "sample_data"  # bundled fallback so the demo runs standalone

WEBIQ_ENDPOINT = os.environ.get("WEBIQ_ENDPOINT", "https://api.microsoft.ai/v3/search/web")
WEBIQ_API_KEY = os.environ.get("WEBIQ_API_KEY", "")

C_DIM = "\033[2m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RESET = "\033[0m"


def _strip_html(text: str) -> str:
    """Web IQ returns lightly-tagged passages (<H1>, <P>, <A> ...). Flatten for display."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ───────────────────────────────  LEFT · Web IQ  ────────────────────────────────
def webiq_search(query: str, count: int = 5) -> list[dict]:
    """Call the real Web IQ grounding API and return its webResults."""
    if not WEBIQ_API_KEY:
        sys.exit(
            "✗ Set WEBIQ_API_KEY first (copy .env.example → .env, or export):\n"
            "    WEBIQ_API_KEY='<your-web-iq-key>'"
        )

    headers = {"x-apikey": WEBIQ_API_KEY, "Content-Type": "application/json"}
    # Web IQ takes a natural-language query; count caps how many passages come back.
    payload = {"query": query, "count": count}

    print(f"{C_CYAN}[Web IQ]{C_RESET} POST {WEBIQ_ENDPOINT}")
    print(f"{C_CYAN}[Web IQ]{C_RESET} query = {query!r}")
    resp = requests.post(WEBIQ_ENDPOINT, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("webResults") or data.get("results") or []
    print(f"{C_CYAN}[Web IQ]{C_RESET} {len(results)} grounded passages returned "
          f"({resp.elapsed.total_seconds() * 1000:.0f} ms)\n")
    return results


def print_webiq(results: list[dict]) -> None:
    print(f"{C_CYAN}{'═' * 72}{C_RESET}")
    print(f"{C_CYAN}LEFT · Microsoft Web IQ — \"what does the web say?\"{C_RESET}")
    print(f"{C_CYAN}{'═' * 72}{C_RESET}")
    if not results:
        print(f"  {C_DIM}(no passages){C_RESET}\n")
        return
    for i, r in enumerate(results, 1):
        title = r.get("title", "(untitled)")
        url = r.get("url", "")
        snippet = _strip_html(r.get("content", ""))[:280]
        print(f"  {C_GREEN}{i}. {title}{C_RESET}")
        print(f"     {C_DIM}{url}{C_RESET}")
        for line in textwrap.wrap(snippet, width=66):
            print(f"     {line}")
        print()


# ─────────────────────────────  RIGHT · Bright Data  ────────────────────────────
def brightdata_cached() -> list[dict] | None:
    """Reuse the most recent structured product JSON collected by task2_amazon_flow.

    Falls back to the bundled sample_data/ collection so the demo runs standalone.
    """
    files = sorted(glob.glob(str(TASK2_OUTPUT / "amazon_products_*.json")))
    if not files:
        files = sorted(glob.glob(str(SAMPLE_DATA / "amazon_products_*.json")))
    if not files:
        return None
    latest = files[-1]
    print(f"{C_YELLOW}[Bright Data]{C_RESET} reusing cached collection → {Path(latest).name}\n")
    return json.loads(Path(latest).read_text(encoding="utf-8"))


def brightdata_live(keyword: str, max_pdps: int) -> list[dict]:
    """Run the real Browser-API → Web-Scraper flow and return structured products."""
    sys.path.insert(0, str(TASK2_DIR))
    import amazon_flow  # noqa: E402  (validated module reused as-is)

    print(f"{C_YELLOW}[Bright Data]{C_RESET} live flow: Browser API → Web Scraper API ...\n")
    urls = amazon_flow.discover_pdp_urls(keyword, max_pages=1)
    if not urls:
        sys.exit("✗ Bright Data: no PDP URLs found.")
    if max_pdps and len(urls) > max_pdps:
        urls = urls[:max_pdps]
    snapshot_id = amazon_flow.trigger_scrape(urls)
    amazon_flow.wait_until_ready(snapshot_id)
    return amazon_flow.download_results(snapshot_id)


def print_brightdata(products: list[dict]) -> None:
    print(f"{C_YELLOW}{'═' * 72}{C_RESET}")
    print(f"{C_YELLOW}RIGHT · Bright Data — \"what is THIS page right now?\"{C_RESET}")
    print(f"{C_YELLOW}{'═' * 72}{C_RESET}")
    if not products:
        print(f"  {C_DIM}(no products — run with --bd-live or collect task2 output first){C_RESET}\n")
        return
    print(f"  {'ASIN':<12} | {'PRICE':>10} | {'RATING':>6} | TITLE")
    print(f"  {'-' * 12}-+-{'-' * 10}-+-{'-' * 6}-+-{'-' * 34}")
    for p in products[:10]:
        asin = str(p.get("asin", "?"))
        price = p.get("final_price") or p.get("price") or "?"
        cur = p.get("currency", "")
        rating = p.get("rating", "?")
        title = (p.get("title") or "")[:34]
        print(f"  {asin:<12} | {str(price):>7} {cur:<2} | {'★' + str(rating):>6} | {title}")
    if len(products) > 10:
        print(f"      ... and {len(products) - 10} more")
    print()


# ───────────────────────────────────  main  ─────────────────────────────────────
def print_summary(query: str, keyword: str) -> None:
    print(f"{'═' * 72}")
    print("SAME QUESTION → TWO DIFFERENT JOBS")
    print(f"{'═' * 72}")
    rows = [
        ("primitive",        "natural-language grounding",   "site collection + browser action"),
        ("you specify",      "a question",                   "target sites / URLs / interactions"),
        ("output",           "curated passages + attribution", "deterministic structured records"),
        ("freshness/price",  "'what the web says'",          "exact price/ASIN/stock right now"),
        ("interaction",      "none",                         "click, search, login, checkout"),
        ("geo / anti-bot",   "handled, opaque",              "geo-targeted, unblock 5-layer defense"),
        ("latency",          "~164 ms p95",                  "seconds–minutes (real collection)"),
        ("best for",         "discovery / RAG grounding",    "precise data + agent actions"),
    ]
    print(f"  {'':<16} | {'Web IQ':<32} | Bright Data")
    print(f"  {'-' * 16}-+-{'-' * 32}-+-{'-' * 34}")
    for label, a, b in rows:
        print(f"  {label:<16} | {a:<32} | {b}")
    print()
    print(f"  {C_GREEN}Chain them:{C_RESET} Web IQ grounds the agent on \"{query}\"")
    print(f"             → Bright Data then collects + acts on the exact \"{keyword}\" pages.")
    print(f"  Web IQ answers \"what does the web say?\";")
    print(f"  Bright Data answers \"what is this specific page now, and can my agent act on it?\"")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(description="Web IQ vs Bright Data — complementary-layers demo")
    ap.add_argument("--query", default="best Lenovo ThinkPad for travel under $1500",
                    help="natural-language question for Web IQ grounding")
    ap.add_argument("--keyword", default="lenovo thinkpad",
                    help="product keyword for Bright Data collection")
    ap.add_argument("--count", type=int, default=5, help="Web IQ passages to request")
    ap.add_argument("--max-pdps", type=int, default=5, help="cap PDPs in --bd-live mode")
    ap.add_argument("--bd-live", action="store_true",
                    help="run the real Bright Data flow now instead of reusing cached output")
    args = ap.parse_args()

    # LEFT — real Web IQ call
    webiq_results = webiq_search(args.query, count=args.count)
    print_webiq(webiq_results)

    # RIGHT — Bright Data (cached by default, live on request)
    if args.bd_live:
        products = brightdata_live(args.keyword, args.max_pdps)
    else:
        products = brightdata_cached() or []
        if not products:
            print(f"{C_YELLOW}[Bright Data]{C_RESET} no cached output found — "
                  f"re-run with --bd-live to collect live.\n")
    print_brightdata(products)

    print_summary(args.query, args.keyword)


if __name__ == "__main__":
    main()
