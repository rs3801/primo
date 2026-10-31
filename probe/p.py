import json, urllib.request
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "primo-family-app/1.0"}), timeout=30))
    except Exception as e: return {"err": str(e)}
A = "https://api.elections.kalshi.com/trade-api/v2"
out = []; cur = ""
for i in range(5):
    d = get(A + "/events?series_ticker=KXNCAAFGAME&limit=200" + ("&cursor=" + cur if cur else ""))
    for e in d.get("events", []):
        if "26OCT31" in e["event_ticker"] and any(x in e["event_ticker"] for x in ("MICH", "SYR", "RUTG")): out.append(e["event_ticker"] + " " + str(e.get("title")))
    cur = d.get("cursor") or ""
    if not cur: break
d = get(A + "/markets?series_ticker=KXNCAAFGAME&status=open&limit=1000")
out.append("open GAME markets: %d" % len(d.get("markets", [])))
out.append(" ".join(sorted({m["event_ticker"] for m in d.get("markets", []) if "26OCT31" in m["event_ticker"]})[:80]))
open("probe.txt", "w").write("\n".join(out))
