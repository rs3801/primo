import json, urllib.request
out = []
def get(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}), timeout=25)
        return r.status, json.loads(r.read())
    except Exception as e:
        return "ERR", str(e)
def log(*a): out.append(" ".join(str(x) for x in a))
P = "https://guest.api.arcadia.pinnacle.com/0.1"
s, sp = get(P + "/sports"); log("sports", s, [(x["id"], x["name"], x.get("matchupCount")) for x in sp] if s == 200 else sp)
for sid in (15, 4, 29, 33, 3, 19):
    s, lg = get(f"{P}/sports/{sid}/leagues?all=false")
    if s == 200: log("sport", sid, [(x["id"], x["name"], x.get("matchupCount")) for x in lg if x.get("matchupCount")][:40])
    else: log("sport", sid, s, str(lg)[:200])
s, m = get(P + "/leagues/889/matchups")
if s == 200:
    log("889 matchups", len(m)); 
    for x in m[:6]: log(json.dumps({k: x.get(k) for k in ("id","type","units","startTime","parentId","participants","special","isLive")})[:500])
s, m = get(P + "/leagues/889/markets/straight")
if s == 200:
    log("889 markets", len(m))
    for x in m[:8]: log(json.dumps(x)[:400])
s, d = get("https://api.actionnetwork.com/web/v1/scoreboard/nfl?period=game&bookIds=15,30,68,69,71,75,76,79,123")
if s == 200:
    g = d["games"][0]; log("AN game", g.get("teams") and [t["full_name"] for t in g["teams"]], g.get("start_time"))
    for o in (g.get("odds") or [])[:12]: log("  AN", o.get("book_id"), o.get("ml_home"), o.get("ml_away"), o.get("spread_home"), o.get("total"), o.get("over"), o.get("under"))
    log("AN keys", list(g.keys()))
open("probe.txt", "w").write("\n".join(out))
