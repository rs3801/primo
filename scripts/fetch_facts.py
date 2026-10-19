"""Free hourly facts for Primo (no Claude, no laptop), from ESPN and MLB.com:
- schedules and start times for NFL, college football, NBA, WNBA, NHL, MLB and top soccer leagues
- official injury reports (NFL, NBA, WNBA, NHL)
- starting lineups when they are announced (soccer, basketball), MLB probable pitchers and series score
- sportsbook odds (DraftKings via ESPN) so Primo can tell when Kalshi is cheaper (value)
Writes data/facts.js."""
import json, time, datetime, urllib.request
from zoneinfo import ZoneInfo
PT = ZoneInfo("America/Los_Angeles")
ESPN = "https://site.api.espn.com/apis/site/v2/sports/"
LEAGUES = [  # (Kalshi sport name, league label, ESPN path, has injury report)
    ("Football", "NFL", "football/nfl", True),
    ("Football", "College football", "football/college-football", False),
    ("Basketball", "NBA", "basketball/nba", True),
    ("Basketball", "WNBA", "basketball/wnba", True),
    ("Hockey", "NHL", "hockey/nhl", True),
    ("Baseball", "MLB", "baseball/mlb", False),
] + [("Soccer", name, "soccer/" + code, False) for code, name in [
    ("eng.1", "Premier League"), ("esp.1", "La Liga"), ("ita.1", "Serie A"), ("ger.1", "Bundesliga"), ("fra.1", "Ligue 1"),
    ("uefa.champions", "Champions League"), ("uefa.europa", "Europa League"), ("usa.1", "MLS"), ("mex.1", "Liga MX"),
    ("bra.1", "Brasileirão"), ("eng.2", "Championship"), ("por.1", "Primeira Liga"), ("ned.1", "Eredivisie")]]
CALLS = {"n": 0}

def get(url, tries=3):
    for i in range(tries):
        try:
            CALLS["n"] += 1
            req = urllib.request.Request(url, headers={"User-Agent": "primo-family-app/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as r: return json.load(r)
        except Exception as e:
            print("retry", url, e); time.sleep(2 * (i + 1))
    return None

def american(o):
    try:
        o = float(str(o).replace("+", ""))
        return 100 / (o + 100) if o > 0 else -o / (-o + 100)
    except (TypeError, ValueError): return None

def odds_of(comp):
    o = (comp.get("odds") or [None])[0]
    if not o: return None
    ml = o.get("moneyline") or {}
    def side(k):
        s = ml.get(k) or {}
        return american(((s.get("close") or s.get("current") or s.get("open") or {}).get("odds")))
    h, a, d = side("home"), side("away"), side("draw")
    if d is None and (o.get("drawOdds") or {}).get("moneyLine") is not None: d = american((o["drawOdds"])["moneyLine"])
    raw = [x for x in (h, a, d) if x]
    out = {"book": (o.get("provider") or {}).get("name", ""), "total": o.get("overUnder"), "line": o.get("details", "")}
    if h and a:
        tot = sum(raw)   # remove the sportsbook's cut so the chances add to 100%
        out.update({"home": round(100 * h / tot, 1), "away": round(100 * a / tot, 1)})
        if d: out["draw"] = round(100 * d / tot, 1)
    return out

def team(c):
    t = c.get("team", {})
    return {"name": t.get("displayName", ""), "short": t.get("shortDisplayName", ""), "loc": t.get("location", ""),
            "nick": t.get("name", ""), "abbr": t.get("abbreviation", ""), "home": c.get("homeAway") == "home"}

def lineups(path, eid):
    j = get(ESPN + path + "/summary?event=" + str(eid), tries=1) or {}
    out = {}
    for r in j.get("rosters") or []:
        starters = [p.get("athlete", {}).get("displayName", "") for p in (r.get("roster") or []) if p.get("starter")]
        if starters: out[(r.get("team") or {}).get("displayName", "")] = starters
    return out

def main():
    now = datetime.datetime.now(datetime.timezone.utc); today = datetime.datetime.now(PT).date()
    games, inj, seen = [], {}, set()
    for sport, league, path, has_inj in LEAGUES:
        days = [None] if league == "NFL" else [today + datetime.timedelta(days=i) for i in range(3)]
        urls = [ESPN + path + "/scoreboard" + ("" if d is None else "?dates=" + d.strftime("%Y%m%d")) for d in days]
        if league == "NFL":
            sb = get(urls[0]) or {}
            wk = (sb.get("week") or {}).get("number"); st = (sb.get("season") or {}).get("type") or 2
            evs = list(sb.get("events", []))
            if wk: evs += (get(ESPN + path + "/scoreboard?week=%d&seasontype=%s" % (wk + 1, st)) or {}).get("events", [])
        else:
            evs = [e for u in urls for e in ((get(u) or {}).get("events", []))]
        for ev in evs:
            if ev.get("id") in seen: continue
            seen.add(ev.get("id"))
            comp = (ev.get("competitions") or [{}])[0]
            state = ((ev.get("status") or {}).get("type") or {}).get("state", "")
            if state == "post": continue
            cs = comp.get("competitors", [])
            g = {"sport": sport, "league": league, "start": ev.get("date", ""), "state": state, "teams": [team(c) for c in cs], "notes": []}
            od = odds_of(comp)
            if od: g["odds"] = od
            for c in cs:   # MLB probable pitchers from ESPN
                for p in c.get("probables") or []:
                    nm = (p.get("athlete") or {}).get("displayName")
                    if nm: g["notes"].append("%s starting pitcher: %s" % (c.get("team", {}).get("displayName", ""), nm))
            ser = (comp.get("series") or {}).get("summary")
            if ser: g["notes"].insert(0, ser)
            try: start = datetime.datetime.fromisoformat(g["start"].replace("Z", "+00:00"))
            except ValueError: start = None
            if start and sport in ("Soccer", "Basketball") and state == "pre" and (start - now).total_seconds() < 3 * 3600 and CALLS["n"] < 150:
                lu = lineups(path, ev.get("id"))
                if lu: g["lineups"] = lu
            games.append(g)
        if has_inj:
            for t in (get(ESPN + path + "/injuries") or {}).get("injuries", []):
                rows = []
                for e in t.get("injuries", []):
                    stt = e.get("status", "")
                    if stt == "Day-To-Day": stt = "Questionable"
                    if stt not in ("Out", "Doubtful", "Questionable"): continue
                    a = e.get("athlete", {}); d = e.get("details") or {}
                    rows.append({"player": a.get("displayName", ""), "pos": (a.get("position") or {}).get("abbreviation", ""), "status": stt,
                                 "injury": (d.get("type") or "").replace("Undisclosed", "undisclosed injury"), "date": (e.get("date") or "")[:10], "sport": sport})
                if rows: inj[t.get("displayName", "")] = rows
    t = datetime.datetime.now(PT)
    out = {"asof": t.strftime("%a, %b ") + str(t.day) + ", " + t.strftime("%I:%M %p").lstrip("0") + " PT", "games": games, "injuries": inj}
    if not games and not inj: raise SystemExit("No facts found; keeping the old file.")
    with open("data/facts.js", "w") as f:
        f.write("window.PRIMO_FACTS=" + json.dumps(out, separators=(",", ":")).replace("</", "<\\/") + ";\n")
    print(out["asof"], len(games), "games,", sum(len(v) for v in inj.values()), "injured players,",
          sum(1 for g in games if g.get("odds")), "with odds,", sum(1 for g in games if g.get("lineups")), "with lineups,", CALLS["n"], "calls")

if __name__ == "__main__":
    main()
