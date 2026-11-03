import urllib.request, json
out = []
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "primo-family-app/1.0"}), timeout=30) as r: return json.load(r)
    except Exception as e: out.append("ERR " + u + " " + str(e)); return None
E = "https://site.api.espn.com/apis/site/v2/sports/soccer/"
last = None
for path in ["all/teams/432/schedule", "all/teams/359/schedule", "eng.1/teams/359/schedule?season=2026", "all/teams/359/schedule?season=2026"]:
    d = get(E + path)
    if d:
        evs = sorted([e for e in d.get("events") or [] if e['competitions'][0]['status']['type'].get('completed')], key=lambda e: e["date"])
        out.append(f"== {path}: {len(evs)} done; season {json.dumps(d.get('season'))[:80]}; latest: " + " | ".join(e["date"][:10] + " " + e["name"] + " #" + e["id"] + " " + str((e.get('league') or {}).get('slug') if isinstance(e.get('league'), dict) else '') for e in evs[-3:]))
        if not last and evs: last = (evs[-1]["id"])
d = get(E + "all/summary?event=" + last)
if d:
    for t in (d.get("rosters") or [])[:1]:
        out.append("team " + t.get("team", {}).get("displayName", ""))
        for p in (t.get("roster") or [])[:30]:
            st = {s.get("name"): s.get("value") for s in p.get("stats") or []}
            if st.get("totalGoals") or st.get("goalAssists") or p.get("starter"): out.append(p["athlete"]["displayName"] + " " + p.get("position", {}).get("abbreviation", "") + " starter=" + str(p.get("starter")) + " " + json.dumps(st)[:400])
open("probe.txt", "w").write("\n".join(out))
