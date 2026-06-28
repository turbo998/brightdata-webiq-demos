#!/usr/bin/env python3
"""
DEMO 1 — Task 1 · "The Unblocking Ladder"
=========================================
Hit ONE target (amazon.com) three ways and print a side-by-side scorecard.
This makes the Task 1 thesis tangible: a raw request gets blocked; a clean IP
isn't enough on its own; managed unblocking (Unlocker / Browser API) gets through.

  Rung 1 · Plain requests   — no proxy, library User-Agent  → usually blocked
  Rung 2 · Web Unlocker API — URL in, unblocked HTML out     → success, no browser
  Rung 3 · Browser API      — real cloud Chrome over CDP     → success + screenshot

Run:
    pip install -r ../requirements.txt
    python -m playwright install chromium
    cp ../.env.example .env            # fill in BRIGHTDATA_API_TOKEN, UNLOCKER_ZONE, BROWSER_AUTH
    python unblocking_ladder.py --url "https://www.amazon.com/s?k=lenovo+thinkpad"

Notes
- Anti-bot is probabilistic. A single plain request may occasionally succeed; run a
  few times (or point at a hard PDP) to see the contrast. The teaching point is the
  delta between the rungs, narrated live.
- Stays on PUBLIC pages only — the compliant, defensible position from Task 1/Task 3.
"""
from __future__ import annotations
import argparse, os, time, requests
from playwright.sync_api import sync_playwright
try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass

API_TOKEN   = os.environ.get("BRIGHTDATA_API_TOKEN", "")
UNLOCKER_ZONE = os.environ.get("UNLOCKER_ZONE", "web_unlocker1")
BROWSER_AUTH = os.environ.get("BROWSER_AUTH", "")
CDP = f"wss://{BROWSER_AUTH}@{os.environ.get('BROWSER_HOST','brd.superproxy.io')}:{os.environ.get('BROWSER_PORT','9222')}"

BLOCK_MARKERS = [
    "robot check", "captcha", "to discuss automated access",
    "enter the characters you see below", "are you a human", "access denied",
    "sorry, we just need to make sure you're not a robot",
]

def looks_blocked(status: int, body: str) -> bool:
    if status >= 400:
        return True
    low = (body or "").lower()
    return any(m in low for m in BLOCK_MARKERS)

def rung1_plain(url: str) -> dict:
    t = time.time()
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "python-requests/2.31"})
        body = r.text
        return {"method": "1 · Plain requests", "status": r.status_code,
                "bytes": len(body), "blocked": looks_blocked(r.status_code, body),
                "secs": round(time.time() - t, 1), "note": "library UA, no proxy"}
    except Exception as e:
        return {"method": "1 · Plain requests", "status": "ERR", "bytes": 0,
                "blocked": True, "secs": round(time.time() - t, 1), "note": type(e).__name__}

def rung2_unlocker(url: str) -> dict:
    t = time.time()
    if not API_TOKEN:
        return {"method": "2 · Web Unlocker", "status": "skip", "bytes": 0, "blocked": None,
                "secs": 0, "note": "set BRIGHTDATA_API_TOKEN"}
    try:
        r = requests.post(
            "https://api.brightdata.com/request",
            headers={"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"},
            json={"zone": UNLOCKER_ZONE, "url": url, "format": "raw"},
            timeout=90,
        )
        body = r.text
        return {"method": "2 · Web Unlocker", "status": r.status_code, "bytes": len(body),
                "blocked": looks_blocked(r.status_code, body), "secs": round(time.time() - t, 1),
                "note": f"zone={UNLOCKER_ZONE}"}
    except Exception as e:
        return {"method": "2 · Web Unlocker", "status": "ERR", "bytes": 0, "blocked": True,
                "secs": round(time.time() - t, 1), "note": type(e).__name__}

def rung3_browser(url: str) -> dict:
    t = time.time()
    if "<id>" in BROWSER_AUTH or not BROWSER_AUTH:
        return {"method": "3 · Browser API", "status": "skip", "bytes": 0, "blocked": None,
                "secs": 0, "note": "set BROWSER_AUTH"}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(CDP)
            page = browser.new_page()
            page.set_default_navigation_timeout(120_000)
            page.goto(url, wait_until="domcontentloaded")
            html = page.content()
            title = page.title()
            page.screenshot(path="rung3_browser_api.png", full_page=False)
            browser.close()
        return {"method": "3 · Browser API", "status": 200, "bytes": len(html),
                "blocked": looks_blocked(200, html), "secs": round(time.time() - t, 1),
                "note": f"screenshot saved · title: {title[:32]}"}
    except Exception as e:
        return {"method": "3 · Browser API", "status": "ERR", "bytes": 0, "blocked": True,
                "secs": round(time.time() - t, 1), "note": type(e).__name__}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://www.amazon.com/s?k=lenovo+thinkpad")
    args = ap.parse_args()

    print("\n" + "=" * 78)
    print(f"  THE UNBLOCKING LADDER  →  {args.url}")
    print("=" * 78)
    rows = [rung1_plain(args.url), rung2_unlocker(args.url), rung3_browser(args.url)]

    print(f"\n  {'Method':<20}{'Status':<9}{'Bytes':<10}{'Blocked?':<10}{'Secs':<7}Note")
    print("  " + "-" * 76)
    for r in rows:
        blocked = {True: "BLOCKED", False: "ok", None: "-"}[r["blocked"]]
        print(f"  {r['method']:<20}{str(r['status']):<9}{str(r['bytes']):<10}{blocked:<10}{str(r['secs']):<7}{r['note']}")
    print("\n  Takeaway: the delta between rung 1 and rungs 2-3 is the Task 1 story —")
    print("  managed unblocking handles all 5 anti-bot layers, not just the IP.\n")

if __name__ == "__main__":
    main()
