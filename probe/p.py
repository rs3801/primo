import sys, json; sys.path.insert(0, "probe"); import fp
out = []
d = fp.get("https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event=401908046")
b = fp.box_of(d, "Baseball")
for t, v in b["t"].items():
    out.append(t + " score " + str(v["s"]))
    for n, r in list(v["p"].items())[:4] + [x for x in v["p"].items() if x[1][7]][:3]: out.append("  " + n + " " + json.dumps(r))
g = fp.get("https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes/5080761/gamelog")
out.append("events date sample " + json.dumps({k: v.get("gameDate") for k, v in list((g.get("events") or {}).items())[:3]}))
sb = fp.get("https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard") or {}
for e in sb.get("events", [])[:3]:
    for c in e["competitions"][0]["competitors"]: out.append("NHL probables " + c["team"]["displayName"] + " " + json.dumps([(p.get("athlete") or {}).get("displayName") for p in c.get("probables") or []]))
open("probe.txt", "w").write("\n".join(out))
