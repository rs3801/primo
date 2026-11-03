import urllib.request, json
out = []
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "primo-family-app/1.0"}), timeout=30) as r: return json.load(r)
    except Exception as e: out.append("ERR " + u + " " + str(e)); return {}
K = "https://api.elections.kalshi.com/trade-api/v2/markets?limit=400&event_ticker="
want = ["Chicago", "Caleb Williams: 2+ passing", "Caleb Williams: 225+ passing", "Colston Loveland: 40+", "Luther Burden III: 50+", "Rome Odunze: 40+", "D'Andre Swift: 1+ touchdown"]
for s in ["KXNFLGAME", "KXNFLPASSTDS", "KXNFLPASSYDS", "KXNFLRECYDS", "KXNFLTD"]:
    d = get(K + s + "-26NOV02CHISEA")
    for m in d.get("markets", []):
        lab = m.get("yes_sub_title") or m.get("subtitle") or ""
        if any(lab.startswith(w) for w in want): out.append(f"{s} | {lab} | status={m.get('status')} result={m.get('result')} last={m.get('last_price')}")
sb = get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=20261102")
for e in sb.get("events", []):
    if "Seahawks" in e.get("name", ""):
        c = e["competitions"][0]; out.append("SCORE " + " / ".join(f"{x['team']['displayName']} {x['score']}" for x in c["competitors"]) + " " + c["status"]["type"]["description"])
        s = get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event=" + e["id"])
        for t in (s.get("boxscore") or {}).get("players", []):
            if "Bears" not in t["team"]["displayName"]: continue
            for cat in t["statistics"]:
                for a in cat["athletes"]:
                    n = a["athlete"]["displayName"]
                    if any(x in n for x in ["Caleb Williams", "Loveland", "Burden", "Odunze", "Swift"]): out.append(f"{cat['name']} {n} " + " ".join(f"{k}={v}" for k, v in zip(cat.get("labels", []), a["stats"])))
open("probe.txt", "w").write("\n".join(out))
