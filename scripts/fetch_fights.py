"""UFC fight facts (free ESPN feeds) -> data/fights.js
For every UFC fight in the next 8 days: each fighter's record, age, height, reach, stance, weight class, team,
style and the last 5 fights (win/loss, how, which round, against whom)."""
import json, time, datetime, urllib.request, os
from zoneinfo import ZoneInfo

PT = ZoneInfo("America/Los_Angeles")
SB = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard?dates="
CORE = "https://sports.core.api.espn.com/v2/sports/mma/athletes/"
CALLS = {"n": 0}

def get(url, tries=2):
    url = url.replace("http://", "https://")
    for i in range(tries):
        try:
            CALLS["n"] += 1
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "primo-family-app/1.0"}), timeout=30) as r:
                return json.load(r)
        except Exception as e:
            print("retry", i + 1, url[-70:], e); time.sleep(1.5)
    return None

def load(p, d):
    try: return json.load(open(p))
    except Exception: return d

def fighter(aid, cache, past):
    now = time.time(); c = cache.get(aid)
    if c and now - c.get("t", 0) < 12 * 3600: return c["f"]
    a = get(CORE + aid) or {}
    f = {"name": a.get("displayName", ""), "age": a.get("age"), "ht": a.get("displayHeight"), "reach": a.get("displayReach"), "wt": a.get("displayWeight"),
         "stance": (a.get("stance") or {}).get("text"), "wc": (a.get("weightClass") or {}).get("text"), "team": (a.get("association") or {}).get("name"),
         "style": ", ".join(s.get("text", "") for s in a.get("styles") or []), "from": a.get("citizenship"), "last": []}
    el = get(CORE + aid + "/eventlog") or {}
    for it in ((el.get("events") or {}).get("items") or []):
        if not it.get("played") or len(f["last"]) >= 5: continue
        cref = (it.get("competition") or {}).get("$ref", "")
        key = cref.split("/competitions/")[-1].split("?")[0]
        if key in past: r = past[key]
        else:
            cm = get(cref) or {}
            st = get(((cm.get("status") or {}).get("$ref")) or "") or {}
            res = st.get("result") or {}
            comps = cm.get("competitors") or []
            r = {"d": (cm.get("date") or "")[:10], "how": res.get("shortDisplayName") or res.get("displayName") or "", "det": res.get("displayDescription") or "",
                 "rd": st.get("period"), "t": st.get("displayClock"), "w": {str(x.get("id")): bool(x.get("winner")) for x in comps}, "names": {}}
            for x in comps:
                ar = (x.get("athlete") or {}).get("$ref")
                if ar and str(x.get("id")) != aid:
                    o = get(ar) or {}; r["names"][str(x.get("id"))] = o.get("displayName", "")
            past[key] = r
        won = r["w"].get(aid)
        if won is None: continue
        opp = next((n for i, n in r.get("names", {}).items() if i != aid), "") or "?"
        draw = not any(r["w"].values())
        f["last"].append({"r": "D" if draw else ("W" if won else "L"), "how": r["how"], "det": r["det"], "rd": r["rd"], "t": r["t"], "opp": opp, "d": r["d"]})
    cache[aid] = {"t": now, "f": f}
    return f

def main():
    cache = load("data/fighter_cache.json", {}); past = load("data/fight_past.json", {})
    today = datetime.datetime.now(PT).date(); fights = []
    seen = set()
    for i in range(0, 9):
        d = get(SB + (today + datetime.timedelta(days=i)).strftime("%Y%m%d")) or {}
        for ev in d.get("events") or []:
            for c in ev.get("competitions") or []:
                if c.get("id") in seen: continue
                st = ((c.get("status") or {}).get("type") or {})
                if st.get("state") != "pre": continue
                seen.add(c.get("id"))
                side = []
                for x in c.get("competitors") or []:
                    f = fighter(str(x.get("id")), cache, past)
                    f = dict(f); f["rec"] = ([r.get("summary") for r in x.get("records") or []] or [""])[0]
                    side.append(f)
                if len(side) == 2:
                    fights.append({"ev": ev.get("name", ""), "start": c.get("date") or c.get("startDate"), "wc": (c.get("type") or {}).get("abbreviation", ""),
                                   "rounds": (c.get("format") or {}).get("regulation", {}).get("periods"), "f": side})
    now = time.time()
    cache = {k: v for k, v in cache.items() if now - v.get("t", 0) < 10 * 86400}
    json.dump(cache, open("data/fighter_cache.json", "w"), separators=(",", ":"))
    json.dump(past, open("data/fight_past.json", "w"), separators=(",", ":"))
    out = {"asof": datetime.datetime.now(PT).strftime("%b %d, %I:%M %p PT"), "fights": fights}
    with open("data/fights.js", "w") as f:
        f.write("window.PRIMO_FIGHTS=" + json.dumps(out, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/") + ";\n")
    print("fights:", len(fights), "calls:", CALLS["n"], "size:", os.path.getsize("data/fights.js"))

if __name__ == "__main__":
    main()
