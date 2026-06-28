# Expected Output — "did it work?" reference

Run each demo locally and compare against the samples below. Numbers (bytes, seconds,
prices, ASINs) will differ — match the **shape** and the **success markers** (✅).

---

## Demo 1 — Unblocking Ladder

```
$ python unblocking_ladder.py --url "https://www.amazon.com/s?k=lenovo+thinkpad"

==============================================================================
  THE UNBLOCKING LADDER  →  https://www.amazon.com/s?k=lenovo+thinkpad
==============================================================================

  Method              Status   Bytes     Blocked?  Secs   Note
  ----------------------------------------------------------------------------
  1 · Plain requests  503      4521      BLOCKED   0.6    library UA, no proxy
  2 · Web Unlocker    200      612043    ok        3.4    zone=web_unlocker1
  3 · Browser API     200      1284922   ok        7.1    screenshot saved · title: Amazon.com : lenovo thinkpad

  Takeaway: the delta between rung 1 and rungs 2-3 is the Task 1 story —
  managed unblocking handles all 5 anti-bot layers, not just the IP.
```

**Success markers ✅**
- Rung 1 shows `BLOCKED` (status 503/403, or a Robot-Check body). *Occasionally it slips through —
  re-run, or point `--url` at a specific PDP, to get a reliable block.*
- Rung 2 `ok`, large byte count (full HTML, ~300KB–1MB+).
- Rung 3 `ok`, even larger byte count, and a file **`rung3_browser_api.png`** appears in the folder.
- The "Note" on rung 3 shows a real page `title:` — proof the page actually rendered.

**Reading it for the customer:** "Rung 1 is what Sarah hits today; rungs 2–3 are the two managed
fixes — HTML-only vs full browser."

| If you see… | Meaning | Fix |
| --- | --- | --- |
| Rung 2 `status skip` | `BRIGHTDATA_API_TOKEN` not set | fill `.env` |
| Rung 2 `403 / Forbidden` | wrong `UNLOCKER_ZONE` name | match the zone name in your dashboard |
| Rung 3 `skip` | `BROWSER_AUTH` not set | fill `.env` with the Browser API zone string |
| Rung 3 `ERR 407` | wrong port / creds | port must be **9222**; check `brd-customer-…-zone-…:pwd` |
| Rung 1 shows `ok` | anti-bot let it through this time | re-run or use a harder URL — narrate that it's probabilistic |

---

## Demo 2 — Browser API → Web Scraper (single flow)

```
$ python amazon_flow.py --keyword "lenovo thinkpad" --max-pdps 5 --max-pages 1

========================================================================
STAGE 1·2 — Browser API: search Amazon for 'lenovo thinkpad', collect PDP URLs (up to 1 page(s))
========================================================================
[10:14:02] [browser] connecting to Bright Data Browser API over CDP ...
[10:14:05] [browser] navigating to https://www.amazon.com ...
[10:14:09] [browser] typed 'lenovo thinkpad' and submitted (page 1)
[10:14:13] [browser] page 1: +22 new PDP URLs (total 22)
[10:14:13] [browser] collected 22 unique PDP URLs across 1 page(s)
[10:14:13] [browser] Browser API session closed
[10:14:13] [flow   ] capping 22 → 5 PDPs for the demo (set --max-pdps 0 for all)

  PDP URLs handed to the Web Scraper:
    • https://www.amazon.com/dp/B0CX23V2ZK
    • https://www.amazon.com/dp/B0BS4BP8FB
    • https://www.amazon.com/dp/B0D9J9K2L3
    • https://www.amazon.com/dp/B0C7KMR9MN
    • https://www.amazon.com/dp/B09XYZ1234

========================================================================
STAGE 3 — Web Scraper API: push PDP URLs to 'Amazon Products by URL'
========================================================================
[10:14:13] [scraper] triggering dataset gd_l7q7dkf244hwjntr0 with 5 URLs ...
[10:14:14] [scraper] snapshot_id = s_lq8x2k9p0z

========================================================================
STAGE 4 — Web Scraper API: poll snapshot progress until 'ready'
========================================================================
[10:14:24] [scraper] status = running
[10:14:34] [scraper] status = running
[10:14:44] [scraper] status = ready

========================================================================
STAGE 5 — Web Scraper API: download structured product JSON
========================================================================
[10:14:45] [scraper] downloaded 5 product records

========================================================================
RESULT — 5 products  (single flow complete ✓)
========================================================================
  • B0CX23V2ZK   |  1399.99 USD | ★4.6 | Lenovo ThinkPad X1 Carbon Gen 11 14" ...
  • B0BS4BP8FB   |   929.00 USD | ★4.4 | Lenovo ThinkPad E16 Business Laptop ...
  • B0D9J9K2L3   |  1649.00 USD | ★4.7 | Lenovo ThinkPad P16s Mobile Workstation ...
  • B0C7KMR9MN   |   749.99 USD | ★4.3 | Lenovo ThinkPad L14 Gen 4 ...
  • B09XYZ1234   |  2099.00 USD | ★4.8 | Lenovo ThinkPad X1 Yoga Gen 8 ...

  Full JSON → .../output/amazon_products_20260621_101445.json
```

**Success markers ✅**
- Stage 1 collects a double-digit count of PDP URLs, then caps to 5.
- A `snapshot_id` comes back from `/trigger`.
- Polling flips `running → ready` (usually 1–3 cycles; large jobs take longer).
- Stage 5 downloads the same number of records you sent.
- Two files in `output/`: `pdp_urls_*.json` and `amazon_products_*.json`.

**Sample record in `amazon_products_*.json`** (fields vary; this is the shape):
```json
{
  "title": "Lenovo ThinkPad X1 Carbon Gen 11 14\" Laptop ...",
  "asin": "B0CX23V2ZK",
  "brand": "Lenovo",
  "final_price": 1399.99,
  "currency": "USD",
  "rating": 4.6,
  "reviews_count": 312,
  "availability": "In Stock",
  "url": "https://www.amazon.com/dp/B0CX23V2ZK",
  "image": "https://m.media-amazon.com/images/I/...jpg"
}
```

| If you see… | Meaning | Fix |
| --- | --- | --- |
| `[browser] search box not found — navigating to /s?k=...` | Amazon A/B layout — **this is fine**, the fallback kicked in | nothing |
| `ERR 407` on connect | wrong port/creds | port **9222**; verify `BROWSER_AUTH` |
| `TimeoutError` waiting for results | hard unblock / slow target | re-run; timeout is already 120s |
| trigger `401 Unauthorized` | bad API token | check `BRIGHTDATA_API_TOKEN` |
| trigger `400 / unknown dataset` | wrong dataset id | confirm `AMAZON_DATASET_ID` in your dashboard |
| status stuck on `running` a while | normal for bigger batches | wait; `--max-pdps 5` keeps it short |
| records have `warning`/`error` fields | a URL had an issue (we set `include_errors=true`) | expected; good observability |

---

## Demo 3 — MCP + Agent (Claude Desktop / Cursor)

**Success markers ✅ — before you prompt**
- After adding the config and restarting, you see a **tools / connector icon** showing the
  **Bright Data** server connected, exposing tools like `search_engine`, `scrape_as_markdown`,
  `web_data_amazon_product`, etc.

**What a good run looks like** (warm-up prompt):

> **You:** Using the Bright Data tools, scrape `https://www.amazon.com/s?k=lenovo+thinkpad` and
> list the first 5 products as a JSON array with title, price, rating, url.
>
> **Claude:** *→ calls tool `scrape_as_markdown` (Bright Data)*  ⏳
> *→ tool returns page content*
>
> Here are the first 5 results:
> ```json
> [
>   {"title": "Lenovo ThinkPad X1 Carbon Gen 11 ...", "price": "$1,399.99", "rating": 4.6, "url": "https://www.amazon.com/dp/B0CX23V2ZK"},
>   {"title": "Lenovo ThinkPad E16 ...",             "price": "$929.00",   "rating": 4.4, "url": "https://www.amazon.com/dp/B0BS4BP8FB"},
>   {"title": "Lenovo ThinkPad P16s ...",            "price": "$1,649.00", "rating": 4.7, "url": "https://www.amazon.com/dp/B0D9J9K2L3"},
>   {"title": "Lenovo ThinkPad L14 Gen 4 ...",       "price": "$749.99",   "rating": 4.3, "url": "https://www.amazon.com/dp/B0C7KMR9MN"},
>   {"title": "Lenovo ThinkPad X1 Yoga Gen 8 ...",   "price": "$2,099.00", "rating": 4.8, "url": "https://www.amazon.com/dp/B09XYZ1234"}
> ]
> ```

**Success markers ✅ — during the run**
- You can **see** the agent invoke a Bright Data tool (a tool-call line/expandable block appears).
- It returns real, current data as structured JSON — no proxies, selectors, or CAPTCHAs in your prompt.
- It costs credits from the free 5,000/month pool (base tools = 1 credit/request).

**The line to say:** "I never mentioned proxies or parsing — the agent just called a tool, and
Bright Data handled access *and* extraction. That's the Task 3 future: parsing is a commodity the
model does for free; trusted, compliant access is the durable value."

| If you see… | Meaning | Fix |
| --- | --- | --- |
| No Bright Data tools appear | server not loaded | restart the app; check JSON path & that Node is installed |
| `Invalid/again token` or 401 | bad API token | replace `YOUR_BRIGHTDATA_API_TOKEN` (or the `?token=` in the hosted URL) |
| "tool not available" for browser actions | needs Pro mode | set `PRO_MODE=true` in the config (uses more credits) |
| Agent answers from memory, no tool call | it didn't use the tool | re-prompt: "**Use the Bright Data tools** to fetch live data, don't answer from memory." |

---

## 30-second pre-demo health check
1. `python unblocking_ladder.py` → rung 2 or 3 shows `ok`  → **API token + a zone work.**
2. `python amazon_flow.py --max-pdps 3` → ends with `RESULT — 3 products ✓`  → **full flow works.**
3. Open Claude Desktop → Bright Data tools visible → run the warm-up prompt  → **MCP works.**

If all three pass, you're demo-ready. Run them once right before the meeting to warm credentials.
