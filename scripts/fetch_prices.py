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
    os.makedirs("data", exist_ok=True)
    with open("data/prices.js", "w") as f:
        f.write("window.PRIMO_DATA=" + json.dumps(data, separators=(",", ":")).replace("</", "<\\/") + ";\n")
    print(asof, len(G), "games", sum(len(g[3]) for g in G), "markets")

if __name__ == "__main__":
    main()
