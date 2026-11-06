import urllib.request, json, collections
out = []
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "primo-family-app/1.0"}), timeout=30) as r: return json.load(r)
for s in ["KXNBAPTS", "KXNBAREB", "KXNFLRECYDS", "KXNHLPTS"]:
    d = get("https://api.elections.kalshi.com/trade-api/v2/markets?limit=1000&status=open&series_ticker=" + s)
    ms = d.get("markets", [])
    c = collections.Counter(m["event_ticker"] for m in ms)
    out.append(f"{s}: {len(ms)} open; events {dict(list(c.items())[:12])}")
    if ms: out.append("  sample " + json.dumps({k: ms[0].get(k) for k in ("ticker", "yes_sub_title", "volume", "yes_bid", "yes_ask", "open_time")}))
open("probe.txt", "w").write("\n".join(out))
