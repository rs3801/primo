import json, urllib.request
out = []
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "primo-family-app/1.0", "Accept": "application/json"}), timeout=40))
    except Exception as e: return {"err": str(e)}
A = "https://api.elections.kalshi.com/trade-api/v2"
cur = None; cols = []
for i in range(10):
    d = get(A + "/multivariate_event_collections?status=open&limit=200" + ("&cursor=" + cur if cur else ""))
    if "err" in d: out.append(d["err"]); break
    cols += d.get("multivariate_contracts") or d.get("multivariate_event_collections") or []
    cur = d.get("cursor")
    if not cur: break
out.append("collections %d keys %s" % (len(cols), list(cols[0].keys()) if cols else None))
ser = set()
for c in cols:
    for e in c.get("associated_events") or []:
        t = e.get("ticker") if isinstance(e, dict) else e
        if t: ser.add(t.split("-")[0])
    for s in c.get("series_tickers") or []: ser.add(s)
for c in cols[:3]: out.append(json.dumps(c)[:800])
out.append("series: " + " ".join(sorted(ser)))
open("probe.txt", "w").write("\n".join(out))
