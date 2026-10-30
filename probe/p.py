import json, urllib.request
out = []
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u.replace("http://", "https://"), headers={"User-Agent": "Mozilla/5.0"}), timeout=40))
    except Exception as e: return {"err": str(e)}
a = get("https://sports.core.api.espn.com/v2/sports/mma/athletes/3028863")
out.append("ATH keys " + json.dumps({k: v for k, v in a.items() if not isinstance(v, (dict, list))})[:1200])
out.append("ATH dicts " + json.dumps({k: (v if len(json.dumps(v)) < 300 else "...") for k, v in a.items() if isinstance(v, (dict, list))})[:1500])
el = get("https://sports.core.api.espn.com/v2/sports/mma/athletes/3028863/eventlog")
for it in el["events"]["items"][1:3]:
    cp = get(it["competitor"]["$ref"]); cm = get(it["competition"]["$ref"])
    out.append("COMPETITOR " + json.dumps({k: v for k, v in cp.items() if k not in ("athlete",)})[:700])
    out.append("COMPETITION " + json.dumps({k: cm.get(k) for k in ("date", "type", "status", "competitors", "details", "notes")})[:1500])
    st = cm.get("status", {}).get("$ref")
    if st: out.append("STATUS " + json.dumps(get(st))[:800])
open("probe.txt", "w").write("\n".join(out))
