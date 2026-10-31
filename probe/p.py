import subprocess, os, json, sys, urllib.request
sys.path.insert(0, "scripts")
import alerts
out = []
d = json.load(urllib.request.urlopen(urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=80", headers={"User-Agent": "x"}), timeout=30))
n = 0
for ev in d["events"]:
    c = ev["competitions"][0]
    if c["status"]["type"]["state"] != "in": continue
    H = [x for x in c["competitors"] if x["homeAway"] == "home"][0]; A = [x for x in c["competitors"] if x["homeAway"] == "away"][0]
    r = alerts.game_story("football/college-football", ev["id"], "Football", A["team"]["id"], H["team"]["id"], False, A["team"]["shortDisplayName"], H["team"]["shortDisplayName"])
    out.append("%s %s-%s %s | WHY %s | CAREFUL %s | wp %s jump %s" % (ev["shortName"], A["score"], H["score"], c["status"]["type"]["shortDetail"], r[0], r[1], r[2], r[3]))
    n += 1
    if n >= 4: break
env = dict(os.environ, NTFY_TOPIC="")
rr = subprocess.run(["python3", "scripts/alerts.py"], capture_output=True, text=True, env=env)
out.append(rr.stdout[-2500:] + rr.stderr[-1500:])
open("probe.txt", "w").write("\n".join(out))
