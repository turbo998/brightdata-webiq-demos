# Demo 1 — The Unblocking Ladder (Task 1)

Proves the Task 1 thesis live: a raw request gets blocked, but managed unblocking gets
through — because anti-bot is 5 layers, not just the IP.

## Run
```bash
pip install -r ../requirements.txt          # no `playwright install` needed — remote CDP browser
cp ../.env.example .env                       # fill BRIGHTDATA_API_TOKEN, UNLOCKER_ZONE, BROWSER_AUTH
python unblocking_ladder.py --url "https://www.amazon.com/s?k=lenovo+thinkpad"
```

## What it does
| Rung | Method | Expected |
| --- | --- | --- |
| 1 | Plain `requests` (library UA, no proxy) | often **BLOCKED** (503 / Robot Check) |
| 2 | Web Unlocker API (`POST /request`, `format:raw`) | **ok** — clean HTML, no browser |
| 3 | Browser API (Playwright over CDP) | **ok** — renders + screenshot `rung3_browser_api.png` |

Prints a side-by-side scorecard: status · bytes · blocked? · seconds · note.

## Talk track
"Rung 1 is what Sarah's agents hit today. Rung 2 is the cheapest fix when you only need
HTML. Rung 3 is when the agent has to *act* on the page. Same target, three layers of the
ladder — pick the lowest rung that clears the block."

## Notes
- Anti-bot is probabilistic — run a few times, or point `--url` at a specific PDP, to make
  rung 1's block reliable. The *delta* between rungs is the point.
- `UNLOCKER_ZONE` must match the Web Unlocker zone name in your dashboard (often `web_unlocker1`).
- Public pages only — the compliant position.
