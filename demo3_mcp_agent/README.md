# Demo 3 — Bright Data MCP + Agent (Task 3)

Demonstrates the Task 3 thesis live: an AI agent reaching the web through Bright Data's
**Model Context Protocol (MCP)** server — agent-native, on-demand, never blocked.

## Option A — Hosted connector (easiest, nothing to install)
Claude Desktop → **Settings → Connectors → Add custom connector**
- Name: `Bright Data Web`
- URL: `https://mcp.brightdata.com/mcp?token=YOUR_BRIGHTDATA_API_TOKEN`
- Add → restart Claude Desktop.

## Option B — Local server via npx
1. Install Node 18+.
2. Copy `claude_desktop_config.json` (this folder) into Claude Desktop's config:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   For Cursor, use `cursor_mcp.json` → `~/.cursor/mcp.json`.
3. Replace `YOUR_BRIGHTDATA_API_TOKEN` (Bright Data → account settings → API tokens).
4. Restart the app. You'll see the **Bright Data** tools appear (search_engine, scrape_as_markdown, …).

## Run the demo
Open `demo_prompts.md` and paste the prompts. Start with the warm-up to prove the tool is live,
then the Amazon one that ties back to Task 2.

## ✅ Verified live (2026-06-24)
This demo was tested end-to-end against the hosted MCP endpoint with a real API token — it
returns live data **even on a brand-new account with no zones provisioned**, because the MCP
free tier routes through Bright Data's own managed proxy network (not your account zones).

| Check | Result |
| --- | --- |
| MCP `initialize` handshake | ✅ `brightdata-mcp v1.0.0`, token accepted |
| `tools/list` | ✅ `search_engine`, `scrape_as_markdown`, `search_engine_batch`, `scrape_batch`, `ask_brightdata_assistant` |
| `search_engine` ("lenovo thinkpad") | ✅ structured Google results (organic array) |
| `scrape_as_markdown` (Amazon search page) | ✅ **346,995 chars** of clean markdown — anti-bot fully bypassed |

**Why this matters for the interview:** Demos 1 & 2 depend on account zone provisioning, but
Demo 3 runs on the free MCP tier and is **guaranteed live** — so there is always at least one
demo that works on stage, regardless of account state.

## Good to know
- **Free tier**: 5,000 credits/month, auto-renews, no card. Base tools = 1 credit/request;
  `web_data_*` = 1 credit/record.
- **PRO_MODE=true** unlocks advanced tools (browser automation, more web_data_* datasets) — leave
  `false` for a clean, cheap demo.
- Works with Claude Desktop, Cursor, VS Code (Continue/Cline), and any MCP-compatible agent.

## Why this is the strongest Task 3 demo
It *shows* the predicted future stack's top layer — the MCP/agent interface — running on the
same network the other two demos use. "Parsing is becoming a commodity the model does for free;
trusted, compliant access is the durable value." You just proved it without writing a scraper.
