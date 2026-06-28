# Demo 3 — Live prompts (Task 3 · AI-native web access)

Once the MCP server is connected (see README), drive these in **Claude Desktop** or **Cursor**.
The point of the demo: the agent reaches the live web through Bright Data's tools
(`search_engine`, `scrape_as_markdown`, `web_data_*`) and never gets blocked — *this* is the
"future of web scraping" thesis made real: agent-native, on-demand, structured.

## Warm-up — prove the tool is live
> Using the Bright Data tools, scrape https://www.amazon.com/s?k=lenovo+thinkpad and list the
> first 5 products as a JSON array with fields: title, price, rating, url.

## Ties back to Task 2 — same job, zero code
> Search Amazon for "lenovo thinkpad", take the top 5 product URLs, and return a clean JSON
> table with title, ASIN, price, rating, and review count for each.

*(Narrate: "In Task 2 I wrote a script to do exactly this. Here the agent does it through the
same Bright Data engine — no script, just a request. Same platform, two ways to consume it.")*

## Shows live grounding / freshness (RAG point)
> Use the search tool to find the 3 most recent news items about "AI web scraping regulation"
> and summarize each in one sentence with its source link.

## Shows multi-step agent behavior
> Find the current price of the Lenovo ThinkPad X1 Carbon on Amazon, then check whether a
> cheaper listing for the same model exists, and tell me the delta.

## Talking points while it runs
- **No selectors, no proxies, no CAPTCHAs in my prompt** — the agent calls a tool; Bright Data
  handles access + extraction. Parsing has become something the model does for free.
- **MCP = the agent-native interface** from Task 3's predicted stack:
  proxies → unblocking → browser → structured extraction → **MCP/agent interface**.
- **Free tier**: 5,000 credits/month, so the demo costs nothing. Base tools = 1 credit/request.
- **Compliant by design**: public data only; same governance posture as the rest of the platform.

## If asked "how is this different from Browser API?"
Browser API / Agent Browser = you drive a browser from code. MCP = the *LLM* drives Bright Data
tools directly, in natural language. Same underlying network; different altitude of abstraction —
exactly the "right tool, right layer" through-line.
