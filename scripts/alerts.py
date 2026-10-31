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
        # 1) late upset
        if stage and preH is not None and Ht and At:
            dogHome = preH < .5; dog, fav = (H, A) if dogHome else (A, H); dogT = Ht if dogHome else At
            pre = preH if dogHome else 1 - preH
            if pre <= .40:
                diff = sc(dog) - sc(fav); ball = str(situation.get("possession") or "") == str((dog.get("team") or {}).get("id"))
                near = {"Football": 8 if ball else 3, "Basketball": 6 if "college" in c["_path"] else 7, "Hockey": 1, "Baseball": 1, "Soccer": 0}.get(g["sport"])
                if near is not None and diff >= -near:
                    level = 3 if diff > 0 else 2 if diff == 0 else 1
                    key = f"late|{g['espn'][1]}"
                    if sent.get(key, 0) < level:
                        ask, ser = ask_for(dogT)
                        head = {3: "UPSET HAPPENING", 2: "UPSET BREWING", 1: "UPSET WATCH"}[level]
                        title = f"{head}: {nm(dog)} vs {nm(fav)}"
                        body = f"{nm(dog)} were only {round(pre*100)}% to win before the game. Now {sc(dog)}-{sc(fav)} in the {stage} ({clock})."
                        if ball: body += f" {nm(dog)} have the ball."
                        if wp is not None: body += f" ESPN live: {nm(dog)} {round((wp if dogHome else 1 - wp)*100)}%."
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
