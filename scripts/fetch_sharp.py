"""Sharp sportsbook prices (Pinnacle, free public feed) -> data/sharp.js
Pinnacle is the sportsbook professional bettors trust most: its prices, with its small cut removed,
are the standard "fair chance" for a bet. Primo compares Kalshi's price to it to spot real value."""
import json, time, datetime, urllib.request
from zoneinfo import ZoneInfo

P = "https://guest.api.arcadia.pinnacle.com/0.1"
PT = ZoneInfo("America/Los_Angeles")
SPORTS = {15: "Football", 4: "Basketball", 19: "Hockey", 3: "Baseball", 29: "Soccer", 33: "Tennis", 22: "MMA", 6: "Boxing"}
PROP_LEAGUES = {"NFL", "NCAA", "NBA", "NHL", "MLB", "WNBA"}   # player props: only these (per-league calls include them)
DAYS = 4

def get(path, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(P + path, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            print("retry", i + 1, path, e); time.sleep(3 * (i + 1))
    return None

def imp(a):
    a = float(a)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)

def novig(prices):
    ps = [imp(x) for x in prices]; s = sum(ps)
    return [round(p / s, 4) for p in ps] if s > 0 else None

def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    end = now + datetime.timedelta(days=DAYS)
    games, props_by_parent = {}, {}
    for sid, sname in SPORTS.items():
        mu = get(f"/sports/{sid}/matchups?withSpecials=false") or []
        mk = get(f"/sports/{sid}/markets/straight?primaryOnly=false&withSpecials=false") or []
        time.sleep(0.4)
        prop_leagues = set()
        for x in mu:
            if x.get("type") != "matchup" or x.get("parentId") or x.get("isLive"): continue
            try: st = datetime.datetime.fromisoformat(x["startTime"].replace("Z", "+00:00"))
            except Exception: continue
            if st < now or st > end: continue
            pa = {p.get("alignment"): p.get("name") for p in x.get("participants", [])}
            if not pa.get("home") or not pa.get("away"): continue
            lg = (x.get("league") or {})
            if sid in (15, 4, 19, 3) and lg.get("name") in PROP_LEAGUES: prop_leagues.add(lg.get("id"))
            games[x["id"]] = {"s": sname, "l": lg.get("name", ""), "t": x["startTime"][:16], "h": pa["home"], "a": pa["away"],
                              "u": x.get("units", ""), "ml": None, "sp": [], "to": [], "th": [], "ta": [], "pr": []}
        for m in mk:
            g = games.get(m.get("matchupId"))
            if not g or m.get("period") != 0 or m.get("status", "open") != "open": continue
            pr = m.get("prices") or []
            try:
                if m["type"] == "moneyline":
                    d = {p.get("designation"): p["price"] for p in pr}
                    if "home" in d and "away" in d:
                        nv = novig([d["home"], d["away"]] + ([d["draw"]] if "draw" in d else []))
                        if nv: g["ml"] = nv
                elif m["type"] == "spread":
                    d = {p.get("designation"): p for p in pr}
                    nv = novig([d["home"]["price"], d["away"]["price"]])
                    if nv: g["sp"].append([d["home"]["points"], nv[0]])
                elif m["type"] == "total":
                    d = {p.get("designation"): p for p in pr}
                    nv = novig([d["over"]["price"], d["under"]["price"]])
                    if nv: g["to"].append([d["over"]["points"], nv[0]])
                elif m["type"] == "team_total":
                    d = {p.get("designation"): p for p in pr}
                    nv = novig([d["over"]["price"], d["under"]["price"]])
                    if nv: g["th" if m.get("side") == "home" else "ta"].append([d["over"]["points"], nv[0]])
            except (KeyError, TypeError, ValueError):
                continue
        # player props (only the big US leagues)
        for lid in prop_leagues:
            lmu = get(f"/leagues/{lid}/matchups") or []
            lmk = get(f"/leagues/{lid}/markets/straight") or []
            time.sleep(0.4)
            price = {}
            for m in lmk:
                if m.get("period") == 0 and m.get("status", "open") == "open":
                    for p in m.get("prices") or []:
                        if p.get("participantId"): price[p["participantId"]] = p
            for x in lmu:
                sp = x.get("special") or {}
                if x.get("type") != "special" or sp.get("category") != "Player Props" or x.get("parentId") not in games: continue
                ps = {p.get("name"): p.get("id") for p in x.get("participants", [])}
                o, u = price.get(ps.get("Over")), price.get(ps.get("Under"))
                if not o or not u or o.get("points") is None: continue
                nv = novig([o["price"], u["price"]])
                if nv: games[x["parentId"]]["pr"].append([sp.get("description", ""), o["points"], nv[0]])
    out = []
    for g in games.values():
        if not g["ml"] and not g["sp"] and not g["to"]: continue
        for k in ("sp", "to", "th", "ta"): g[k] = sorted(g[k])
        for k in ("sp", "to", "th", "ta", "pr", "u"):
            if not g[k]: del g[k]
        out.append(g)
    out.sort(key=lambda g: g["t"])
    data = {"asof": datetime.datetime.now(PT).strftime("%b %d, %I:%M %p PT"), "games": out}
    with open("data/sharp.js", "w") as f:
        f.write("window.PRIMO_SHARP=" + json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/") + ";\n")
    from collections import Counter
    print("sharp games", len(out), Counter(g["s"] for g in out), "props", sum(len(g.get("pr", [])) for g in out),
          "tennis units", Counter(g.get("u") for g in out if g["s"] == "Tennis"))

if __name__ == "__main__":
    main()
