import json, urllib.request
out = []
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40))
    except Exception as e: return {"err": str(e)}
d = get("https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard?dates=20261031")
c = d["events"][0]["competitions"][-1]
x = c["competitors"][0]; a = x["athlete"]
out.append("comp keys " + json.dumps(list(c.keys())) + " athlete " + json.dumps(a)[:600])
aid = a.get("id")
for u in ["https://sports.core.api.espn.com/v2/sports/mma/athletes/%s" % aid,
          "https://site.web.api.espn.com/apis/common/v3/sports/mma/athletes/%s" % aid,
          "https://site.web.api.espn.com/apis/common/v3/sports/mma/athletes/%s/fightHistory" % aid,
          "https://sports.core.api.espn.com/v2/sports/mma/athletes/%s/eventlog" % aid,
          "https://site.web.api.espn.com/apis/common/v3/sports/mma/athletes/%s/overview" % aid]:
    r = get(u); out.append(u + "\n   " + json.dumps(r)[:1500])
open("probe.txt", "w").write("\n".join(out))
