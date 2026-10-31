import json, urllib.request
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "primo-family-app/1.0"}), timeout=30))
    except Exception as e: return {"err": str(e)}
A = "https://api.elections.kalshi.com/trade-api/v2"
out = []
for ev in ["KXNCAAFGAME-26OCT31KUTCU", "KXNCAAFGAME-26OCT31TCUKU", "KXNCAAFGAME-26OCT31KANTCU"]:
    d = get(A + "/markets?event_ticker=" + ev)
    out.append(ev + " " + json.dumps([{k: m.get(k) for k in ("ticker", "status", "yes_sub_title", "yes_ask_dollars")} for m in d.get("markets", [])])[:400] + str(d.get("err", "")))
d = get(A + "/events?series_ticker=KXNCAAFGAME&limit=200&with_nested_markets=false")
evs = [e["event_ticker"] for e in d.get("events", [])]
out.append("events first page %d: %s" % (len(evs), [e for e in evs if "KU" in e or "TCU" in e][:10]))
# what does the spread event say about related events?
sp = get(A + "/events/KXNCAAFSPREAD-26OCT31KUTCU")
out.append(json.dumps(sp)[:900])
ms = get(A + "/milestones?limit=50&related_event_ticker=KXNCAAFSPREAD-26OCT31KUTCU")
out.append(json.dumps(ms)[:1500])
open("probe.txt", "w").write("\n".join(out))
