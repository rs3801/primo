import json, urllib.request, collections
out = []
def get(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}), timeout=40)
        return r.status, json.loads(r.read())
    except Exception as e:
        return "ERR", str(e)
def log(*a): out.append(" ".join(str(x) for x in a))
P = "https://guest.api.arcadia.pinnacle.com/0.1"
for u in ["/sports/29/matchups?withSpecials=false", "/sports/29/markets/straight?primaryOnly=false&withSpecials=false", "/sports/33/matchups", "/sports/33/markets/straight"]:
    s, d = get(P + u); log(u, s, len(d) if s == 200 else d[:200])
    if s == 200 and "markets" in u: log("  keys", collections.Counter(x["key"].split(";")[0] + ";" + x["key"].split(";")[2] if len(x["key"].split(";"))>2 else x["key"] for x in d).most_common(15))
s, m = get(P + "/leagues/889/markets/straight")
log("types", collections.Counter((x["type"], x["key"][:9], bool(x.get("isAlternate"))) for x in m).most_common(20))
sp = [x for x in m if x["type"] == "spread"][:3]
for x in sp: log(json.dumps(x)[:500])
tt = [x for x in m if x["type"] == "team_total"][:2]
for x in tt: log(json.dumps(x)[:500])
s, mu = get(P + "/leagues/889/matchups")
main = [x for x in mu if x["type"] == "matchup"][:2]
for x in main: log(json.dumps(x)[:900])
log("special categories", collections.Counter((x.get("special") or {}).get("category") for x in mu))
log("prop units", collections.Counter(x.get("units") for x in mu if (x.get("special") or {}).get("category") == "Player Props"))
log([ (x["special"]["description"], [p["name"] for p in x["participants"]]) for x in mu if "Touchdown" in (x.get("special") or {}).get("description","")][:5])
open("probe.txt", "w").write("\n".join(out))
