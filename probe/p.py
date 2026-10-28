import json, urllib.request, collections
out = []
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "primo-family-app/1.0"}), timeout=40))
    except Exception as e: return {"err": str(e)}
A = "https://api.elections.kalshi.com/trade-api/v2"
evs = get(A + "/events?series_ticker=KXNBAGAME&status=open&limit=20").get("events", [])
for e in evs[:4]:
    code = e["event_ticker"].split("-")[1]
    for s in ["KXNBAPTS", "KXNBAREB", "KXNBAAST", "KXNBA3PT", "KXNBASTL", "KXNBABLK", "KXNBAPRA", "KXNBA2D", "KXNBA3D", "KXNBASTOCK"]:
        ms = get(A + "/markets?event_ticker=%s-%s&limit=500" % (s, code)).get("markets", [])
        nob = sum(1 for m in ms if float(m.get("yes_bid_dollars") or 0) <= 0)
        nov = sum(1 for m in ms if float(m.get("volume_fp") or 0) < 1)
        out.append("%s %s total=%d nobid=%d novol=%d status=%s" % (code, s, len(ms), nob, nov, collections.Counter(m.get("status") for m in ms)))
open("probe.txt", "w").write("\n".join(out))
