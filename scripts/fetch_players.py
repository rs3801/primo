"""Player usage and recent game logs (free ESPN box scores) -> data/players.js
For every team playing in the next few days: its last 5 finished games, each player's numbers in them,
how the team spreads the ball around (targets, carries), and how much its defense has been giving up."""
import json, time, datetime, urllib.request, os, re
from zoneinfo import ZoneInfo

ESPN = "https://site.api.espn.com/apis/site/v2/sports/"
PT = ZoneInfo("America/Los_Angeles")
LEAGUES = {"NFL": "football/nfl", "College football": "football/college-football", "NBA": "basketball/nba", "WNBA": "basketball/wnba",
           "College basketball": "basketball/mens-college-basketball", "NHL": "hockey/nhl", "MLB": "baseball/mlb"}
SOCCER = "soccer/all"   # every soccer league: one team schedule covers league, cup and Europe games
N_GAMES = 10
MAX_NEW_BOX = 520
# per-game numbers kept for each player, by sport (order matters: the app reads them by position)
FB = ["tgt", "rec", "recYds", "recTD", "car", "rushYds", "rushTD", "cmp", "att", "passYds", "passTD", "int", "longRec", "longRush"]
BB = ["min", "pts", "reb", "ast", "3pm", "stl", "blk"]
HK = ["g", "a", "sog", "sv", "toi"]
SC = ["g", "a", "sot", "sh", "st", "sv"]
# baseball: batting (at-bats, hits, runs, RBIs, home runs, walks, strikeouts), then pitching (innings, hits, earned runs, walks, strikeouts, home runs, pitches, started 1/0)
BS = ["ab", "h", "r", "rbi", "hr", "bb", "k", "ip", "ph", "er", "pbb", "pk", "phr", "pc", "sp"]
def innings(v):
    try: w, f = str(v).split("."); return int(w) + int(f) / 3
    except Exception: return num(v)   # soccer: goals, assists, shots on target, shots, started (1/0), saves
CALLS = {"n": 0}

def get(url, tries=2):
    for i in range(tries):
        try:
            CALLS["n"] += 1
            req = urllib.request.Request(url, headers={"User-Agent": "primo-family-app/1.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception as e:
            print("retry", i + 1, url[-80:], e); time.sleep(2)
    return None

def load(path, default):
    try: return json.load(open(path))
    except Exception: return default

def num(v):
    try: return float(str(v).replace("+", ""))
    except (TypeError, ValueError): return None

def mins(v):
    try: m, s = str(v).split(":"); return round(int(m) + int(s) / 60, 1)
    except Exception: return num(v)

def box_of(d, sport):
    """Compact box score: {date, teams: {name: {score, stats, players: {name: [..]}}}}"""
    hc = ((d.get("header") or {}).get("competitions") or [{}])[0]
    out = {"d": (hc.get("date") or "")[:10], "t": {}}
    for c in hc.get("competitors") or []:
        out["t"][(c.get("team") or {}).get("displayName", "")] = {"s": num(c.get("score")), "st": {}, "p": {}}
    if sport == "Soccer":
        for t in (d.get("boxscore") or {}).get("teams") or []:
            nm = (t.get("team") or {}).get("displayName", "")
            if nm not in out["t"]: continue
            st = {s.get("name"): s.get("displayValue") for s in t.get("statistics") or []}
            out["t"][nm]["st"] = {k: num(st[k]) for k in ("possessionPct", "totalShots", "shotsOnTarget") if k in st and num(st[k]) is not None}
        for t in d.get("rosters") or []:
            nm = (t.get("team") or {}).get("displayName", "")
            if nm not in out["t"]: continue
            for a in t.get("roster") or []:
                who = (a.get("athlete") or {}).get("displayName"); st = {x.get("name"): x.get("value") for x in a.get("stats") or []}
                if not who or not st.get("appearances"): continue
                out["t"][nm]["p"][who] = [num(st.get("totalGoals")) or 0, num(st.get("goalAssists")) or 0, num(st.get("shotsOnTarget")) or 0, num(st.get("totalShots")) or 0, 1 if a.get("starter") else 0, num(st.get("saves"))]
                pos = (a.get("position") or {}).get("abbreviation", "")
                if pos: out.setdefault("pos", {})[who] = pos
        return out
    bx = d.get("boxscore") or {}
    for t in bx.get("teams") or []:
        nm = (t.get("team") or {}).get("displayName", "")
        if nm not in out["t"]: continue
        st = {s.get("name"): s.get("displayValue") for s in t.get("statistics") or []}
        keep = {}
        for k in ("totalYards", "netPassingYards", "rushingYards", "rushingAttempts", "shotsTotal", "totalRebounds", "assists"):
            if k in st and num(st[k]) is not None: keep[k] = num(st[k])
        out["t"][nm]["st"] = keep
    for t in bx.get("players") or []:
        nm = (t.get("team") or {}).get("displayName", "")
        if nm not in out["t"]: continue
        P = out["t"][nm]["p"]
        for cat in t.get("statistics") or []:
            keys = cat.get("keys") or []; cname = cat.get("name") or ""
            for a in cat.get("athletes") or []:
                who = (a.get("athlete") or {}).get("displayName"); vals = a.get("stats") or []
                if not who or not vals or a.get("didNotPlay"): continue
                row = dict(zip(keys, vals))
                pos = ((a.get("athlete") or {}).get("position") or {}).get("abbreviation", "")
                if sport == "Football":
                    r = P.setdefault(who, [None] * len(FB))
                    if cname == "receiving":
                        r[0] = num(row.get("receivingTargets")); r[1] = num(row.get("receptions")); r[2] = num(row.get("receivingYards")); r[3] = num(row.get("receivingTouchdowns")); r[12] = num(row.get("longReception"))
                    elif cname == "rushing":
                        r[4] = num(row.get("rushingAttempts")); r[5] = num(row.get("rushingYards")); r[6] = num(row.get("rushingTouchdowns")); r[13] = num(row.get("longRushing"))
                    elif cname == "passing":
                        ca = str(row.get("completions/passingAttempts", "")).split("/")
                        if len(ca) == 2: r[7] = num(ca[0]); r[8] = num(ca[1])
                        r[9] = num(row.get("passingYards")); r[10] = num(row.get("passingTouchdowns")); r[11] = num(row.get("interceptions"))
                    else:
                        if all(v is None for v in r): del P[who]
                elif sport == "Basketball":
                    tp = str(row.get("threePointFieldGoalsMade-threePointFieldGoalsAttempted", "")).split("-")
                    P[who] = [num(row.get("minutes")), num(row.get("points")), num(row.get("rebounds")), num(row.get("assists")), num(tp[0]) if tp and tp[0] else None, num(row.get("steals")), num(row.get("blocks"))]
                elif sport == "Baseball":
                    r = P.setdefault(who, [None] * len(BS)); typ = cat.get("type") or cname
                    if typ == "batting":
                        for i, k in enumerate(("atBats", "hits", "runs", "RBIs", "homeRuns", "walks", "strikeouts")): r[i] = num(row.get(k))
                    elif typ == "pitching":
                        r[7] = innings(row.get("fullInnings.partInnings")); r[8] = num(row.get("hits")); r[9] = num(row.get("earnedRuns")); r[10] = num(row.get("walks"))
                        r[11] = num(row.get("strikeouts")); r[12] = num(row.get("homeRuns")); r[13] = num(row.get("pitches")); r[14] = 1 if a.get("starter") else 0
                    if all(v is None for v in r): del P[who]
                elif sport == "Hockey":
                    if cname == "goalies": P[who] = [None, None, None, num(row.get("saves")), mins(row.get("timeOnIce"))]
                    else: P[who] = [num(row.get("goals")), num(row.get("assists")), num(row.get("shotsTotal")), None, mins(row.get("timeOnIce"))]
                if who in P and pos: out.setdefault("pos", {})[who] = pos
    return out

def main():
    txt = open("data/facts.js").read(); FXd = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
    sched = load("data/sched_cache.json", {}); boxes = load("data/box_cache.json", {})
    now = time.time(); utc = datetime.datetime.now(datetime.timezone.utc)
    teams = {}   # (league, team name) -> (path, id, sport)
    for g in FXd.get("games") or []:
        path = SOCCER if g.get("sport") == "Soccer" else LEAGUES.get(g.get("league"))
        if not path or g.get("state") not in (None, "pre", "in"): continue
        try:
            if datetime.datetime.fromisoformat(g["start"].replace("Z", "+00:00")) > utc + datetime.timedelta(days=7 if g["sport"] == "Football" else 3): continue
        except Exception: continue
        for t in g.get("teams") or []:
            if t.get("id"): teams[(g["league"], t["name"])] = (path, str(t["id"]), g["sport"])
    print(len(teams), "teams playing soon")
    new_box = 0; new_sched = 0
    out_teams, out_players = {}, {}
    for (league, name), (path, tid, sport) in sorted(teams.items()):
        k = path + "|" + tid
        sc = sched.get(k)
        if (not sc or now - sc.get("t", 0) > 10 * 3600) and new_sched < 220:
            d = get(ESPN + path + "/teams/" + tid + "/schedule"); new_sched += 1
            if d:
                ids = []
                for e in d.get("events") or []:
                    c = (e.get("competitions") or [{}])[0]
                    lg = e.get("league") if isinstance(e.get("league"), dict) else {}
                    if "friendl" in ((lg.get("slug") or "") + (lg.get("name") or "")).lower(): continue   # pre-season friendlies say little
                    if ((c.get("status") or {}).get("type") or {}).get("completed"): ids.append([e.get("date", "")[:10], e.get("id")])
                ids.sort()
                sc = sched[k] = {"t": now, "ids": [i for _, i in ids[-N_GAMES:]]}
        if not sc: continue
        logs = []
        for eid in sc["ids"]:
            b = boxes.get(eid)
            if not b and new_box < MAX_NEW_BOX:
                d = get(ESPN + path + "/summary?event=" + eid); new_box += 1
                if d:
                    b = box_of(d, sport); b["k"] = now
                    if b["t"]: boxes[eid] = b
            if b and name in b["t"]: logs.append(b)
        if not logs: continue
        games, plog = [], {}
        for b in logs:
            me = b["t"][name]; opp_name = next((n for n in b["t"] if n != name), ""); opp = b["t"].get(opp_name, {})
            games.append({"d": b["d"], "o": opp_name, "pf": me.get("s"), "pa": opp.get("s"), "f": me.get("st", {}), "a": opp.get("st", {})})
        # every player's line in each game (None = didn't play / no stats)
        names = {}
        for b in logs:
            for p in b["t"][name]["p"]: names[p] = (b.get("pos") or {}).get(p) or names.get(p) or ""
        for p, pos in names.items():
            log = [b["t"][name]["p"].get(p) for b in logs]
            rows = [r for r in log if r]
            s_ = lambda i: sum((r[i] or 0) for r in rows)
            if sport == "Football" and not (s_(8) > 0 or s_(0) + s_(4) + s_(1) >= 4 or s_(2) + s_(5) >= 25): continue
            if sport == "Basketball" and s_(0) < 8 * len(rows): continue
            if sport == "Hockey" and rows and rows[0][3] is None and s_(4) < 8 * len(rows): continue
            if sport == "Baseball" and not (s_(0) >= 6 or s_(7) >= 3): continue
            if sport == "Soccer" and (len(rows) < 2 or (s_(0) + s_(1) == 0 and s_(3) < 4 and not (s_(5) or 0))): continue
            out_players[p] = {"tm": name, "lg": league, "pos": pos, "log": [[(int(v) if v is not None and v == int(v) else v) for v in r] if r else 0 for r in log]}
        out_teams[name] = {"lg": league, "sp": sport, "g": games}
    # starting pitchers and goalies: their own last few games (they don't play every game, so the team's last 5 isn't enough)
    starters = {}; scache = load("data/starter_cache.json", {}); new_sc = 0
    for g in FXd.get("games") or []:
        if g.get("sport") not in ("Baseball", "Hockey") or g.get("state") not in (None, "pre"): continue
        for tm, pr in (g.get("prob") or {}).items():
            aid = pr.get("id"); key = g["sport"] + "|" + aid
            c = scache.get(key)
            if (not c or now - c.get("t", 0) > 12 * 3600) and new_sc < 80:
                path = "baseball/mlb" if g["sport"] == "Baseball" else "hockey/nhl"
                d = get("https://site.web.api.espn.com/apis/common/v3/sports/%s/athletes/%s/gamelog" % (path, aid)); new_sc += 1
                if d:
                    names = d.get("names") or []; ix = {n: i for i, n in enumerate(names)}; evs = d.get("events") or {}; rows = []
                    for stp in d.get("seasonTypes") or []:
                        for cat in stp.get("categories") or []:
                            for e in cat.get("events") or []:
                                st = e.get("stats") or []; dt = ((evs.get(e.get("eventId")) or {}).get("gameDate") or "")[:10]
                                v = lambda k: st[ix[k]] if k in ix and ix[k] < len(st) else None
                                if g["sport"] == "Baseball":
                                    ip = innings(v("innings")) or 0
                                    if ip >= 2.5 or (num(v("pitches")) or 0) >= 45: rows.append([dt, round(ip, 2), num(v("earnedRuns")), num(v("strikeouts")), num(v("walks")), num(v("hits"))])
                                elif str(v("gameStarted")) == "1": rows.append([dt, num(v("goalsAgainst")), num(v("shotsAgainst")), num(v("saves"))])
                    rows.sort(key=lambda r: r[0], reverse=True)
                    c = scache[key] = {"t": now, "last": rows[:5]}
            if c and c.get("last"): starters[pr["n"]] = {"tm": tm, "sp": g["sport"], "last": c["last"]}
    json.dump({k: v for k, v in scache.items() if now - v.get("t", 0) < 7 * 86400}, open("data/starter_cache.json", "w"), separators=(",", ":"))
    print("starters:", len(starters), "new game logs:", new_sc)
    # keep caches small
    keep_ids = {i for v in sched.values() for i in v.get("ids", [])}
    boxes = {k: v for k, v in boxes.items() if k in keep_ids or now - v.get("k", now) < 20 * 86400}
    sched = {k: v for k, v in sched.items() if now - v.get("t", 0) < 7 * 86400}
    json.dump(boxes, open("data/box_cache.json", "w"), separators=(",", ":"))
    json.dump(sched, open("data/sched_cache.json", "w"), separators=(",", ":"))
    # self-check: every player Kalshi has bets on, does Primo have his recent games?
    audit = {"checked": 0, "missing": []}
    try:
        import unicodedata
        fold = lambda x: "".join(c for c in unicodedata.normalize("NFD", (x or "").lower()) if unicodedata.category(c) != "Mn")
        t = open("data/prices.js").read(); PD = json.loads(t[t.index("{"):t.rindex("}") + 1]); have = {fold(n) for n in out_players}; seen = set()
        for kg in PD.get("G") or []:
            if kg[0] not in ("Football", "Basketball", "Hockey", "Baseball"): continue
            teams = [fold(r[1]) for r in kg[3] if ":" not in r[1]]
            for r in kg[3]:
                m = re.match(r"^(.+?):\s*(\d+\+|over|double|triple)", r[1], re.I)
                if not m: continue
                who = m.group(1).strip(); fw = fold(who)
                if fw in seen or "d/st" in fw or len(who.split()) < 2 or any(fw in x for x in teams): continue
                seen.add(fw); audit["checked"] += 1
                if fw not in have: audit["missing"].append(who)
    except Exception as e: print("audit failed", e)
    print("self-check:", audit["checked"], "players with Kalshi bets,", len(audit["missing"]), "without recent games")
    data = {"asof": datetime.datetime.now(PT).strftime("%b %d, %I:%M %p PT"), "audit": audit, "keys": {"Football": FB, "Basketball": BB, "Hockey": HK, "Soccer": SC, "Baseball": BS}, "starters": starters, "teams": out_teams, "players": out_players}
    with open("data/players.js", "w") as f:
        f.write("window.PRIMO_PLAYERS=" + json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/") + ";\n")
    print("players:", len(out_players), "teams:", len(out_teams), "new box scores:", new_box, "schedules:", new_sched, "calls:", CALLS["n"], "size:", os.path.getsize("data/players.js"))

if __name__ == "__main__":
    main()
