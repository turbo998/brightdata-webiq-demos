# Bright Data — 4 Demos

Turnkey demos to run live in **VS Code / Claude Code**. Built in Cowork; run them locally
so they reach Bright Data's endpoints with full network access and your real API key.

| Demo | Task | What it shows | Stack |
| --- | --- | --- | --- |
| **demo1_unblocking_ladder** | Task 1 | Same target, 3 rungs: plain request (blocked) → Unlocker → Browser API | Python |
| **demo2_browser_to_scraper** | Task 2 | Single flow: Browser API discovers PDP links → Web Scraper returns JSON | Python + Node |
| **demo3_mcp_agent** | Task 3 | An AI agent scrapes the live web via Bright Data MCP — no code | MCP + Claude Desktop/Cursor |
| **demo4_webiq_vs_brightdata** | Task 3 | One shopping question, two layers chained: Web IQ grounds → Bright Data collects + acts | Python + MCP |

## One-time setup
```bash
# from the demos/ folder
pip install -r requirements.txt
cp .env.example .env        # then fill in your Bright Data credentials
```
Copy `.env` into each demo subfolder that needs it (demo1, demo2). Demo 3 uses a JSON config, not `.env`.

> **No `playwright install` needed.** These demos connect to Bright Data's **remote** cloud
> browser over CDP (`connect_over_cdp`), so no local Chromium is downloaded or launched. You only
> need the `playwright` Python package (in `requirements.txt`). Run `python -m playwright install
> chromium` *only* if you want to test a local-browser fallback.

## Credentials you need (all from your Bright Data dashboard)
- `BRIGHTDATA_API_TOKEN` — account settings → API tokens (used by Unlocker, Web Scraper, MCP)
- `BROWSER_AUTH` — Browser API zone: `brd-customer-<id>-zone-<zone>:<password>`
- `UNLOCKER_ZONE` — the name of your Web Unlocker zone (often `web_unlocker1`)
- `AMAZON_DATASET_ID` — Amazon "Products by URL" scraper (default `gd_l7q7dkf244hwjntr0`)

> Trial note: the support team activates Unlocker, SERP, Browser API and Web Scrapers, plus a $10
> bonus. These demos are designed to stay well inside that (MAX_PDPS=5, MCP free tier 5,000/mo).

## Suggested live order (matches the deck)
1. **Demo 1** after Task 1 — visceral proof that managed unblocking beats a raw request.
2. **Demo 2** for Task 2 — the required single-flow demo.
3. **Demo 3** for Task 3 — the agent-native finale that lands the "future" thesis.

## Why run locally, not in Cowork
- The assignment asks for a "real production environment (e.g. VS Code)."
- Browser API needs `wss://brd.superproxy.io:9222` and the APIs need `api.brightdata.com` — full
  network access on your machine, not a sandbox allowlist.
- Your API key stays in a local `.env`, never pasted into a chat.
