import json, urllib.request
out = []
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))
    except Exception as e: return {"err": str(e)}
E = "https://site.api.espn.com/apis/site/v2/sports/"
for path in ["football/nfl", "football/college-football", "basketball/nba", "hockey/nhl"]:
    sb = get(E + path + "/scoreboard")
    evs = [e for e in sb.get("events", []) if e["status"]["type"]["state"] == "pre"][:1] or sb.get("events", [])[:1]
    if not evs: out.append(path + " none"); continue
    d = get(E + path + "/summary?event=" + evs[0]["id"])
    lf = d.get("lastFiveGames") or []
    out.append(path + " lastFive " + json.dumps([[ (x.get("team") or {}).get("displayName"), [e.get("id") for e in x.get("events", [])]] for x in lf])[:300])
    if lf and lf[0].get("events"):
        pid = lf[0]["events"][0]["id"]; p = get(E + path + "/summary?event=" + pid)
        bx = p.get("boxscore") or {}
        for t in bx.get("players", [])[:1]:
            for c in t.get("statistics", []):
                a = (c.get("athletes") or [{}])[0]
                out.append("  %s keys=%s labels=%s ex=%s %s" % (c.get("name"), c.get("keys"), c.get("labels"), (a.get("athlete") or {}).get("displayName"), a.get("stats")))
        for t in bx.get("teams", [])[:1]:
            out.append("  team stats " + json.dumps([(s.get("name"), s.get("displayValue")) for s in t.get("statistics", [])])[:900])
        out.append("  size %d" % len(json.dumps(p)))
open("probe.txt", "w").write("\n".join(out))
