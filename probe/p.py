import urllib.request, json
out = []
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "primo-family-app/1.0"}), timeout=30) as r: return json.load(r)
    except Exception as e: out.append("ERR " + u + " " + str(e)); return None
E = "https://site.api.espn.com/apis/site/v2/sports/soccer/"
for path in ["uefa.champions/teams/432/schedule", "all/teams/432/schedule", "tur.1/teams/432/schedule", "eng.1/teams/359/schedule", "ger.1/teams/134/schedule"]:
    d = get(E + path)
    if d:
        evs = d.get("events") or []
        out.append(f"== {path}: {len(evs)} events; done={sum(1 for e in evs if (e['competitions'][0]['status']['type'].get('completed')))}; leagues={sorted(set((e.get('league') or {}).get('abbreviation','?') if isinstance(e.get('league'),dict) else '?' for e in evs))}")
        done = [e for e in evs if e['competitions'][0]['status']['type'].get('completed')]
        if done: out.append("  last: " + done[-1]["date"] + " " + done[-1]["name"] + " id " + done[-1]["id"]); last = done[-1]["id"]
# summary structure of last game
d = get(E + "eng.1/summary?event=" + last) or get(E + "all/summary?event=" + last)
if d:
    out.append("summary keys: " + ",".join(d.keys()))
    bx = d.get("boxscore") or {}
    out.append("box keys " + ",".join(bx.keys()))
    for t in bx.get("teams", [])[:1]: out.append("team stats: " + ", ".join(f"{s.get('name')}={s.get('displayValue')}" for s in t.get("statistics", [])[:30]))
    ro = d.get("rosters") or []
    out.append(f"rosters {len(ro)}")
    for t in ro[:1]:
        for p in (t.get("roster") or [])[:3]: out.append("player: " + json.dumps({k: p.get(k) for k in ("athlete", "position", "starter", "stats")})[:900])
    out.append("header comps " + json.dumps(((d.get("header") or {}).get("competitions") or [{}])[0].get("competitors", [{}])[0])[:500])
open("probe.txt", "w").write("\n".join(out))
