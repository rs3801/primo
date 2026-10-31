import subprocess, os, json, urllib.request
env = dict(os.environ, NTFY_TOPIC="")
r = subprocess.run(["python3", "scripts/alerts.py"], capture_output=True, text=True, env=env)
out = [r.stdout[-3000:], r.stderr[-2000:]]
# how many college games in progress, with lastPlay probability present?
d = json.load(urllib.request.urlopen(urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=80", headers={"User-Agent": "x"}), timeout=30))
for ev in d["events"][:40]:
    c = ev["competitions"][0]
    if c["status"]["type"]["state"] != "in": continue
    s = c.get("situation") or {}
    out.append("%s %s P%s %s | prob=%s | odds=%s" % (ev["shortName"], [x["score"] for x in c["competitors"]], c["status"].get("period"), c["status"].get("displayClock"), (s.get("lastPlay") or {}).get("probability"), json.dumps((c.get("odds") or [{}])[0])[:150]))
open("probe.txt", "w").write("\n".join(out))
