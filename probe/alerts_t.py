"""Phone/watch alerts for live upsets (free: ntfy.sh push notifications).
Runs inside the live robot every few minutes. Uses ESPN's live scores and win chance (free) and Kalshi's live prices
(live.json) to spot:
  - LATE UPSETS: the team that was the clear underdog before the game (40% or less) is ahead, tied or within one score
    late in the game (4th quarter, 3rd period, 7th inning on, last half hour of soccer).
  - LIVE VALUE: Kalshi sells a team for at least 7 cents less than ESPN's live win chance.
  - CLOSE FINISH: coin-flip games within one score late.
Every alert says whether the team is REALLY outplaying the other or the score is LUCKY (turnovers, hot shooting, a goalie).
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

def send(title, body, click, kalshi=None):
    """Tapping the alert opens that game's card in Primo's Live tab; a second button opens it on Kalshi."""
    if not TOPIC: print("alerts: no NTFY_TOPIC set;", title, "|", body, "|", click, kalshi); return
    h = {"Title": title.encode("ascii", "ignore").decode(), "Tags": "rotating_light", "Priority": "high", "Click": click}
    acts = [f"view, Open in Primo, {click}"]
    if kalshi: acts.append(f"view, Open on Kalshi, {kalshi}")
    h["Actions"] = "; ".join(acts)
    req = urllib.request.Request("https://ntfy.sh/" + TOPIC, data=body.encode("utf-8"), method="POST", headers=h)
    try:
        urllib.request.urlopen(req, timeout=20).read(); print("alert sent:", title)
    except Exception as e: print("alerts: send failed", e)

def num(v):
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)", str(v if v is not None else ""))
    return float(m.group(1)) if m else None

def ratio(v):
    """'7-12' (made-attempts) -> 0.583"""
    m = re.match(r"\s*(\d+)\s*[-/]\s*(\d+)", str(v or ""))
    return int(m.group(1)) / int(m.group(2)) if m and int(m.group(2)) else None

def mins_of(v):
    m = re.match(r"\s*(\d+):(\d+)", str(v or "")); return int(m.group(1)) + int(m.group(2)) / 60 if m else None

def real_or_lucky(sport, B, F, dname, fname, diff):
    """Is the team (B) really outplaying the other (F), or is the score flattering them?
    Returns (verdict, label, details): label is REAL, EVEN or LUCKY. diff = B's score minus F's."""
    pts, luck, plus, minus = 0, [], [], []
    def side(cond_good, cond_bad, w, txt):
        nonlocal pts
        if cond_good: pts += w; plus.append(txt)
        elif cond_bad: pts -= w; minus.append(txt)
    if sport == "Football":
        yb, yf = num(B.get("yardsPerPlay")), num(F.get("yardsPerPlay"))
        if yb is not None and yf is not None: side(yb - yf >= .7, yf - yb >= .7, 2, f"yards per play {yb} vs {yf}")
        tb, tf = num(B.get("totalYards")), num(F.get("totalYards"))
        if tb and tf: side(tb >= tf * 1.15, tf >= tb * 1.15, 1, f"total yards {int(tb)} vs {int(tf)}")
        fb, ff = num(B.get("firstDowns")), num(F.get("firstDowns"))
        if fb is not None and ff is not None: side(fb - ff >= 3, ff - fb >= 3, 1, f"first downs {int(fb)} vs {int(ff)}")
        rb, rf = ratio(B.get("thirdDownEff")), ratio(F.get("thirdDownEff"))
        if rb is not None and rf is not None: side(rb - rf >= .15, rf - rb >= .15, 1, f"3rd downs {B.get('thirdDownEff')} vs {F.get('thirdDownEff')}")
        pb, pf = mins_of(B.get("possessionTime")), mins_of(F.get("possessionTime"))
        if pb and pf: side(pb - pf >= 5, pf - pb >= 5, 1, f"time with the ball {B.get('possessionTime')} vs {F.get('possessionTime')}")
        ob, of_ = num(B.get("turnovers")), num(F.get("turnovers"))
        if ob is not None and of_ is not None and of_ - ob >= 2: luck.append(f"{fname} have given the ball away {int(of_)} times ({dname} {int(ob)}), which handed {dname} extra chances")
        if ob is not None and of_ is not None and ob - of_ >= 2: minus.append(f"{dname} have {int(ob)} turnovers to {int(of_)}")
        if num(B.get("defensiveTouchdowns") or 0): luck.append(f"{dname} scored a defensive touchdown")
    elif sport == "Basketball":
        gb, gf = num(B.get("fieldGoalPct")), num(F.get("fieldGoalPct"))
        if gb is not None and gf is not None: side(gb - gf >= 4, gf - gb >= 4, 2, f"shooting {gb}% vs {gf}%")
        rb, rf = num(B.get("totalRebounds")), num(F.get("totalRebounds"))
        if rb is not None and rf is not None: side(rb - rf >= 5, rf - rb >= 5, 1, f"rebounds {int(rb)} vs {int(rf)}")
        ob, of_ = num(B.get("totalTurnovers") or B.get("turnovers")), num(F.get("totalTurnovers") or F.get("turnovers"))
        if ob is not None and of_ is not None: side(of_ - ob >= 3, ob - of_ >= 3, 1, f"turnovers {int(ob)} vs {int(of_)}")
        pb, pf = num(B.get("pointsInPaint")), num(F.get("pointsInPaint"))
        if pb is not None and pf is not None: side(pb - pf >= 8, pf - pb >= 8, 1, f"points in the paint {int(pb)} vs {int(pf)}")
        t3 = num(B.get("threePointFieldGoalPct"))
        if t3 is not None and t3 >= 45 and (gb or 0) - (gf or 0) < 4: luck.append(f"{dname} are hitting {t3}% from 3, a hot streak that often cools off")
    elif sport == "Hockey":
        sb, sf = num(B.get("shotsTotal")), num(F.get("shotsTotal"))
        if sb and sf:
            share = sb / (sb + sf)
            side(share >= .55, share <= .45, 2, f"shots {int(sb)} vs {int(sf)}")
            if share <= .42 and diff >= 0: luck.append(f"{dname} are being out-shot {int(sf)} to {int(sb)}: their goalie is keeping them in it")
    elif sport == "Soccer":
        sb, sf = num(B.get("shotsOnTarget")), num(F.get("shotsOnTarget"))
        if sb is not None and sf is not None: side(sb - sf >= 2, sf - sb >= 2, 2, f"shots on target {int(sb)} vs {int(sf)}")
        pb = num(B.get("possessionPct"))
        if pb is not None: side(pb >= 58, pb <= 42, 1, f"possession {pb}%")
    if pts >= 3 and not luck: label, v = "REAL", f"{dname} are truly outplaying {fname}: " + ", ".join(plus[:4]) + "."
    elif pts >= 2: label, v = "REAL", f"{dname} are playing better: " + ", ".join(plus[:3]) + "." + (" (Some help: " + "; ".join(luck[:1]) + ".)" if luck else "")
    elif pts <= -2: label, v = "LUCKY", f"{dname} are being outplayed: " + ", ".join(minus[:3]) + "." + (" The score is helped by luck: " + "; ".join(luck[:2]) + "." if luck else " The score may not last.")
    elif luck: label, v = "LUCKY", f"Even game on the field, but the score is helped by luck: " + "; ".join(luck[:2]) + "."
    else: label, v = "EVEN", f"Even game on the field" + (": " + ", ".join((plus + minus)[:3]) if plus or minus else "") + "."
    return v, label

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
                    ca = str(row.get("completions/passingAttempts", "")).split("/"); cm, at = (num(ca[0]), num(ca[1])) if len(ca) == 2 else (None, None)
                    yds, ints, tds = num(row.get("passingYards")) or 0, num(row.get("interceptions")) or 0, num(row.get("passingTouchdowns")) or 0
                    line = f"QB {who}: {row.get('completions/passingAttempts', '')}, {int(yds)} yds, {int(tds)} TD, {int(ints)} INT"
                    if ints >= 2: warns.append(line)
                    elif yds >= 150 or (at and at >= 8 and cm / at >= .65) or tds >= 2: reasons.append(line + " (playing well)")
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
    # game flow: lead changes, biggest leads, who won the latest quarter/period, and who is hot tonight
    flow = {"lc": None, "big_d": None, "big_f": None, "per_d": [], "per_f": [], "hot_d": [], "hot_f": []}
    for t in (d.get("boxscore") or {}).get("teams") or []:
        st_ = {x.get("name"): x.get("displayValue") for x in t.get("statistics") or []}
        tid = str((t.get("team") or {}).get("id"))
        lc = num(st_.get("leadChanges")); ll = num(st_.get("largestLead"))
        if lc is not None: flow["lc"] = int(lc)
        if tid == str(dog_id): flow["big_d"] = ll
        elif tid == str(fav_id): flow["big_f"] = ll
    for x in ((d.get("header") or {}).get("competitions") or [{}])[0].get("competitors") or []:
        per = [num(l.get("displayValue") if l.get("displayValue") is not None else l.get("value")) or 0 for l in x.get("linescores") or []]
        if str((x.get("team") or {}).get("id")) == str(dog_id): flow["per_d"] = per
        elif str((x.get("team") or {}).get("id")) == str(fav_id): flow["per_f"] = per
    if sport in ("Basketball", "Hockey", "Soccer"):
        for t in (d.get("boxscore") or {}).get("players") or []:
            tid = str((t.get("team") or {}).get("id")); cat = (t.get("statistics") or [{}])[0]
            keys = cat.get("names") or cat.get("labels") or []; ix = {k: i for i, k in enumerate(keys)}
            rows = []
            for a in cat.get("athletes") or []:
                v = a.get("stats") or []; g_ = lambda k: num(v[ix[k]]) if k in ix and ix[k] < len(v) else None
                who = (a.get("athlete") or {}).get("displayName", "")
                if sport == "Basketball" and g_("PTS") is not None:
                    tp = str(v[ix["3PT"]]).split("-")[0] if "3PT" in ix and ix["3PT"] < len(v) else "0"
                    rows.append((g_("PTS"), f"{who} {int(g_('PTS'))} pts" + (f", {tp} threes" if num(tp) and num(tp) >= 3 else "") + (f", {int(g_('REB'))} reb" if (g_("REB") or 0) >= 10 else "")))
                elif sport == "Hockey" and (g_("G") or 0) + (g_("A") or 0) >= 2: rows.append(((g_("G") or 0) + (g_("A") or 0), f"{who} {int(g_('G') or 0)}G {int(g_('A') or 0)}A"))
            rows.sort(key=lambda r: -r[0]); top = [r[1] for r in rows[:2] if sport != "Basketball" or r[0] >= 15]
            if tid == str(dog_id): flow["hot_d"] = top
            elif tid == str(fav_id): flow["hot_f"] = top
    try:
        sb_ = {}
        for x in ((d.get("header") or {}).get("competitions") or [{}])[0].get("competitors") or []: sb_[str((x.get("team") or {}).get("id"))] = num(x.get("score")) or 0
        verdict = real_or_lucky(sport, B, F, dname, fname, (sb_.get(str(dog_id), 0) - sb_.get(str(fav_id), 0)))
    except Exception as e:
        print("verdict failed", e); verdict = None
    return reasons, warns, wp_now, wp_jump, verdict, flow

def mins_left(sport, path, period, clock):
    """Rough minutes of game time left (None when it doesn't apply)."""
    m = re.match(r"(\d+):(\d+)", clock or ""); c = int(m.group(1)) + int(m.group(2)) / 60 if m else (float(clock) / 60 if re.match(r"^[\d.]+$", str(clock or "")) else 0)
    P = int(period or 0)
    if sport == "Basketball": return c + (max(0, 2 - P) * 20 if "college" in path else max(0, 4 - P) * (10 if "wnba" in path else 12))
    if sport == "Football": return c + max(0, 4 - P) * 15
    if sport == "Hockey": return c + max(0, 3 - P) * 20
    return None

def story_line(sport, flow, dname, fname, diff, left, verdict, wp, ask):
    """The headline the phone shows first: what kind of game this is, whether there's time, and Primo's call."""
    tag, bits = "", []
    lc, pd, pf = flow.get("lc"), flow.get("per_d") or [], flow.get("per_f") or []
    lastd = lastf = None
    if pd and pf and len(pd) == len(pf):
        i = len(pd) - 1
        if i >= 1 and pd[i] + pf[i] < (8 if sport == "Basketball" else 1): i -= 1   # the period just started: use the one before
        lastd, lastf = pd[i], pf[i]
        unit = "quarter" if sport in ("Basketball", "Football") and len(pd) <= 5 else "half" if sport == "Basketball" else "period"
        if lastd > lastf: bits.append(f"{dname} won the latest {unit} {int(lastd)}-{int(lastf)}")
        elif lastf > lastd: bits.append(f"{fname} won the latest {unit} {int(lastf)}-{int(lastd)}")
    if lc is not None and lc >= 6: tag = "BACK-AND-FORTH"; bits.append(f"{lc} lead changes")
    elif diff < 0 and lastd is not None and lastd > lastf: tag = "COMEBACK BUILDING"
    elif diff < 0 and lastd is not None and lastf > lastd: tag = "FADING"
    elif diff >= 0 and (flow.get("big_f") or 0) >= (10 if sport == "Basketball" else 10 if sport == "Football" else 2): tag = "TURNAROUND"; bits.append(f"{fname} once led by {int(flow['big_f'])}")
    elif diff >= 0: tag = "UPSET IN PROGRESS"
    else: tag = "CLOSE GAME" if abs(diff) <= (5 if sport == "Basketball" else 8 if sport == "Football" else 1) else "UNDERDOG BEHIND"
    # is there enough time?
    if diff < 0 and left is not None:
        need = -diff
        if sport == "Basketball": ok = "enough time" if need <= left * .8 else "running out of time" if need > left * 1.4 else "possible but needs a run"
        elif sport == "Football": sc_ = -(-need // 8); ok = "enough time" if left >= sc_ * 5 else "running out of time" if left < sc_ * 3 else "possible but tight"; bits.append(f"needs {sc_} score{'s' if sc_ > 1 else ''}")
        elif sport == "Hockey": ok = "enough time" if left >= need * 8 else "running out of time" if left < need * 4 else "possible but tight"
        else: ok = None
        if ok: bits.append(f"down {need} with about {int(round(left))} min left: {ok}")
    if flow.get("hot_d"): bits.append(f"{dname} hot tonight: " + ", ".join(flow["hot_d"]))
    if flow.get("hot_f"): bits.append(f"{fname}: " + ", ".join(flow["hot_f"]))
    # Primo's call
    lab = verdict[1] if verdict else "EVEN"
    if ask and wp is not None and wp - ask >= .05 and lab != "LUCKY" and tag not in ("FADING",): call = f"Primo: worth a small bet ({dname} {round(ask*100)}c, ESPN {round(wp*100)}%)"
    elif tag == "FADING" or lab == "LUCKY" or (diff < 0 and bits and "running out of time" in " ".join(bits)): call = f"Primo: skip it, {'they are fading' if tag == 'FADING' else 'the score flatters them' if lab == 'LUCKY' and diff >= 0 else 'not enough time' if 'running out' in ' '.join(bits) else 'being outplayed'}"
    elif ask and wp is not None: call = f"Primo: fair price ({round(ask*100)}c vs ESPN {round(wp*100)}%), fun-size bet only"
    else: call = "Primo: check the price"
    return f"[{tag}] {call}. " + ("; ".join(bits) + "." if bits else "")

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
        # no sportsbook line on the scoreboard (common for college games once they start): use ESPN's win chance at kickoff
        if preH is None and (stage or half2) and abs(sc(H) - sc(A)) <= 8:
            pk = f"pre|{g['espn'][1]}"
            if pk not in sent:
                dd = get(ESPN + c["_path"] + "/summary?event=" + str(g["espn"][1])) or {}
                w = (dd.get("winprobability") or [None])[0]
                sent[pk] = w.get("homeWinPercentage") if w else None
            preH = sent.get(pk)
        if (stage or half2) and preH is not None and Ht and At:
            dogHome = preH < .5; dog, fav = (H, A) if dogHome else (A, H); dogT = Ht if dogHome else At
            pre = preH if dogHome else 1 - preH
            if pre <= .46:   # the team that was expected to lose
                diff = sc(dog) - sc(fav); ball = str(situation.get("possession") or "") == str((dog.get("team") or {}).get("id"))
                near = {"Football": 8 if ball else 3, "Basketball": 5, "Hockey": 1, "Baseball": 1, "Soccer": 0}.get(g["sport"])
                if near is not None and diff >= -near:
                    level = 3 if diff > 0 else 2 if diff == 0 else 1
                    key = f"{'late' if stage else 'come'}|{g['espn'][1]}"
                    story = None
                    if sent.get(key, 0) < level:
                        story = game_story(c["_path"], g["espn"][1], g["sport"], (dog.get("team") or {}).get("id"), (fav.get("team") or {}).get("id"), dogHome, nm(dog), nm(fav))
                        reasons, warns, wpd, jump, verdict, flow = story
                        if not stage:   # earlier in the 2nd half: only a real comeback with momentum counts
                            if not (jump is not None and jump >= .12 and len(reasons) >= 3): level = 0

                    if level and sent.get(key, 0) < level:
                        reasons, warns, wpd, jump, verdict, flow = story
                        ask, ser = ask_for(dogT)
                        head = {3: "UPSET HAPPENING", 2: "UPSET BREWING", 1: "UPSET WATCH"}[level] if stage else "COMEBACK"
                        title = f"{head}: {nm(dog)} vs {nm(fav)}"
                        when = stage or (str((st.get("type") or {}).get("shortDetail") or ""))
                        left = mins_left(g["sport"], c["_path"], period, clock)
                        body = f"Now {sc(dog)}-{sc(fav)} ({when}{', ' + clock if stage and clock else ''}). " + story_line(g["sport"], flow, nm(dog), nm(fav), diff, left, verdict, wpd if wpd is not None else ((wp if dogHome else 1 - wp) if wp is not None else None), ask) + f"\n{nm(dog)} were only {round(pre*100)}% to win before the game."
                        if ball: body += f" {nm(dog)} have the ball."
                        if wpd is not None: body += f" ESPN live chance: {round(wpd*100)}%."
                        elif wp is not None: body += f" ESPN live: {nm(dog)} {round((wp if dogHome else 1 - wp)*100)}%."
                        if verdict: body += f" {'REAL' if verdict[1] == 'REAL' else ('LUCKY?' if diff >= 0 else 'OUTPLAYED') if verdict[1] == 'LUCKY' else 'EVEN'}: {verdict[0]}"
                        if reasons: body += "\nWHY: " + "; ".join(reasons[:4]) + "."
                        if warns: body += "\nCAREFUL: " + "; ".join(warns[:2]) + "."
                        ask0, _ = ask_for(dogT)
                        if ask0 and wpd is not None and wpd - ask0 >= .05: body += f" VALUE: Kalshi sells {nm(dog)} at {round(ask0*100)}c but ESPN gives them {round(wpd*100)}%."
                        if ask: body += f" Kalshi: {round(ask*100)}c, $10 wins about ${10/ask - 10:.2f}."
                        else: body += " Check Kalshi's live price."
                        kal = f"https://kalshi.com/markets/{ser.lower()}/x/{(ser + '-' + ((D.get('REMAP') or {}).get(code, {}).get(ser, code))).lower()}" if ask and code else None
                        msgs.append((title, body, f"{APP}#live-{g['espn'][1]}", kal)); sent[key] = level
        # 1b) close finish: a coin-flip game (neither team a real underdog) that's within one score late
        big_lg = g.get("league") in ("NFL", "NBA", "WNBA", "NHL", "MLB", "College football", "College basketball") and not c.get("_fcs")
        if stage and big_lg and Ht and At and f"late|{g['espn'][1]}" not in sent and f"close|{g['espn'][1]}" not in sent:
            lead, trail = (H, A) if sc(H) >= sc(A) else (A, H); gap = sc(lead) - sc(trail)
            poss = str(situation.get("possession") or ""); tball = poss == str((trail.get("team") or {}).get("id"))
            m_ = re.match(r"(\d+):(\d+)", clock or ""); mins = int(m_.group(1)) + int(m_.group(2)) / 60 if m_ else 99
            close = {"Football": gap <= 3 or (tball and gap <= 8), "Basketball": gap <= 4 and mins <= 6, "Hockey": gap <= 1, "Baseball": gap <= 1 and int(period or 0) >= 8}.get(g["sport"], False)
            if close:
                trailT = Ht if trail is H else At
                story = game_story(c["_path"], g["espn"][1], g["sport"], (trail.get("team") or {}).get("id"), (lead.get("team") or {}).get("id"), trail is H, nm(trail), nm(lead))
                reasons, warns, wpt, jump, verdict, flow = story
                left = mins_left(g["sport"], c["_path"], period, clock); ask_t0, _ = ask_for(trailT)
                title = f"CLOSE FINISH: {nm(trail)} {sc(trail)} - {nm(lead)} {sc(lead)}" if gap else f"TIED LATE: {nm(H)} {sc(H)} - {nm(A)} {sc(A)}"
                body = f"{stage}{', ' + clock if clock else ''}. " + (f"{nm(trail)} have the ball{': ' + situation.get('downDistanceText') if situation.get('downDistanceText') else ''}. " if tball else "")
                parts = []
                for side, t in ((H, Ht), (A, At)):
                    ask, ser = ask_for(t)
                    ch = (wp if side is H else (1 - wp)) if wp is not None else None
                    seg = f"{nm(side)}: " + (f"ESPN {round(ch*100)}%" if ch is not None else "") + (f", Kalshi {round(ask*100)}c" if ask else "")
                    if ask and ch is not None and ch - ask >= .05: seg += " (cheaper than it should be)"
                    parts.append(seg)
                body += " | ".join(parts) + "."
                body = story_line(g["sport"], flow, nm(trail), nm(lead), -gap, left, verdict, wpt, ask_t0) + "\n" + body
                if verdict: body += f" {'REAL' if verdict[1] == 'REAL' else ('LUCKY?' if not gap else 'OUTPLAYED') if verdict[1] == 'LUCKY' else 'EVEN'}: {verdict[0]}"
                if reasons: body += f" {nm(trail)} WHY: " + "; ".join(reasons[:3]) + "."
                if warns: body += "\nCAREFUL: " + "; ".join(warns[:2]) + "."
                ask_t, ser_t = ask_for(trailT)
                kal = f"https://kalshi.com/markets/{ser_t.lower()}/x/{(ser_t + '-' + ((D.get('REMAP') or {}).get(code, {}).get(ser_t, code))).lower()}" if ask_t and code else None
                msgs.append((title, body, f"{APP}#live-{g['espn'][1]}", kal)); sent[f"close|{g['espn'][1]}"] = 1
        # 2) live value: Kalshi well below ESPN's live chance
        fresh = now - (LV.get("ts") or 0) < 8 * 60
        big = g.get("league") in ("NFL", "NBA", "WNBA", "NHL", "MLB", "College football") and not c.get("_fcs")
        if wp is not None and rows and fresh and big:
            for t, p in ((Ht, wp), (At, 1 - wp)):
                ask, ser = ask_for(t) if t else (None, None)
                if ask and .10 <= ask <= .85 and p - ask >= .07:
                    key = f"value|{g['espn'][1]}|{t['name']}"
                    if now - sent.get(key, 0) > 45 * 60:
                        title = f"LIVE VALUE: {t.get('short') or t['name']} to win"
                        body = f"Kalshi sells it at {round(ask*100)}c but ESPN's live model gives {t.get('short') or t['name']} {round(p*100)}% ({nm(H)} {sc(H)} - {nm(A)} {sc(A)}, {(st.get('type') or {}).get('shortDetail', '')}). $10 wins about ${10/ask - 10:.2f}."
                        me_, op_ = (H, A) if t is Ht else (A, H)
                        stv = game_story(c["_path"], g["espn"][1], g["sport"], (me_.get("team") or {}).get("id"), (op_.get("team") or {}).get("id"), t is Ht, nm(me_), nm(op_))
                        body = story_line(g["sport"], stv[5], nm(me_), nm(op_), sc(me_) - sc(op_), mins_left(g["sport"], c["_path"], period, clock), stv[4], p, ask) + "\n" + body
                        if stv[4]: body += f" {'REAL' if stv[4][1] == 'REAL' else 'LUCKY?' if stv[4][1] == 'LUCKY' else 'EVEN'}: {stv[4][0]}"
                        if stv[4] and stv[4][1] == "LUCKY": title = title.replace("LIVE VALUE", "LIVE VALUE (careful)")
                        kal = f"https://kalshi.com/markets/{ser.lower()}/x/{(ser + '-' + ((D.get('REMAP') or {}).get(code, {}).get(ser, code))).lower()}" if code else None
                        msgs.append((title, body, f"{APP}#live-{g['espn'][1]}", kal)); sent[key] = now
        for m in msgs[:2]:
            send(*m); n_alerts += 1
    json.dump(sent, open(STATE, "w"))
    print("alerts:", len(cand), "games checked,", n_alerts, "sent")

if __name__ == "__main__":
    main()
