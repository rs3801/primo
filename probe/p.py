import urllib.request, json
out = []
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "primo-family-app/1.0"}), timeout=30) as r: return json.load(r)
    except Exception as e: out.append("ERR " + u + " " + str(e)[:200]); return None
d = get("https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event=401908046")
pid = None
for t in d["boxscore"]["players"][:1]:
    for cat in t["statistics"]:
        if cat.get("type") == "pitching": pid = cat["athletes"][0]["athlete"]["id"]
out.append("pitcher id " + str(pid))
for u in ["https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/%s/gamelog" % pid,
          "https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/%s/gamelog?season=2026" % pid]:
    g = get(u)
    if not g: continue
    out.append("== " + u + " keys " + ",".join(g.keys()))
    out.append("labels " + json.dumps(g.get("labels")) + " names " + json.dumps(g.get("names")))
    st = g.get("seasonTypes") or []
    for s_ in st[:2]:
        out.append("season type " + str(s_.get("displayName")))
        for c in (s_.get("categories") or [])[:2]:
            out.append("  cat " + str(c.get("displayName")) + " " + str(c.get("type")))
            for e in (c.get("events") or [])[:3]: out.append("    " + json.dumps(e)[:300])
    evs = g.get("events") or {}
    out.append("events sample " + json.dumps(list(evs.items())[:1])[:400])
# NHL goalie
sb = get("https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates=20261031") or {}
e = [x for x in sb.get("events", []) if x["competitions"][0]["status"]["type"].get("completed")][0]
s = get("https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary?event=" + e["id"])
gid = None
for t in s["boxscore"]["players"][:1]:
    for cat in t["statistics"]:
        if cat.get("name") == "goalies": gid = cat["athletes"][0]["athlete"]["id"]; out.append("goalie keys " + json.dumps(cat.get("keys")))
g = get("https://site.web.api.espn.com/apis/common/v3/sports/hockey/nhl/athletes/%s/gamelog" % gid)
if g:
    out.append("NHL labels " + json.dumps(g.get("labels")) + " names " + json.dumps(g.get("names")))
    for s_ in (g.get("seasonTypes") or [])[:1]:
        for c in (s_.get("categories") or [])[:1]:
            for e in (c.get("events") or [])[:2]: out.append("    " + json.dumps(e)[:300])
open("probe.txt", "w").write("\n".join(out))
