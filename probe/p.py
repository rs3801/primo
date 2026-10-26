import json, urllib.request
out = []
def get(u, h=None):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=h or {"User-Agent": "Mozilla/5.0"}), timeout=25)
        return r.status, r.read()
    except Exception as e:
        return "ERR", str(e).encode()
def log(*a): out.append(" ".join(str(x) for x in a))
s, b = get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=20261026")
evs = json.loads(b).get("events", []) if s == 200 else []
log("nfl events", len(evs))
for path, lg in [("football/leagues/nfl", None), ("basketball/leagues/nba", None), ("football/leagues/college-football", None)]:
    s, b = get("https://site.api.espn.com/apis/site/v2/sports/" + path.replace("/leagues", "") + "/scoreboard")
    try: ev = json.loads(b)["events"]
    except Exception: log(path, "no sb", s); continue
    ev = [e for e in ev if e["status"]["type"]["state"] == "pre"][:1]
    if not ev: log(path, "no pre games"); continue
    eid = ev[0]["id"]; log(path, ev[0]["name"], eid)
    s, b = get(f"https://sports.core.api.espn.com/v2/sports/{path}/events/{eid}/competitions/{eid}/odds")
    try:
        d = json.loads(b)
        for it in d.get("items", []):
            p = it.get("provider", {})
            log("  core", p.get("name"), p.get("id"), it.get("details"), it.get("overUnder"), (it.get("homeTeamOdds") or {}).get("moneyLine"), (it.get("awayTeamOdds") or {}).get("moneyLine"))
    except Exception as e: log("  core err", s, b[:200])
    s, b = get(f"https://site.api.espn.com/apis/site/v2/sports/{path.replace('/leagues','')}/summary?event={eid}")
    try:
        d = json.loads(b)
        for it in d.get("pickcenter", []): log("  pickcenter", (it.get("provider") or {}).get("name"), it.get("details"), it.get("overUnder"))
    except Exception as e: log("  sum err", s)
for name, u in [("polymarket", "https://gamma-api.polymarket.com/events?tag_slug=nfl&closed=false&limit=3"),
                ("polymarket-sports", "https://gamma-api.polymarket.com/sports"),
                ("pinnacle", "https://guest.api.arcadia.pinnacle.com/0.1/leagues/889/matchups"),
                ("actionnetwork", "https://api.actionnetwork.com/web/v1/scoreboard/nfl?period=game&bookIds=15,30,68,69,71,75,76,79,123"),
                ("bovada", "https://www.bovada.lv/services/sports/event/v2/events/A/description/football/nfl")]:
    s, b = get(u); log(name, s, b[:400].decode("utf8", "replace").replace("\n", " "))
open("probe.txt", "w").write("\n".join(out))
