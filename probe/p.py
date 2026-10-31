import json, urllib.request
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "primo-family-app/1.0"}), timeout=30))
    except Exception as e: return {"err": str(e)}
A = "https://api.elections.kalshi.com/trade-api/v2"
out = []
ser = get(A + "/series?category=Sports").get("series", [])
cf = [s["ticker"] for s in ser if "NCAAF" in s["ticker"] or "COLLEGE" in (s.get("title") or "").upper() and "FOOTBALL" in (s.get("title") or "").upper()]
out.append("series: " + " ".join(cf))
for s in cf:
    d = get(A + "/events?series_ticker=%s&status=open&limit=200" % s)
    hits = [e["event_ticker"] for e in d.get("events", []) if "MICH" in e["event_ticker"] and "26OCT31" in e["event_ticker"]]
    if hits: out.append(s + ": " + " ".join(hits))
open("probe.txt", "w").write("\n".join(out))
