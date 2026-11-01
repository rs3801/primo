import json, urllib.request, time
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "primo-family-app/1.0"}), timeout=60))
    except Exception as e: return {"err": str(e)}
A = "https://api.elections.kalshi.com/trade-api/v2"
out = []
for ev in ["KXNFLGAME-26NOV01LVNYJ", "KXNFLGAME-26NOV01TENCIN"]:
    d = get(A + "/markets?event_ticker=" + ev)
    out.append(ev + " " + json.dumps([{k: m.get(k) for k in ("ticker", "status", "yes_sub_title", "yes_bid_dollars", "yes_ask_dollars", "close_time")} for m in d.get("markets", [])])[:700])
now = int(time.time()); cur = ""; pages = 0; total = 0; first_nfl = None
while pages < 120:
    d = get(A + "/markets?status=open&limit=1000&mve_filter=exclude&min_close_ts=%d&max_close_ts=%d%s" % (now, now + 17*86400, "&cursor=" + cur if cur else ""))
    ms = d.get("markets") or []; pages += 1; total += len(ms)
    for m in ms:
        if m["event_ticker"].startswith("KXNFLGAME-26NOV01") and first_nfl is None: first_nfl = pages
    cur = d.get("cursor") or ""
    if not cur or not ms: break
out.append("pages %d total %d first NFL GAME on page %s" % (pages, total, first_nfl))
open("probe.txt", "w").write("\n".join(out))
