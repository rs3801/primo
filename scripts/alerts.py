"""Phone/watch alerts for live upsets (free: ntfy.sh push notifications).
Runs inside the live robot every few minutes. Uses ESPN's live scores and win chance (free) and Kalshi's live prices
(live.json) to spot:
  - LATE UPSETS: the team that was the clear underdog before the game (40% or less) is ahead, tied or within one score
    late in the game (4th quarter, 3rd period, 7th inning on, last half hour of soccer).
  - LIVE VALUE: Kalshi sells a team for at least 10 cents less than ESPN's live win chance.
Each game alerts once per level (watch -> brewing -> happening), so the phone doesn't buzz nonstop."""
import json, os, re, time, calendar, unicodedata, urllib.request

TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
ESPN = "https://site.api.espn.com/apis/site/v2/sports/"
APP = "https://rs3801.github.io/primo/"
STATE = "/tmp/lv_alerts.json"

def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "primo-family-app/1.0"}), timeout=25) as r:
            return json.load(r)
    except Exception as e:
        print("alerts: fetch failed", url[-60:], e); return None

def fold(x): return "".join(c for c in unicodedata.normalize("NFD", (x or "").lower()) if unicodedata.category(c) != "Mn")
def load_js(p):
    t = open(p).read(); return json.loads(t[t.index("{"):t.rindex("}") + 1])

def team_hit(t, label):
    L = " " + re.sub(r"[^a-z0-9 ]", " ", fold(label)) + " "
    for n in (t.get("name"), t.get("short"), t.get("loc"), t.get("nick")):
        n = re.sub(r"[^a-z0-9 ]", " ", fold(n or "")).strip()
        if len(n) > 2 and (" " + n + " ") in L: return True
    return False

def late_stage(sport, path, period, clock):
    P = int(period or 0)
    m = re.match(r"(\d+):(\d+)", clock or ""); mins = int(m.group(1)) + int(m.group(2)) / 60 if m else None
    if sport == "Football": return ("overtime" if P > 4 else "4th quarter") if P >= 4 else None
    if sport == "Basketball":
        if "mens-college-basketball" in path: return "overtime" if P >= 3 else ("2nd half" if P == 2 and (mins is None or mins <= 12) else None)
        return "overtime" if P >= 5 else ("4th quarter" if P == 4 else None)
    if sport == "Hockey": return "overtime" if P >= 4 else ("3rd period" if P == 3 else None)
    if sport == "Baseball": return f"inning {P}" if P >= 7 else None
    if sport == "Soccer":
        try: mm = int(re.match(r"(\d+)", clock or "").group(1))
        except Exception: mm = None
        return "last half hour" if P >= 2 and (mm is None or mm >= 60) else None
    return None

def imp(a):
    try: a = float(a)
    except (TypeError, ValueError): return None
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)

def send(title, body, click):
    if not TOPIC: print("alerts: no NTFY_TOPIC set;", title); return
    req = urllib.request.Request("https://ntfy.sh/" + TOPIC, data=body.encode("utf-8"), method="POST",
                                 headers={"Title": title.encode("ascii", "ignore").decode(),
                                          "Tags": "rotating_light", "Priority": "high", "Click": click})
    try:
        urllib.request.urlopen(req, timeout=20).read(); print("alert sent:", title)
    except Exception as e: print("alerts: send failed", e)

def num(v):
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)", str(v if v is not None else ""))
    return float(m.group(1)) if m else None

def game_story(path, eid, sport, dog_id, fav_id, dog_home, dname, fname):
    """Read ESPN's game page: how each team is actually playing, the momentum, and the dog's key players.
    Returns (reasons, warnings, wp_now, wp_jump) where wp_* are the underdog's ESPN live win chance and its rise
    over roughly the last 10 plays."""
    d = get(ESPN + path + "/summary?event=" + str(eid)) or {}
    reasons, warns = [], []
    box = {}
    for t in (d.get("boxscore") or {}).get("teams") or []:
        box[str((t.get("team") or {}).get("id"))] = {x.get("name"): x.get("displayValue") for x in t.get("statistics") or []}
    B, F = box.get(str(dog_id), {}), box.get(str(fav_id), {})
    def cmp(key, label, better="more", pct=False, margin=0):
        b, f = num(B.get(key)), num(F.get(key))
        if b is None or f is None: return
        good = (b > f + margin) if better == "more" else (b < f - margin)
        bad = (f > b + margin) if better == "more" else (f < b - margin)
        txt = f"{label}: {dname} {B.get(key)}{'%' if pct else ''} vs {fname} {F.get(key)}{'%' if pct else ''}"
        if good: reasons.append(txt)
        elif bad: warns.append(txt)
    if sport == "Football":
        cmp("totalYards", "Total yards", margin=20); cmp("netPassingYards", "Passing yards", margin=25); cmp("rushingYards", "Rushing yards", margin=20)
        cmp("turnovers", "Turnovers", better="less"); cmp("firstDowns", "First downs", margin=2)
        # the underdog's quarterback and top runner today
        for t in (d.get("boxscore") or {}).get("players") or []:
            if str((t.get("team") or {}).get("id")) != str(dog_id): continue
            for cat in t.get("statistics") or []:
                a = (cat.get("athletes") or [None])[0]
                if not a: continue
                row = dict(zip(cat.get("keys") or [], a.get("stats") or [])); who = (a.get("athlete") or {}).get("displayName", "")
                if cat.get("name") == "passing" and row.get("passingYards"):
                    reasons.append(f"QB {who}: {row.get('completions/passingAttempts', '')}, {row.get('passingYards')} yds, {row.get('passingTouchdowns', 0)} TD, {row.get('interceptions', 0)} INT")
                if cat.get("name") == "rushing" and num(row.get("rushingYards") or 0) and num(row.get("rushingYards")) >= 50:
                    reasons.append(f"Runner {who}: {row.get('rushingAttempts')} carries, {row.get('rushingYards')} yds")
                if cat.get("name") == "receiving" and num(row.get("receivingYards") or 0) and num(row.get("receivingYards")) >= 60:
                    reasons.append(f"Top target {who}: {row.get('receptions')} catches, {row.get('receivingYards')} yds")
    elif sport == "Basketball":
        cmp("fieldGoalPct", "Shooting", pct=True, margin=2); cmp("threePointFieldGoalPct", "3-point shooting", pct=True, margin=3)
        cmp("totalRebounds", "Rebounds", margin=2); cmp("totalTurnovers", "Turnovers", better="less", margin=1)
    elif sport == "Hockey":
        cmp("shotsTotal", "Shots", margin=3); cmp("powerPlayGoals", "Power-play goals")
    elif sport == "Soccer":
        cmp("shotsOnTarget", "Shots on target", margin=0); cmp("possessionPct", "Possession", pct=True, margin=5)
    # momentum: the last scores of the game
    sp = d.get("scoringPlays") or []
    last = [x for x in sp[-3:]]
    dog_last = [x for x in last if str((x.get("team") or {}).get("id")) == str(dog_id)]
    if len(last) >= 2 and len(dog_last) >= 2: reasons.append(f"Momentum: {dname} scored {len(dog_last)} of the last {len(last)} times")
    elif len(last) >= 2 and not dog_last: warns.append(f"{fname} scored the last {len(last)} times")
    # ESPN's live win chance and how fast it's rising
    wps = d.get("winprobability") or []
    wp_now = wp_jump = None
    if wps:
        f = lambda w: w.get("homeWinPercentage") if dog_home else 1 - w.get("homeWinPercentage", 0) - (w.get("tiePercentage") or 0)
        wp_now = f(wps[-1]); old = f(wps[-12] if len(wps) > 12 else wps[0]); wp_jump = wp_now - old
        if wp_jump >= .08: reasons.append(f"ESPN's live chance for {dname} rose from {round(old*100)}% to {round(wp_now*100)}% over the last plays")
        elif wp_jump <= -.08: warns.append(f"ESPN's live chance for {dname} dropped from {round(old*100)}% to {round(wp_now*100)}% over the last plays")
    return reasons, warns, wp_now, wp_jump

def main():
    D = load_js("data/prices.js"); FX = load_js("data/facts.js")
    try: LV = json.load(open("live.json"))
    except Exception: LV = {"games": {}}
    try: sent = json.load(open(STATE))
    except Exception: sent = {}
    SER = {i: s[0] for i, s in enumerate(D["SER"])}
    now = time.time()
    # games that should be under way (ESPN kickoff in the last 5 hours)
    cand = []
    for g in FX.get("games") or []:
        try: st = calendar.timegm(time.strptime(g["start"][:16], "%Y-%m-%dT%H:%M"))
        except Exception: continue
        if 0 < now - st < 5 * 3600 and g.get("espn") and g["espn"][1] and len(g.get("teams") or []) == 2: cand.append(g)
    paths = sorted({g["espn"][0] for g in cand})
    sb = {}
    for p in paths:
        urls = [p + "/scoreboard?groups=80", p + "/scoreboard?groups=81"] if p == "football/college-football" else [p + "/scoreboard?groups=50&limit=300"] if p == "basketball/mens-college-basketball" else [p + "/scoreboard"]
        for u in urls:
            d = get(ESPN + u) or {}
            for ev in d.get("events") or []:
                c = (ev.get("competitions") or [{}])[0]; c["_path"] = p; c["_fcs"] = "groups=81" in u; sb[str(ev.get("id"))] = c
    n_alerts = 0
    for g in cand:
        c = sb.get(str(g["espn"][1]))
        if not c: continue
        st = c.get("status") or {}
        if ((st.get("type") or {}).get("state")) != "in": continue
        comps = c.get("competitors") or []
        if len(comps) != 2: continue
        H = next((x for x in comps if x.get("homeAway") == "home"), None); A = next((x for x in comps if x is not H), None)
        if not H or not A: continue
        # Kalshi live prices for this game
        code = None
        for kg in D["G"]:
            labs = [r[1] for r in kg[3] if re.search(r"(GAME|MATCH)$", SER[r[0]])]
            if kg[0] == g["sport"] and labs and all(any(team_hit(t, l) for l in labs) for t in g["teams"]) and kg[1] in LV.get("games", {}):
                code = kg[1]; break
        rows = [r for r in (LV.get("games", {}).get(code) or []) if re.search(r"(GAME|MATCH)$", r[0]) and not re.search(r"tie|draw", r[1], re.I)]
        def ask_for(t):
            r = next((r for r in rows if team_hit(t, r[1])), None); return (r[3] / 100, r[0]) if r else (None, None)
        # chance before the game: sportsbook money line (ESPN) or Primo's saved sportsbook odds
        od = (c.get("odds") or [{}])[0]
        def ml(x):
            x = x or {}; v = x.get("moneyLine")
            if v is None: v = ((x.get("current") or x.get("close") or x.get("open") or {}).get("moneyLine") or {}).get("american")
            return imp(v)
        h, a = ml(od.get("homeTeamOdds")), ml(od.get("awayTeamOdds"))
        preH = h / (h + a) if h and a else None
        if preH is None and (g.get("odds") or {}).get("home") is not None: preH = g["odds"]["home"] / (g["odds"]["home"] + g["odds"]["away"])
        Ht = next((t for t in g["teams"] if t.get("home")), None); At = next((t for t in g["teams"] if not t.get("home")), None)
        sc = lambda x: int(float(x.get("score") or 0))
        nm = lambda x: (x.get("team") or {}).get("shortDisplayName") or (x.get("team") or {}).get("displayName") or "?"
        clock, period = st.get("displayClock"), st.get("period")
        stage = late_stage(g["sport"], c["_path"], period, clock)
        situation = c.get("situation") or {}
        wp = situation.get("lastPlay", {}).get("probability", {}).get("homeWinPercentage") if isinstance(situation.get("lastPlay"), dict) else None
        msgs = []
        # 1) late upset (or a strong comeback already in the 2nd half)
        P = int(period or 0)
        half2 = (g["sport"] in ("Football", "Basketball") and (P >= 3 or ("mens-college-basketball" in c["_path"] and P >= 2))) or (g["sport"] == "Hockey" and P >= 2) or (g["sport"] == "Baseball" and P >= 5) or (g["sport"] == "Soccer" and P >= 2)
        if (stage or half2) and preH is not None and Ht and At:
            dogHome = preH < .5; dog, fav = (H, A) if dogHome else (A, H); dogT = Ht if dogHome else At
            pre = preH if dogHome else 1 - preH
            if pre <= .40:
                diff = sc(dog) - sc(fav); ball = str(situation.get("possession") or "") == str((dog.get("team") or {}).get("id"))
                near = {"Football": 8 if ball else 3, "Basketball": 6 if "college" in c["_path"] else 7, "Hockey": 1, "Baseball": 1, "Soccer": 0}.get(g["sport"])
                if near is not None and diff >= -near:
                    level = 3 if diff > 0 else 2 if diff == 0 else 1
                    key = f"{'late' if stage else 'come'}|{g['espn'][1]}"
                    story = None
                    if sent.get(key, 0) < level:
                        story = game_story(c["_path"], g["espn"][1], g["sport"], (dog.get("team") or {}).get("id"), (fav.get("team") or {}).get("id"), dogHome, nm(dog), nm(fav))
                        reasons, warns, wpd, jump = story
                        if not stage:   # earlier in the 2nd half: only a real comeback with momentum counts
                            if not (jump is not None and jump >= .12 and len(reasons) >= 3): level = 0
                        elif level == 1 and len(reasons) < 2: level = 0   # close but not playing better: don't buzz
                    if level and sent.get(key, 0) < level:
                        reasons, warns, wpd, jump = story
                        ask, ser = ask_for(dogT)
                        head = {3: "UPSET HAPPENING", 2: "UPSET BREWING", 1: "UPSET WATCH"}[level] if stage else "COMEBACK"
                        title = f"{head}: {nm(dog)} vs {nm(fav)}"
                        when = stage or (str((st.get("type") or {}).get("shortDetail") or ""))
                        body = f"{nm(dog)} were only {round(pre*100)}% to win before the game. Now {sc(dog)}-{sc(fav)} ({when}{', ' + clock if stage and clock else ''})."
                        if ball: body += f" {nm(dog)} have the ball."
                        if wpd is not None: body += f" ESPN live chance: {round(wpd*100)}%."
                        elif wp is not None: body += f" ESPN live: {nm(dog)} {round((wp if dogHome else 1 - wp)*100)}%."
                        if reasons: body += " WHY: " + "; ".join(reasons[:5]) + "."
                        if warns: body += " CAREFUL: " + "; ".join(warns[:2]) + "."
                        if ask: body += f" Kalshi: {round(ask*100)}c, $10 wins about ${10/ask - 10:.2f}."
                        else: body += " Check Kalshi's live price."
                        link = f"https://kalshi.com/markets/{ser.lower()}/x/{(ser + '-' + code).lower()}" if ask and code else APP
                        msgs.append((title, body, link)); sent[key] = level
        # 2) live value: Kalshi well below ESPN's live chance
        fresh = now - (LV.get("ts") or 0) < 8 * 60
        big = g.get("league") in ("NFL", "NBA", "WNBA", "NHL", "MLB", "College football") and not c.get("_fcs")
        if wp is not None and rows and fresh and big:
            for t, p in ((Ht, wp), (At, 1 - wp)):
                ask, ser = ask_for(t) if t else (None, None)
                if ask and .15 <= ask <= .75 and p - ask >= .10:
                    key = f"value|{g['espn'][1]}|{t['name']}"
                    if now - sent.get(key, 0) > 45 * 60:
                        title = f"LIVE VALUE: {t.get('short') or t['name']} to win"
                        body = f"Kalshi sells it at {round(ask*100)}c but ESPN's live model gives {t.get('short') or t['name']} {round(p*100)}% ({nm(H)} {sc(H)} - {nm(A)} {sc(A)}, {(st.get('type') or {}).get('shortDetail', '')}). $10 wins about ${10/ask - 10:.2f}."
                        link = f"https://kalshi.com/markets/{ser.lower()}/x/{(ser + '-' + code).lower()}" if code else APP
                        msgs.append((title, body, link)); sent[key] = now
        for m in msgs[:2]:
            send(*m); n_alerts += 1
    json.dump(sent, open(STATE, "w"))
    print("alerts:", len(cand), "games checked,", n_alerts, "sent")

if __name__ == "__main__":
    main()
