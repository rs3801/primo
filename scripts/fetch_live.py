"""Live prices for games that are under way, every few minutes (free, GitHub Actions).
Writes live.json, which is pushed to the 'live' branch so it doesn't rebuild the website each time.
The app reads it from raw.githubusercontent.com and adds live scores from ESPN itself."""
import json, time, datetime, re, urllib.request, urllib.parse

API = "https://api.elections.kalshi.com/trade-api/v2"
WIN = re.compile(r"(GAME|MATCH|FIGHT|BOUT)$")

def get(path, params=None, tries=3):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "primo-family-app/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as r: return json.load(r)
        except Exception as e:
            print("retry", path, e); time.sleep(2 * (i + 1))
    return {}

def cents(x):
    try: return round(float(x) * 100)
    except (TypeError, ValueError): return -1

def main():
    s = open("data/prices.js").read(); D = json.loads(s[s.index("{"):s.rindex("}") + 1])
    now = datetime.datetime.now(datetime.timezone.utc)
    codes = {g[1]: g for g in D["G"]}
    # which games are under way right now (Kalshi's live-score feed)
    status, cursor, page = {}, "", 0
    since = (now - datetime.timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
    while page < 30:
        p = {"limit": 500, "category": "Sports", "minimum_start_date": since}
        if cursor: p["cursor"] = cursor
        j = get("/milestones", p); page += 1
        for ms in j.get("milestones") or []:
            st = str((ms.get("details") or {}).get("status") or "").lower()
            start = ms.get("start_date") or ""
            for ev in (ms.get("primary_event_tickers") or []) + (ms.get("related_event_tickers") or []):
                parts = ev.split("-")
                if len(parts) > 1 and parts[1] in codes: status[parts[1]] = [st, start[:16]]
        cursor = j.get("cursor") or ""
        if not cursor or not j.get("milestones"): break
    NOT = ("sch", "scheduled", "not_started", "created", "pre", "upcoming", "delayed", "postponed")
    live = []
    for code, (st, start) in status.items():
        try: t0 = datetime.datetime.fromisoformat(start + ":00+00:00")
        except ValueError: continue
        if t0 > now or (now - t0).total_seconds() > 6 * 3600: continue
        if st in NOT: continue
        live.append(code)
    out = {"ts": int(time.time()), "asof": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "status": {c: status[c][0] for c in live}, "games": {}}
    ser = {i: x[0] for i, x in enumerate(D["SER"])}
    n = 0
    for code in sorted(live, key=lambda c: -sum(r[4] for r in codes[c][3]))[:120]:
        series = sorted({ser[r[0]] for r in codes[code][3] if WIN.search(ser[r[0]]) or "TOTAL" in ser[r[0]] or "SPREAD" in ser[r[0]]})
        rows = []
        for st in series[:4]:
            j = get("/markets", {"event_ticker": st + "-" + code, "status": "open", "limit": 100}); n += 1
            for m in j.get("markets") or []:
                b, a = cents(m.get("yes_bid_dollars")), cents(m.get("yes_ask_dollars"))
                if not (0 < a < 100): continue
                mid = (a + b) / 2 if b > 0 else a
                win = bool(WIN.search(st))
                label = m.get("yes_sub_title") if win else re.sub(r"\?$", "", m.get("title") or m.get("yes_sub_title") or "")
                try: vol = round(float(m.get("volume_fp") or 0))
                except ValueError: vol = 0
                rows.append([st, (label or "")[:90], round(mid), a, vol])
        if rows: out["games"][code] = rows
    with open("live.json", "w") as f: json.dump(out, f, separators=(",", ":"))
    print(len(live), "live games,", len(out["games"]), "with prices,", n, "price calls")

if __name__ == "__main__":
    main()
