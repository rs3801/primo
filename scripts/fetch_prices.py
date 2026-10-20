"""Download Kalshi sports prices and write data/prices.js for Primo.
Same rules Primo's old browser refresh used. Runs on GitHub Actions (free)."""
import json, time, re, urllib.request, urllib.parse, datetime, os
from zoneinfo import ZoneInfo

API = "https://api.elections.kalshi.com/trade-api/v2"
PT = ZoneInfo("America/Los_Angeles")
DAYS = 8
MO = {m: i + 1 for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}
WIN = re.compile(r"(GAME|MATCH|FIGHT|BOUT)$")

def get(path, params=None, tries=5):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "primo-family-app/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            print("retry", i + 1, path, e); time.sleep(3 * (i + 1))
    raise SystemExit("Kalshi did not answer: " + url)

def cents(x):
    try: return round(float(x) * 100)
    except (TypeError, ValueError): return -1

def main():
    series = get("/series", {"category": "Sports"})["series"]
    S = {s["ticker"]: [s.get("title", ""), (s.get("tags") or ["Other"])[0] or "Other"] for s in series}
    print(len(S), "sports series")
    now = int(time.time())
    today = datetime.datetime.now(PT).date()
    last = today + datetime.timedelta(days=DAYS)
    R, cursor, page, zeros = {}, "", 0, 0
    while True:
        params = {"status": "open", "limit": 1000, "mve_filter": "exclude", "min_close_ts": now, "max_close_ts": now + 17 * 86400}
        if cursor: params["cursor"] = cursor
        j = get("/markets", params); ms = j.get("markets") or []; page += 1; kept = 0
        for m in ms:
            ev = m.get("event_ticker", ""); parts = ev.split("-"); st = parts[0]; code = parts[1] if len(parts) > 1 else ""
            if st not in S or re.search(r"PROT$|NEXTTEAM", st): continue
            d = re.match(r"^(\d{2})([A-Z]{3})(\d{2})", code)
            if not d or d.group(2) not in MO: continue
            try: gd = datetime.date(2000 + int(d.group(1)), MO[d.group(2)], int(d.group(3)))
            except ValueError: continue
            if gd < today or gd > last: continue
            b, a, l = cents(m.get("yes_bid_dollars")), cents(m.get("yes_ask_dollars")), cents(m.get("last_price_dollars"))
            pr = (a + b) / 2 if (b > 0 and 0 < a < 100) else (l if l > 0 else a)
            if not (0 < a < 100) or pr < 3 or pr > 97: continue
            try: vol = round(float(m.get("volume_fp") or 0))
            except ValueError: vol = 0
            win = bool(WIN.search(st))
            if not win and (vol < 5 or b < 1): continue
            label = m.get("yes_sub_title") if win else re.sub(r"\?$", "", m.get("title") or m.get("yes_sub_title") or "")
            R[m["ticker"]] = [ev, (label or "")[:90], round(pr), a, vol, (m.get("occurrence_datetime") or m.get("expected_expiration_time") or "")[:16]]
            kept += 1
        print(f"page {page}: {len(ms)} markets, kept {kept}, total {len(R)}")
        zeros = zeros + 1 if kept == 0 and len(R) else 0
        cursor = j.get("cursor") or ""
        if not cursor or not ms or zeros >= 3 or page >= 80: break
        time.sleep(0.4)
    # compact (same shape Primo already reads)
    by_ev = {}
    for v in R.values(): by_ev.setdefault(v[0], []).append(v)
    SER, SI, games = [], {}, {}
    for ev, rows0 in by_ev.items():
        st, code = ev.split("-")[0], ev.split("-")[1]
        win = bool(WIN.search(st))
        rows = rows0 if win else sorted(rows0, key=lambda r: -r[4])[:8]
        sport = S[st][1]; key = sport + "|" + code
        if st not in SI: SI[st] = len(SER); SER.append([st, S[st][0]])
        g = games.setdefault(key, {"e": [sport, code, int(code[5:7]), [], ""], "w": False})
        for r in rows:
            g["e"][3].append([SI[st], r[1], r[2], r[3], r[4]])
            if r[5] and ((win and not g["w"]) or not g["e"][4]):
                g["e"][4] = r[5]
                if win: g["w"] = True
    G = sorted((g["e"] for g in games.values()), key=lambda e: e[2])
    t = datetime.datetime.now(PT)
    asof = t.strftime("%a, %b ") + str(t.day) + ", " + t.strftime("%I:%M %p").lstrip("0") + " PT"
    data = {"asof": asof, "SER": SER, "G": G}
    if not G: raise SystemExit("No games found; keeping the old prices.")
    data["moves"] = price_moves(R)
    try: data["starts"] = real_starts({g[1] for g in G})
    except BaseException as e: print("start times skipped:", e)
    try: update_scorecard(R)
    except Exception as e: print("scorecard skipped:", e)
    os.makedirs("data", exist_ok=True)
    with open("data/prices.js", "w") as f:
        f.write("window.PRIMO_DATA=" + json.dumps(data, separators=(",", ":")).replace("</", "<\\/") + ";\n")
    print(asof, len(G), "games", sum(len(g[3]) for g in G), "markets")

def real_starts(codes):
    """Kalshi's live-score feed ("milestones") has each match's real start time and whether it's under way.
    The market's own time is only a rough end time (for tennis it can be hours after the start)."""
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out, cursor, page = {}, "", 0
    while page < 60:
        params = {"limit": 500, "category": "Sports", "minimum_start_date": since}
        if cursor: params["cursor"] = cursor
        j = get("/milestones", params, tries=3); page += 1
        for ms in j.get("milestones") or []:
            st = ms.get("start_date") or ""
            status = str((ms.get("details") or {}).get("status") or "").lower()
            begun = 1 if status and status not in ("not_started", "scheduled", "created", "pre", "upcoming", "delayed") else 0
            for ev in (ms.get("related_event_tickers") or []) + (ms.get("primary_event_tickers") or []):
                parts = ev.split("-")
                if len(parts) > 1 and parts[1] in codes and st:
                    out[parts[1]] = [st[:16], begun]
        cursor = j.get("cursor") or ""
        if not cursor or not j.get("milestones"): break
        time.sleep(0.3)
    print("real start times:", len(out), "of", len(codes), "games,", sum(v[1] for v in out.values()), "under way,", page, "pages")
    return out

import unicodedata
def mkey(ticker_row):
    ev, label = ticker_row[0], ticker_row[1]
    st, code = ev.split("-")[0], ev.split("-")[1]
    return st + "|" + code + "|" + label

def price_moves(R):
    """Price change since about a day ago, per bet: shows where the money is moving."""
    path = "data/baseline.json"; now = time.time()
    try: base = json.load(open(path))
    except Exception: base = {"t": 0, "p": {}}
    cur = {mkey(v): v[2] for v in R.values()}
    moves = {k: p - base["p"][k] for k, p in cur.items() if k in base["p"] and p - base["p"][k] != 0}
    if now - base.get("t", 0) > 24 * 3600:   # start a new 24-hour window
        json.dump({"t": now, "p": cur, "asof": datetime.datetime.now(PT).isoformat()}, open(path, "w"), separators=(",", ":"))
    return moves

def fold(x): return "".join(c for c in unicodedata.normalize("NFD", (x or "").lower()) if unicodedata.category(c) != "Mn")
def base_code(c): return re.sub(r"^(\d{2}[A-Z]{3}\d{2})\d{4}", r"\1", c)

def update_scorecard(R):
    """Remember every bet Primo's research liked, then grade it with Kalshi's official result."""
    try:
        txt = open("data/research.js").read(); RS = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
    except Exception: RS = {"games": {}}
    path = "data/scorecard.json"
    try: sc = json.load(open(path))
    except Exception: sc = {"picks": {}}
    picks = sc["picks"]
    liked = {}
    for gcode, g in (RS.get("games") or {}).items():
        for l in ((g.get("take") or {}).get("likes") or []):
            liked.setdefault(base_code(gcode), []).append(l)
    today = datetime.datetime.now(PT).strftime("%Y-%m-%d")
    for tk, v in R.items():
        code = v[0].split("-")[1]; lab = fold(v[1])
        for l in liked.get(base_code(code), []):
            ok = any((lab == fold(m[1:])) if m.startswith("=") else (fold(m) in lab) for m in (l.get("match") or []))
            if ok and tk not in picks:
                picks[tk] = {"bet": v[1], "game": v[0], "text": l.get("text", ""), "price": v[2], "day": today, "result": None}
    # grade picks whose games are over
    n = 0
    for tk, pk in picks.items():
        if pk.get("result") or n >= 60: continue
        if tk in R: continue          # still trading, not settled yet
        n += 1
        try: m = get("/markets/" + tk, tries=2).get("market", {})
        except SystemExit: continue
        if m.get("result") in ("yes", "no") and m.get("status") in ("settled", "finalized", "determined", "closed"):
            pk["result"] = "win" if m["result"] == "yes" else "loss"
        time.sleep(0.2)
    graded = [p for p in picks.values() if p.get("result")]
    w = sum(p["result"] == "win" for p in graded); l = len(graded) - w
    exp = sum(p["price"] for p in graded) / 100.0
    sc["summary"] = {"wins": w, "losses": l, "expected_wins": round(exp, 1), "asof": datetime.datetime.now(PT).strftime("%b %d, %I:%M %p PT")}
    sc["recent"] = sorted(graded, key=lambda p: p["day"], reverse=True)[:15]
    json.dump(sc, open(path, "w"), separators=(",", ":"))
    with open("data/scorecard.js", "w") as f:
        f.write("window.PRIMO_SCORE=" + json.dumps({"summary": sc["summary"], "recent": sc["recent"]}, separators=(",", ":")).replace("</", "<\\/") + ";\n")
    print("scorecard", sc["summary"])

if __name__ == "__main__":
    main()
