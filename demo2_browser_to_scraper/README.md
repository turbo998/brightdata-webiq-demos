# Demo 2 — Browser API → Web Scraper (Task 2)

The assignment's core deliverable: one continuous flow that discovers Amazon PDP links
with the **Browser API**, then pushes them to the **Web Scraper API** and returns clean
structured product data. Python and Node versions included (identical flow).

## Run
```bash
pip install -r ../requirements.txt          # no `playwright install` needed — remote CDP browser
cp ../.env.example .env                       # fill BROWSER_AUTH + BRIGHTDATA_API_TOKEN + AMAZON_DATASET_ID
python amazon_flow.py --keyword "lenovo thinkpad" --max-pdps 5 --max-pages 1
```
Node: `node amazon_flow.js "lenovo thinkpad" 5 1`   (args: keyword, max-pdps, max-pages)

- `--max-pages` = how many Amazon results pages to crawl. `1` = first page (fast demo);
  raise it to **collect all** PDP URLs (each page is a fresh Browser API session, since the API
  allows one navigation per session).
- `--max-pdps` caps how many URLs are pushed to the scraper (keeps the demo cheap); `0` = all.

Outputs land in `output/`: `pdp_urls_*.json` and `amazon_products_*.json`.

## Flow
`search (Browser API) → collect /dp/<ASIN> → trigger (Web Scraper, async) → poll → download`

Full design notes and the "why two products / why async" talk track are in
`../../task2_amazon_flow/README.md` (this is the same code, placed here for a self-contained demo).

## Demo tips
- Pre-run once right before the meeting to warm credentials.
- `--max-pdps 5` keeps it ~1 minute and inside trial credit; use `0` for all URLs in production.
- Keep a good `amazon_products.json` from a prior run open as a backup tab.
