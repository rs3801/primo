import json, urllib.request
out = []
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40))
    except Exception as e: return {"err": str(e)}
E = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard?dates=20261031"
d = get(E)
for ev in d.get("events", [])[:2]:
    out.append("EVENT " + ev.get("name", "") + " " + ev.get("id", ""))
    for c in (ev.get("competitions") or [])[:20]:
        row = []
        for x in c.get("competitors") or []:
            a = x.get("athlete") or {}
            row.append("%s rec=%s" % (a.get("displayName"), [r.get("summary") for r in x.get("records") or []]))
        out.append("  " + " | ".join(row) + " type=" + str((c.get("type") or {}).get("abbreviation")))
    cid = (ev.get("competitions") or [{}])[0]
    aid = ((cid.get("competitors") or [{}])[0].get("athlete") or {}).get("id")
if d.get("events"):
    ev = d["events"][0]; c0 = ev["competitions"][0]; a = c0["competitors"][0]["athlete"]
    ath = get("https://site.web.api.espn.com/apis/common/v3/sports/mma/ufc/athletes/%s" % a.get("id"))
    out.append("ATHLETE " + json.dumps(ath)[:2500])
else:
    out.append(json.dumps(d)[:500])
open("probe.txt", "w").write("\n".join(out))
