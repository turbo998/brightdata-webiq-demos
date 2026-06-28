/**
 * Bright Data — Solutions Architect Assignment · Task 2 (v3, Node/JS parity)
 * =========================================================================
 * Single flow: discover → collect → trigger → poll → download.
 * Mirrors amazon_flow.py. Uses Playwright over CDP + the Web Scraper API.
 *
 *   npm install playwright
 *   npx playwright install chromium     # only for a local fallback
 *   cp .env.example .env                 # then fill in credentials
 *   node amazon_flow.js "lenovo thinkpad" 5
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
require("dotenv").config?.();

const BROWSER_AUTH = process.env.BROWSER_AUTH || "brd-customer-<id>-zone-<zone>:<password>";
const TOKEN = process.env.BRIGHTDATA_API_TOKEN || "YOUR_API_TOKEN";
const DATASET_ID = process.env.AMAZON_DATASET_ID || "gd_l7q7dkf244hwjntr0";
const HOST = process.env.BROWSER_HOST || "brd.superproxy.io";
const PORT = process.env.BROWSER_PORT || "9222";
const CDP = `wss://${BROWSER_AUTH}@${HOST}:${PORT}`;
const BASE = "https://api.brightdata.com/datasets/v3";
const AUTH = { Authorization: `Bearer ${TOKEN}` };

const log = (stage, msg) =>
  console.log(`[${new Date().toLocaleTimeString()}] [${stage.padEnd(7)}] ${msg}`);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---- Stage 1+2: Browser API ----
async function collectAsinsOnPage(page) {
  await page.waitForSelector('div[data-component-type="s-search-result"]', { timeout: 60_000 });
  const asins = await page.$$eval(
    'div[data-component-type="s-search-result"][data-asin]',
    (els) => els.map((e) => e.getAttribute("data-asin")).filter(Boolean)
  );
  const hrefs = await page.$$eval("a[href*='/dp/']", (els) => els.map((e) => e.getAttribute("href")));
  for (const h of hrefs) {
    const m = (h || "").match(/\/dp\/([A-Z0-9]{10})/);
    if (m) asins.push(m[1]);
  }
  return asins;
}

// Browser API allows one navigation per session, so we open a fresh page per
// results page: page 1 via the real search box (with /s?k= fallback), pages 2+
// straight to /s?k=<kw>&page=N. Raise maxPages to collect ALL results.
async function discoverPdpUrls(keyword, maxPages = 1) {
  console.log("\n" + "=".repeat(72));
  console.log(`STAGE 1·2 — Browser API: search Amazon for '${keyword}', collect PDP URLs (up to ${maxPages} page(s))`);
  console.log("=".repeat(72));

  log("browser", "connecting to Browser API over CDP ...");
  const browser = await chromium.connectOverCDP(CDP);
  const seen = new Set();
  const pdp = [];
  let pagesDone = 0;
  try {
    for (let pg = 1; pg <= maxPages; pg++) {
      const page = await browser.newPage();
      page.setDefaultNavigationTimeout(120_000);
      try {
        if (pg === 1) {
          log("browser", "navigating to https://www.amazon.com ...");
          await page.goto("https://www.amazon.com", { waitUntil: "domcontentloaded" });
          try {
            await page.fill("#twotabsearchtextbox", keyword, { timeout: 15_000 });
            await page.click("#nav-search-submit-button", { timeout: 15_000 });
            log("browser", `typed '${keyword}' and submitted (page 1)`);
          } catch {
            const url = `https://www.amazon.com/s?k=${encodeURIComponent(keyword)}`;
            log("browser", `search box not found — navigating to ${url}`);
            await page.goto(url, { waitUntil: "domcontentloaded" });
          }
        } else {
          const url = `https://www.amazon.com/s?k=${encodeURIComponent(keyword)}&page=${pg}`;
          log("browser", `fetching results page ${pg} ...`);
          await page.goto(url, { waitUntil: "domcontentloaded" });
        }

        let added = 0;
        for (const a of await collectAsinsOnPage(page)) {
          if (a && !seen.has(a)) {
            seen.add(a);
            pdp.push(`https://www.amazon.com/dp/${a}`);
            added++;
          }
        }
        pagesDone = pg;
        log("browser", `page ${pg}: +${added} new PDP URLs (total ${pdp.length})`);
        if (added === 0 && pg > 1) {
          log("browser", "no new results — stopping pagination");
          await page.close();
          break;
        }
      } finally {
        await page.close();
      }
    }
    log("browser", `collected ${pdp.length} unique PDP URLs across ${pagesDone} page(s)`);
    return pdp;
  } finally {
    await browser.close();
    log("browser", "Browser API session closed");
  }
}

// ---- Stage 3: trigger ----
async function triggerScrape(pdpUrls) {
  console.log("\n" + "=".repeat(72));
  console.log("STAGE 3 — Web Scraper API: trigger 'Amazon Products by URL'");
  console.log("=".repeat(72));
  const qs = new URLSearchParams({ dataset_id: DATASET_ID, include_errors: "true", format: "json" });
  const res = await fetch(`${BASE}/trigger?${qs}`, {
    method: "POST",
    headers: { ...AUTH, "Content-Type": "application/json" },
    body: JSON.stringify(pdpUrls.map((u) => ({ url: u }))),
  });
  if (!res.ok) throw new Error(`trigger failed: ${res.status}`);
  const { snapshot_id } = await res.json();
  log("scraper", `snapshot_id = ${snapshot_id}`);
  return snapshot_id;
}

// ---- Stage 4: poll ----
async function waitUntilReady(snapshot, pollEvery = 10_000, timeoutMs = 600_000) {
  console.log("\n" + "=".repeat(72));
  console.log("STAGE 4 — Web Scraper API: poll until 'ready'");
  console.log("=".repeat(72));
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const res = await fetch(`${BASE}/progress/${snapshot}`, { headers: AUTH });
    const { status } = await res.json();
    log("scraper", `status = ${status}`);
    if (status === "ready") return;
    if (status === "failed") throw new Error(`snapshot ${snapshot} failed`);
    await sleep(pollEvery);
  }
  throw new Error(`snapshot ${snapshot} not ready in time`);
}

// ---- Stage 5: download ----
async function downloadResults(snapshot) {
  console.log("\n" + "=".repeat(72));
  console.log("STAGE 5 — Web Scraper API: download structured JSON");
  console.log("=".repeat(72));
  const res = await fetch(`${BASE}/snapshot/${snapshot}?format=json`, { headers: AUTH });
  const data = await res.json();
  const arr = Array.isArray(data) ? data : [data];
  log("scraper", `downloaded ${arr.length} product records`);
  return arr;
}

(async () => {
  const keyword = process.argv[2] || process.env.SEARCH_KEYWORD || "lenovo thinkpad";
  let maxPdps = parseInt(process.argv[3] || process.env.MAX_PDPS || "5", 10);
  const maxPages = parseInt(process.argv[4] || process.env.MAX_PAGES || "1", 10);
  if (BROWSER_AUTH.includes("<id>") || TOKEN === "YOUR_API_TOKEN") {
    console.error("✗ Set BROWSER_AUTH and BRIGHTDATA_API_TOKEN (copy .env.example → .env).");
    process.exit(1);
  }
  const outDir = path.join(__dirname, "output");
  fs.mkdirSync(outDir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");

  let pdp = await discoverPdpUrls(keyword, maxPages);
  if (!pdp.length) { console.error("✗ No PDP URLs found."); process.exit(1); }
  if (maxPdps && pdp.length > maxPdps) {
    log("flow", `capping ${pdp.length} → ${maxPdps} for the demo (pass 0 for all)`);
    pdp = pdp.slice(0, maxPdps);
  }
  fs.writeFileSync(path.join(outDir, `pdp_urls_${stamp}.json`), JSON.stringify(pdp, null, 2));
  console.log("\n  PDP URLs handed to the Web Scraper:");
  pdp.forEach((u) => console.log(`    • ${u}`));

  const snapshot = await triggerScrape(pdp);
  await waitUntilReady(snapshot);
  const products = await downloadResults(snapshot);

  const outPath = path.join(outDir, `amazon_products_${stamp}.json`);
  fs.writeFileSync(outPath, JSON.stringify(products, null, 2));
  console.log("\n" + "=".repeat(72));
  console.log(`RESULT — ${products.length} products (single flow complete ✓)`);
  console.log("=".repeat(72));
  products.slice(0, 10).forEach((p) =>
    console.log(`  • ${String(p.asin || "?").padEnd(12)} | ${String(p.final_price || p.price || "?").padStart(8)} ${p.currency || ""} | ★${p.rating || "?"} | ${(p.title || "").slice(0, 50)}`)
  );
  console.log(`\n  Full JSON → ${outPath}`);
})().catch((e) => { console.error(e); process.exit(1); });
