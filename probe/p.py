import json, urllib.request
out = []
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))
    except Exception as e: return {"err": str(e)}
E = "https://site.api.espn.com/apis/site/v2/sports/"
for path, tid in [("basketball/nba", "13"), ("hockey/nhl", "21"), ("football/college-football", "61"), ("basketball/wnba", "3")]:
    sc = get(E + path + "/teams/" + tid + "/schedule")
    evs = [e for e in sc.get("events", []) if ((e.get("competitions") or [{}])[0].get("status") or {}).get("type", {}).get("completed")]
    out.append("%s sched events %d completed %d %s" % (path, len(sc.get("events", [])), len(evs), sc.get("err", "")))
    if not evs: continue
    p = get(E + path + "/summary?event=" + evs[-1]["id"])
    bx = p.get("boxscore") or {}
    for t in bx.get("players", [])[:1]:
        for c in t.get("statistics", []):
            a = (c.get("athletes") or [{}])[0]
            out.append("  %s keys=%s ex=%s pos=%s %s" % (c.get("name") or c.get("text"), c.get("keys"), (a.get("athlete") or {}).get("displayName"), ((a.get("athlete") or {}).get("position") or {}).get("abbreviation"), a.get("stats")))
    for t in bx.get("teams", [])[:1]:
        out.append("  team " + json.dumps([(s.get("name"), s.get("displayValue")) for s in t.get("statistics", [])])[:600])
    hc = ((p.get("header") or {}).get("competitions") or [{}])[0]
    out.append("  header " + json.dumps([((c.get("team") or {}).get("displayName"), c.get("score"), c.get("homeAway")) for c in hc.get("competitors", [])]) + " date " + str(hc.get("date")))
open("probe.txt", "w").write("\n".join(out))
