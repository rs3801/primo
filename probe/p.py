import urllib.request, json
out = []
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "primo-family-app/1.0"}), timeout=30) as r: return json.load(r)
    except Exception as e: out.append("ERR " + u + " " + str(e)); return None
E = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/"
eid = None
for dt in ["20261031", "20261030", "20261028", "20261025", "20260928"]:
    sb = get(E + "scoreboard?dates=" + dt) or {}
    evs = [e for e in sb.get("events", []) if e["competitions"][0]["status"]["type"].get("completed")]
    if evs: eid = evs[0]["id"]; out.append(dt + " " + evs[0]["name"] + " " + eid); break
d = get(E + "summary?event=" + eid)
bx = d.get("boxscore") or {}
for t in bx.get("players", [])[:1]:
    out.append("team " + t["team"]["displayName"])
    for cat in t.get("statistics", []):
        out.append("cat " + str(cat.get("name")) + " type " + str(cat.get("type")) + " keys " + json.dumps(cat.get("keys")) + " labels " + json.dumps(cat.get("labels")))
        for a in cat.get("athletes", [])[:2]: out.append("   " + a["athlete"]["displayName"] + " " + json.dumps(a.get("stats")) + " pos " + str((a["athlete"].get("position") or {}).get("abbreviation")) + " starter " + str(a.get("starter")))
for t in bx.get("teams", [])[:1]:
    out.append("team stats " + json.dumps([(s.get("name"), s.get("displayValue")) for s in t.get("statistics", [])])[:600])
sched = get(E + "teams/19/schedule?season=2026")
if sched: out.append("sched events " + str(len(sched.get("events", []))) + " " + json.dumps(sched.get("requestedSeason") or sched.get("season"))[:100])
open("probe.txt", "w").write("\n".join(out))
