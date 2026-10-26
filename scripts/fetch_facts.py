"""Free hourly facts for Primo (no Claude, no laptop), from ESPN and MLB.com:
- schedules and start times for NFL, college football, NBA, WNBA, NHL, MLB and top soccer leagues
- official injury reports (NFL, NBA, WNBA, NHL)
- starting lineups when they are announced (soccer, basketball), MLB probable pitchers and series score
- sportsbook odds (DraftKings via ESPN) so Primo can tell when Kalshi is cheaper (value)
- recent form (last 5 games), home/road records and head-to-head meetings for team sports (ESPN game pages)
- ATP and WTA tennis: each player's recent results and head-to-head, from a results archive Primo builds up (data/tennis_results.json)
Writes data/facts.js."""
import json, time, datetime, urllib.request, os, re, unicodedata
from zoneinfo import ZoneInfo
PT = ZoneInfo("America/Los_Angeles")
ESPN = "https://site.api.espn.com/apis/site/v2/sports/"
LEAGUES = [  # (Kalshi sport name, league label, ESPN path, has injury report)
    ("Football", "NFL", "football/nfl", True),
    ("Football", "College football", "football/college-football", False),
    ("Basketball", "NBA", "basketball/nba", True),
    ("Basketball", "WNBA", "basketball/wnba", True),
    ("Basketball", "College basketball", "basketball/mens-college-basketball", False),
    ("Hockey", "NHL", "hockey/nhl", True),
    ("Baseball", "MLB", "baseball/mlb", True),
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

def fold(x):
    x = unicodedata.normalize("NFD", x or "")
    return re.sub(r"[^a-z]", "", "".join(c for c in x if unicodedata.category(c) != "Mn").lower())

def load_json(path, default):
    try:
        with open(path) as f: return json.load(f)
    except Exception: return default

def save_json(path, obj):
    with open(path, "w") as f: json.dump(obj, f, separators=(",", ":"))

def form_from_summary(d, my_names):
    """Last-5 results for each team and recent head-to-head meetings, from an ESPN game page."""
    out = {"form": {}, "h2h": None}
    for blk in d.get("lastFiveGames") or []:
        nm = (blk.get("team") or {}).get("displayName", "")
        rows = []
        for e in blk.get("events") or []:
            res = e.get("gameResult") or ""
            opp = (e.get("opponent") or {}).get("displayName") or (e.get("opponent") or {}).get("abbreviation") or ""
            if not res or not opp: continue
            rows.append("%s %s %s %s" % (res, e.get("score", ""), "at" if e.get("atVs") == "@" else "vs", opp))
        if nm and rows: out["form"][nm] = rows[:5]
    for ser in d.get("seasonseries") or []:
        evs = [e for e in ser.get("events") or [] if (e.get("statusType") or {}).get("completed")]
        games = []
        for e in evs[:5]:
            cs = e.get("competitors") or []
            if len(cs) != 2: continue
            h = next((c for c in cs if c.get("homeAway") == "home"), cs[0]); a = next((c for c in cs if c is not h), cs[1])
            nm = lambda c: (c.get("team") or {}).get("displayName", "")
            games.append("%s: %s %s, %s %s (at %s)" % ((e.get("date") or "")[:10], nm(a), a.get("score", ""), nm(h), h.get("score", ""), nm(h)))
        if games or ser.get("summary"):
            out["h2h"] = {"title": ser.get("title") or ser.get("shortSummary") or "", "summary": ser.get("summary") or "", "games": games}
            if games: break
    return out

def team_form(games):
    """ESPN game pages for games in the next 2 days; cached so each game is fetched about every 8 hours."""
    cache = load_json("data/form_cache.json", {})
    now = time.time(); new = 0
    for g in games:
        eid = g.get("eid")
        if not eid or g.get("state") != "pre": continue
        try: start = datetime.datetime.fromisoformat(g["start"].replace("Z", "+00:00")).timestamp()
        except ValueError: continue
        if start - now > 2 * 86400: continue
        c = cache.get(eid)
        if (not c or now - c.get("t", 0) > 8 * 3600) and new < 140:
            d = get(ESPN + g["path"] + "/summary?event=" + eid); new += 1
            if d: c = cache[eid] = {"t": now, "f": form_from_summary(d, [t["name"] for t in g["teams"]])}
        if c:
            if c["f"].get("form"): g["form"] = c["f"]["form"]
            if c["f"].get("h2h"): g["h2h"] = c["f"]["h2h"]
    cache = {k: v for k, v in cache.items() if now - v.get("t", 0) < 3 * 86400}
    save_json("data/form_cache.json", cache)
    print("team form:", sum(1 for g in games if g.get("form")), "games,", new, "new pages")

def tennis_archive():
    """Collect finished ATP and WTA singles matches. ESPN's scoreboard for a date returns that whole tournament week."""
    arc = load_json("data/tennis_results.json", {"m": {}, "back": 0})
    today = datetime.datetime.now(PT).date()
    dates = [today, today - datetime.timedelta(days=1), today - datetime.timedelta(days=4)]
    back = arc.get("back", 0)
    while back < 140 and len(dates) < 12:   # fill in about 20 weeks of history, a few weeks per run
        back += 7; dates.append(today - datetime.timedelta(days=back))
    arc["back"] = back
    for tour in ("atp", "wta"):
        for dt in dates:
            sb = get(ESPN + "tennis/%s/scoreboard?dates=%s" % (tour, dt.strftime("%Y%m%d"))) or {}
            for ev in sb.get("events", []):
                for grp in ev.get("groupings") or []:
                    gname = json.dumps(grp.get("grouping") or {}).lower()
                    if "double" in gname or "mixed" in gname: continue
                    for c in grp.get("competitions") or []:
                        st = ((c.get("status") or {}).get("type") or {})
                        if not st.get("completed"): continue
                        cs = c.get("competitors") or []
                        if len(cs) != 2 or any(not x.get("athlete") for x in cs): continue
                        w = next((x for x in cs if x.get("winner")), None)
                        if not w: continue
                        l = cs[1] if w is cs[0] else cs[0]
                        sets = []
                        for a, b in zip(w.get("linescores") or [], l.get("linescores") or []):
                            sets.append("%d-%d" % (a.get("value", 0), b.get("value", 0)))
                        ret = " (retired)" if "retir" in (st.get("name", "") + st.get("description", "")).lower() else ""
                        arc["m"][c.get("id")] = [(c.get("date") or "")[:10], w["athlete"].get("displayName", ""), l["athlete"].get("displayName", ""), " ".join(sets) + ret, ev.get("name", ""), tour.upper()]
    cut = (today - datetime.timedelta(days=400)).isoformat()
    arc["m"] = {k: v for k, v in arc["m"].items() if v[0] >= cut}
    save_json("data/tennis_results.json", arc)
    return list(arc["m"].values())

def kalshi_tennis_pairs():
    """Player pairs in Kalshi's tennis matches (from data/prices.js, written just before this script)."""
    try:
        s = open("data/prices.js").read(); D = json.loads(s[s.index("{"):s.rindex("}") + 1])
    except Exception: return []
    pairs = []
    for row in D.get("G", []):
        if row[0] != "Tennis": continue
        names = []
        for r in row[3]:
            lab = r[1]
            if ":" in lab or " " not in lab.strip() or re.search(r"\b(over|under|wins|set|games?|win)\b", lab, re.I): continue
            if lab not in names: names.append(lab)
        if len(names) == 2: pairs.append(names)
    return pairs

def tennis_stats():
    matches = tennis_archive()
    by = {}
    def key(n): return fold(n)
    for m in sorted(matches, key=lambda x: x[0], reverse=True):
        by.setdefault(key(m[1]), []).append(m); by.setdefault(key(m[2]), []).append(m)
    last = {}   # last name -> keys, for names Kalshi spells a little differently
    for k in by: pass
    names = {}
    for m in matches:
        for n in (m[1], m[2]): names[key(n)] = n
    def find(n):
        k = key(n)
        if k in by: return k
        parts = n.split(); ln = fold(parts[-1]) if parts else ""
        cand = [kk for kk, full in names.items() if fold(full.split()[-1]) == ln and full[:1].lower() == n[:1].lower()]
        return cand[0] if len(cand) == 1 else None
    players, h2h = {}, {}
    for a, b in kalshi_tennis_pairs():
        ka, kb = find(a), find(b)
        for n, k in ((a, ka), (b, kb)):
            if not k or n in players: continue
            rows = by[k][:10]
            w = sum(1 for m in rows if key(m[1]) == k)
            players[n] = {"rec": "%d-%d" % (w, len(rows) - w), "last": [[m[0], "W" if key(m[1]) == k else "L", names.get(key(m[2]) if key(m[1]) == k else key(m[1]), ""), m[3], m[4]] for m in rows[:5]]}
        if ka and kb:
            ms = [m for m in by[ka] if {key(m[1]), key(m[2])} == {ka, kb}]
            if ms: h2h[a + "|" + b] = {"a": sum(1 for m in ms if key(m[1]) == ka), "b": sum(1 for m in ms if key(m[1]) == kb), "games": [[m[0], names[key(m[1])], m[3], m[4]] for m in ms[:5]]}
    print("tennis:", len(matches), "matches in archive,", len(players), "Kalshi players with results,", len(h2h), "head-to-heads")
    return {"players": players, "h2h": h2h, "covers": "ATP and WTA main tour"}

def ordinal(n):
    return "%d%s" % (n, "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))

def standings(games):
    """Where each team sits in its league table (ESPN standings, refreshed every 6 hours)."""
    cache = load_json("data/standings.json", {})
    now = time.time(); out = {}
    paths = sorted({(g["league"], g["path"]) for g in games})
    urls = []
    for league, path in paths:   # college: one table per conference (top division 80 + FCS 81 for football, Division I = 50 for basketball)
        groups = [80, 81] if league == "College football" else [50] if league == "College basketball" else [None]
        urls += [(league, path + ("" if gr is None else "?group=%d" % gr)) for gr in groups]
    for league, path in urls:
        c = cache.get(path)
        if not c or now - c.get("t", 0) > 6 * 3600:
            d = get("https://site.api.espn.com/apis/v2/sports/" + path.replace("?", "/standings?", 1) if "?" in path else "https://site.api.espn.com/apis/v2/sports/" + path + "/standings")
            if not d: continue
            table = {}
            def walk(node):
                st = node.get("standings") or {}
                ents = st.get("entries") or []
                if ents:
                    def stat(e, *names):
                        for x in e.get("stats") or []:
                            if x.get("name") in names or x.get("type") in names:
                                try: return float(x.get("value"))
                                except (TypeError, ValueError): pass
                        return None
                    if all(stat(e, "rank") is not None for e in ents): key = lambda e: stat(e, "rank")
                    elif all(stat(e, "playoffSeed") is not None for e in ents): key = lambda e: stat(e, "playoffSeed")
                    else: key = lambda e: -(stat(e, "points") if stat(e, "points") is not None else (stat(e, "winPercent", "winpercent") or 0))
                    grp = node.get("name") or node.get("abbreviation") or league
                    for i, e in enumerate(sorted(ents, key=key)):
                        nm = (e.get("team") or {}).get("displayName", "")
                        if nm and nm not in table: table[nm] = [i + 1, len(ents), grp]
                for ch in node.get("children") or []: walk(ch)
            walk(d)
            c = cache[path] = {"t": now, "table": table}
        for nm, v in c["table"].items(): out.setdefault(league, {})[nm] = v
    save_json("data/standings.json", cache)
    for g in games:
        tb = out.get(g["league"], {})
        for t in g["teams"]:
            v = tb.get(t["name"])
            if v: t["place"] = "%s of %d in the %s" % (ordinal(v[0]), v[1], v[2])
    print("standings:", sum(1 for g in games for t in g["teams"] if t.get("place")), "teams placed,", sum(1 for g in games for t in g["teams"] if t.get("rank")), "ranked college teams")

def team(c):
    t = c.get("team", {})
    return {"id": t.get("id", ""), "name": t.get("displayName", ""), "short": t.get("shortDisplayName", ""), "loc": t.get("location", ""),
            "nick": t.get("name", ""), "abbr": t.get("abbreviation", ""), "home": c.get("homeAway") == "home",
            **({"rank": (c.get("curatedRank") or {}).get("current")} if 0 < ((c.get("curatedRank") or {}).get("current") or 99) < 99 else {})}   # college top-25 ranking

def lineups(path, eid):
    j = get(ESPN + path + "/summary?event=" + str(eid), tries=1) or {}
    out = {}
    for r in j.get("rosters") or []:
        starters = [p.get("athlete", {}).get("displayName", "") for p in (r.get("roster") or []) if p.get("starter")]
        if starters: out[(r.get("team") or {}).get("displayName", "")] = starters
    return out

def rosters(games):
    """Which team each player is on (so Primo can say "McCaffrey plays for the San Francisco 49ers").
    Team rosters are saved in data/rosters.json and refreshed once a day, only for teams playing soon."""
    path_ = "data/rosters.json"
    try: R = json.load(open(path_))
    except Exception: R = {}
    now = time.time(); fetched = 0; out = {}
    soon = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3)
    for g in games:
        if g["league"] in ("College football", "College basketball"): continue
        try:
            if datetime.datetime.fromisoformat(g["start"].replace("Z", "+00:00")) > soon: continue
        except ValueError: continue
        for t in g["teams"]:
            if not t.get("id"): continue
            k = g["path"] + "|" + str(t["id"])
            if (k not in R or now - R[k].get("t", 0) > 20 * 3600) and fetched < 120:
                j = get(ESPN + g["path"] + "/teams/" + str(t["id"]) + "/roster", tries=1); fetched += 1
                if j:
                    names = []
                    for a in j.get("athletes") or []:
                        if isinstance(a, dict) and a.get("items"): names += [x.get("displayName", "") for x in a["items"]]
                        elif isinstance(a, dict): names.append(a.get("displayName", ""))
                    R[k] = {"t": now, "team": t["name"], "players": [n for n in names if n]}
            for n in (R.get(k) or {}).get("players", []): out[n] = t["name"]
    json.dump(R, open(path_, "w"), separators=(",", ":"))
    print("rosters:", fetched, "teams fetched,", len(out), "players mapped")
    return out

def main():
    now = datetime.datetime.now(datetime.timezone.utc); today = datetime.datetime.now(PT).date()
    games, inj, seen = [], {}, set()
    for sport, league, path, has_inj in LEAGUES:
        days = [None] if league == "NFL" else [today + datetime.timedelta(days=i) for i in range(3)]
        urls = [ESPN + path + "/scoreboard" + ("" if d is None else "?dates=" + d.strftime("%Y%m%d")) for d in days]
        if league == "College basketball": urls = [u + "&groups=50&limit=400" for u in urls]   # all Division I games, not just the featured ones
        if league == "NFL":
            sb = get(urls[0]) or {}
            wk = (sb.get("week") or {}).get("number"); st = (sb.get("season") or {}).get("type") or 2
            evs = list(sb.get("events", []))
            if wk: evs += (get(ESPN + path + "/scoreboard?week=%d&seasontype=%s" % (wk + 1, st)) or {}).get("events", [])
        elif league == "College football":   # every FBS game this week, not just the featured ones
            evs = [e for grp in (80, 81) for e in ((get(ESPN + path + "/scoreboard?groups=%d&limit=300" % grp) or {}).get("events", []))]   # 80 = FBS (big schools), 81 = FCS (Ivy League, etc.)
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
                    if nm: g["notes"].append("%s starting %s: %s" % (c.get("team", {}).get("displayName", ""), "goalie" if sport == "Hockey" else "pitcher", nm))
            ser = (comp.get("series") or {}).get("summary")
            if ser: g["notes"].insert(0, ser)
            try: start = datetime.datetime.fromisoformat(g["start"].replace("Z", "+00:00"))
            except ValueError: start = None
            if start and sport in ("Soccer", "Basketball") and state == "pre" and (start - now).total_seconds() < 3 * 3600 and CALLS["n"] < 150:
                lu = lineups(path, ev.get("id"))
                if lu: g["lineups"] = lu
            g["path"] = path; g["eid"] = ev.get("id")
            recs = {}
            for c in cs:
                r = {x.get("type") or x.get("name"): x.get("summary") for x in c.get("records") or [] if x.get("summary")}
                if r: recs[(c.get("team") or {}).get("displayName", "")] = {"all": r.get("total"), "home": r.get("home") or r.get("homerecord"), "road": r.get("road") or r.get("awayrecord")}
            if recs: g["records"] = recs
            games.append(g)
        if has_inj:
            for t in (get(ESPN + path + "/injuries") or {}).get("injuries", []):
                rows = []
                for e in t.get("injuries", []):
                    stt = e.get("status", "")
                    if stt == "Day-To-Day": stt = "Questionable"
                    if "IL" in stt or stt in ("Injured Reserve", "Suspension"): stt = "Out"
                    if stt not in ("Out", "Doubtful", "Questionable"): continue
                    a = e.get("athlete", {}); d = e.get("details") or {}
                    rows.append({"player": a.get("displayName", ""), "pos": (a.get("position") or {}).get("abbreviation", ""), "status": stt,
                                 "injury": (d.get("type") or "").replace("Undisclosed", "undisclosed injury"), "date": (e.get("date") or "")[:10], "sport": sport,
                                 "note": (e.get("shortComment") or "")[:220]})
                if rows: inj[t.get("displayName", "")] = rows
    players = rosters(games)
    try: standings(games)
    except Exception as e: print("standings failed:", e)
    try: team_form(games)
    except Exception as e: print("team form failed:", e)
    try: tennis = tennis_stats()
    except Exception as e: print("tennis failed:", e); tennis = {}
    for g in games: g["espn"] = [g.pop("path", ""), g.pop("eid", "")]   # for live scores in the app
    t = datetime.datetime.now(PT)
    try: news = injury_news(inj)
    except Exception as e: print("injury news failed:", e); news = []
    out = {"news": news, "tennis": tennis, "players": players, "asof": t.strftime("%a, %b ") + str(t.day) + ", " + t.strftime("%I:%M %p").lstrip("0") + " PT", "games": games, "injuries": inj}
    if not games and not inj: raise SystemExit("No facts found; keeping the old file.")
    with open("data/facts.js", "w") as f:
        f.write("window.PRIMO_FACTS=" + json.dumps(out, separators=(",", ":")).replace("</", "<\\/") + ";\n")
    print(out["asof"], len(games), "games,", sum(len(v) for v in inj.values()), "injured players,",
          sum(1 for g in games if g.get("odds")), "with odds,", sum(1 for g in games if g.get("lineups")), "with lineups,", CALLS["n"], "calls")

def injury_news(inj):
    """Compare today's injury lists with what we saw before: who changed status, and when we first saw it.
    Status order: playing (not listed) < Questionable < Doubtful < Out."""
    path = "data/injury_seen.json"
    try: seen = json.load(open(path)); first = False
    except Exception: seen = {}; first = True
    now = datetime.datetime.now(datetime.timezone.utc); stamp = now.strftime("%Y-%m-%dT%H:%MZ")
    cur = {}
    for team, rows in inj.items():
        for r in rows: cur[team + "|" + r["player"]] = r
    for k, r in cur.items():
        old = seen.get(k)
        if not old: seen[k] = {"s": r["status"], "p": "Playing", "t": "old" if first else stamp, "pos": r.get("pos", "")}
        elif old["s"] != r["status"]: seen[k] = {"s": r["status"], "p": old["s"], "t": stamp, "pos": r.get("pos", "")}
    for k, old in list(seen.items()):
        if k not in cur and old["s"] != "Playing" and k.split("|", 1)[0] in inj:   # dropped off his team's list = cleared to play
            seen[k] = {"s": "Playing", "p": old["s"], "t": stamp, "pos": old.get("pos", "")}
        elif k not in cur and old["t"] != "old" and old["t"] < (now - datetime.timedelta(days=10)).strftime("%Y-%m-%dT%H:%MZ"):
            del seen[k]
    json.dump(seen, open(path, "w"), separators=(",", ":"))
    cut = (now - datetime.timedelta(hours=36)).strftime("%Y-%m-%dT%H:%MZ")
    news = []
    for k, v in seen.items():
        if v["t"] == "old" or v["t"] < cut: continue
        team, player = k.split("|", 1); r = cur.get(k) or {}
        news.append({"team": team, "player": player, "pos": r.get("pos") or v.get("pos", ""), "status": v["s"], "prev": v["p"], "when": v["t"], "note": r.get("note", "")})
    news.sort(key=lambda x: x["when"], reverse=True)
    print("injury news:", len(news))
    return news[:300]

if __name__ == "__main__":
    main()
