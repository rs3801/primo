"""Player usage and recent game logs (free ESPN box scores) -> data/players.js
For every team playing in the next few days: its last 5 finished games, each player's numbers in them,
how the team spreads the ball around (targets, carries), and how much its defense has been giving up."""
import json, time, datetime, urllib.request, os
from zoneinfo import ZoneInfo

ESPN = "https://site.api.espn.com/apis/site/v2/sports/"
PT = ZoneInfo("America/Los_Angeles")
LEAGUES = {"NFL": "football/nfl", "College football": "football/college-football", "NBA": "basketball/nba", "WNBA": "basketball/wnba",
           "College basketball": "basketball/mens-college-basketball", "NHL": "hockey/nhl"}
N_GAMES = 5
MAX_NEW_BOX = 260
# per-game numbers kept for each player, by sport (order matters: the app reads them by position)
FB = ["tgt", "rec", "recYds", "recTD", "car", "rushYds", "rushTD", "cmp", "att", "passYds", "passTD", "int", "longRec", "longRush"]
BB = ["min", "pts", "reb", "ast", "3pm", "stl", "blk"]
HK = ["g", "a", "sog", "sv", "toi"]
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
        path = LEAGUES.get(g.get("league"))
        if not path or g.get("state") not in (None, "pre"): continue
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
            out_players[p] = {"tm": name, "lg": league, "pos": pos, "log": [[(int(v) if v is not None and v == int(v) else v) for v in r] if r else 0 for r in log]}
        out_teams[name] = {"lg": league, "sp": sport, "g": games}
    # keep caches small
    keep_ids = {i for v in sched.values() for i in v.get("ids", [])}
    boxes = {k: v for k, v in boxes.items() if k in keep_ids or now - v.get("k", now) < 20 * 86400}
    sched = {k: v for k, v in sched.items() if now - v.get("t", 0) < 7 * 86400}
    json.dump(boxes, open("data/box_cache.json", "w"), separators=(",", ":"))
    json.dump(sched, open("data/sched_cache.json", "w"), separators=(",", ":"))
    data = {"asof": datetime.datetime.now(PT).strftime("%b %d, %I:%M %p PT"), "keys": {"Football": FB, "Basketball": BB, "Hockey": HK}, "teams": out_teams, "players": out_players}
    with open("data/players.js", "w") as f:
        f.write("window.PRIMO_PLAYERS=" + json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/") + ";\n")
    print("players:", len(out_players), "teams:", len(out_teams), "new box scores:", new_box, "schedules:", new_sched, "calls:", CALLS["n"], "size:", os.path.getsize("data/players.js"))

if __name__ == "__main__":
    main()
