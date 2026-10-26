"""Primo's report card.
1) Opens the app in a headless browser and records Primo's opinion on every bet whose game starts soon.
2) Grades recorded bets with Kalshi's official results once the games are over.
3) Writes data/report.js with how each kind of opinion actually did."""
import json, time, datetime, threading, http.server, functools, urllib.request, urllib.parse, os
from zoneinfo import ZoneInfo

API = "https://api.elections.kalshi.com/trade-api/v2"
PT = ZoneInfo("America/Los_Angeles")
LOG = "data/report_log.json"
KEEP_DAYS = 60

def get(path, params=None, tries=3):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "primo-family-app/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception as e:
            print("retry", i + 1, path, e); time.sleep(2 * (i + 1))
    return None

def snapshot():
    from playwright.sync_api import sync_playwright
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=os.getcwd())
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8765), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page()
            pg.on("pageerror", lambda e: print("page error:", e))
            pg.goto("http://127.0.0.1:8765/index.html", wait_until="load", timeout=90000)
            pg.wait_for_function("typeof window.__primoSnapshot === 'function'", timeout=60000)
            pg.wait_for_timeout(4000)
            rows = pg.evaluate("window.__primoSnapshot(3)")
            b.close()
    finally:
        srv.shutdown()
    return rows or []

def main():
    try: log = json.load(open(LOG))
    except Exception: log = {"bets": {}}
    bets = log["bets"]
    now = datetime.datetime.now(datetime.timezone.utc)

    # 1) record (keep overwriting until the game starts, so the last opinion before kickoff is what counts)
    try: rows = snapshot()
    except Exception as e: print("snapshot failed:", e); rows = []
    for r in rows:
        k = r["series"] + "-" + r["code"] + "|" + r["label"] + ("|no" if r["inverse"] else "")
        if k in bets and bets[k].get("result"): continue
        r["seen"] = now.strftime("%Y-%m-%dT%H:%M"); r["result"] = None
        bets[k] = r
    print("recorded", len(rows), "bets; log has", len(bets))

    # 2) grade finished games (Kalshi settles after the game; check games that started 3+ hours ago)
    events = {}
    for k, r in bets.items():
        if r.get("result"): continue
        try: st = datetime.datetime.fromisoformat(r["start"].replace("Z", "+00:00"))
        except Exception: continue
        if now - st < datetime.timedelta(hours=3): continue
        events.setdefault(r["series"] + "-" + r["code"], []).append(k)
    checked = 0
    for ev, keys in events.items():
        if checked >= 150: break
        checked += 1
        d = get("/markets", {"event_ticker": ev, "limit": 1000})
        if not d: continue
        res = {}
        for m in d.get("markets") or []:
            if m.get("result") not in ("yes", "no"): continue
            for lab in (m.get("yes_sub_title"), (m.get("title") or "").rstrip("?")):
                if lab: res[lab[:90]] = m["result"]
        for k in keys:
            r = bets[k]; out = res.get(r["label"])
            if out:
                hit = (out == "yes") != bool(r.get("inverse"))
                r["result"] = "win" if hit else "loss"
            elif now - datetime.datetime.fromisoformat(r["start"].replace("Z", "+00:00")) > datetime.timedelta(days=4):
                r["result"] = "void"   # never settled / couldn't be matched
        time.sleep(0.15)

    # prune old
    cut = (now - datetime.timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    for k in [k for k, r in bets.items() if r["start"][:10] < cut]: del bets[k]

    # 3) summarize
    graded = [r for r in bets.values() if r.get("result") in ("win", "loss")]
    def summ(rs):
        n = len(rs)
        if not n: return None
        w = sum(r["result"] == "win" for r in rs)
        exp = sum(r["ask"] for r in rs) / 100.0
        profit = sum((100.0 / r["ask"] - 1) if r["result"] == "win" else -1 for r in rs) * 10   # $10 on each
        return {"n": n, "wins": w, "hit": round(100 * w / n), "expected": round(100 * exp / n), "per10": round(profit / n, 2)}
    groups = {}
    for name, f in [("keep", lambda r: r["verdict"] == "keep"), ("okay", lambda r: r["verdict"] == "okay"),
                    ("risky", lambda r: r["verdict"] == "risky"), ("drop", lambda r: r["verdict"] == "drop"),
                    ("good", lambda r: r["flag"] == "good"), ("pricey", lambda r: r["flag"] == "pricey"),
                    ("keepgood", lambda r: r["verdict"] == "keep" and r["flag"] == "good"), ("all", lambda r: True)]:
        s = summ([r for r in graded if f(r)])
        if s: groups[name] = s
    by_sport = {}
    for sp in sorted({r["sport"] for r in graded}):
        s = summ([r for r in graded if r["sport"] == sp and r["verdict"] == "keep"])
        if s: by_sport[sp] = s
    by_type = {}
    for t in sorted({r["type"] for r in graded}):
        s = summ([r for r in graded if r["type"] == t and r["verdict"] == "keep"])
        if s: by_type[t] = s
    days = sorted({r["start"][:10] for r in graded})
    out = {"asof": datetime.datetime.now(PT).strftime("%b %d, %I:%M %p PT"), "days": len(days), "since": days[0] if days else None,
           "waiting": sum(1 for r in bets.values() if not r.get("result")), "groups": groups, "sport": by_sport, "type": by_type}
    json.dump(log, open(LOG, "w"), separators=(",", ":"))
    with open("data/report.js", "w") as f:
        f.write("window.PRIMO_REPORT=" + json.dumps(out, separators=(",", ":")).replace("</", "<\\/") + ";\n")
    print("report", json.dumps(groups))

if __name__ == "__main__":
    main()
