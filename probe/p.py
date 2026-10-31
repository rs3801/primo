import subprocess, os, json, urllib.request
out = []
for grp in ("80",):
    d = json.load(urllib.request.urlopen(urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=" + grp, headers={"User-Agent": "x"}), timeout=30))
    for ev in d["events"]:
        c = ev["competitions"][0]
        if c["status"]["type"]["state"] != "in": continue
        out.append("%s %s %s odds=%s" % (ev["shortName"], [x["score"] for x in c["competitors"]], c["status"]["type"]["shortDetail"], bool(c.get("odds"))))
env = dict(os.environ, NTFY_TOPIC="")
rr = subprocess.run(["python3", "scripts/alerts.py"], capture_output=True, text=True, env=env)
out.append(rr.stdout[-3000:] + rr.stderr[-1500:])
open("probe.txt", "w").write("\n".join(out))
