"""Free hourly facts for Primo: official NFL injury report + kickoff times (ESPN),
MLB playoff probable pitchers, series score and first-pitch times (MLB). Writes data/facts.js."""
import json, time, datetime, urllib.request
from zoneinfo import ZoneInfo
PT = ZoneInfo("America/Los_Angeles")

def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "primo-family-app/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as r: return json.load(r)
        except Exception as e:
            print("retry", url, e); time.sleep(3 * (i + 1))
    return None

def nfl():
    games, inj = [], {}
    sb = get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard") or {}
    for ev in sb.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        teams = []
        for c in comp.get("competitors", []):
            t = c.get("team", {})
            teams.append({"name": t.get("displayName", ""), "loc": t.get("location", ""), "nick": t.get("name", ""), "home": c.get("homeAway") == "home"})
        state = ((ev.get("status") or {}).get("type") or {}).get("state", "")
        games.append({"sport": "Football", "league": "NFL", "start": ev.get("date", ""), "state": state, "teams": teams, "notes": []})
    ij = get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries") or {}
    for t in ij.get("injuries", []):
        rows = []
        for e in t.get("injuries", []):
            st = e.get("status", "")
            if st not in ("Out", "Doubtful", "Questionable"): continue
            a = e.get("athlete", {}); d = e.get("details") or {}
            rows.append({"player": a.get("displayName", ""), "pos": (a.get("position") or {}).get("abbreviation", ""), "status": st,
                         "injury": (d.get("type") or "").replace("Undisclosed", "undisclosed injury"), "date": (e.get("date") or "")[:10]})
        if rows: inj[t.get("displayName", "")] = rows
    return games, inj

def mlb():
    games = []
    today = datetime.datetime.now(PT).date()
    url = ("https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=%s&endDate=%s&hydrate=probablePitcher,seriesStatus"
           % (today - datetime.timedelta(days=1), today + datetime.timedelta(days=3)))
    j = get(url) or {}
    for d in j.get("dates", []):
        for g in d.get("games", []):
            tm = g.get("teams", {}); notes = []
            ss = g.get("seriesStatus") or {}
            if ss.get("shortDescription"): notes.append(ss["shortDescription"] + (": " + ss["result"] if ss.get("result") else ""))
            teams = []
            for side in ("away", "home"):
                t = tm.get(side, {}); team = t.get("team", {}); pp = t.get("probablePitcher") or {}
                name = team.get("name", "")
                w = name.split(); k = 2 if " ".join(w[-2:]) in ("Red Sox", "White Sox", "Blue Jays") else 1
                teams.append({"name": name, "loc": " ".join(w[:-k]), "nick": " ".join(w[-k:]), "home": side == "home"})
                notes.append(f"{name} starting pitcher: {pp.get('fullName') or 'not announced yet'}")
            state = (g.get("status") or {}).get("abstractGameState", "")
            games.append({"sport": "Baseball", "league": "MLB", "start": g.get("gameDate", ""), "state": state, "teams": teams, "notes": notes})
    return games

def main():
    g1, inj = nfl(); g2 = mlb()
    t = datetime.datetime.now(PT)
    out = {"asof": t.strftime("%a, %b ") + str(t.day) + ", " + t.strftime("%I:%M %p").lstrip("0") + " PT",
           "games": g1 + g2, "injuries": inj}
    if not out["games"] and not inj: raise SystemExit("No facts found; keeping the old file.")
    with open("data/facts.js", "w") as f:
        f.write("window.PRIMO_FACTS=" + json.dumps(out, separators=(",", ":")).replace("</", "<\\/") + ";\n")
    print(out["asof"], len(out["games"]), "games,", sum(len(v) for v in inj.values()), "injured players")

if __name__ == "__main__":
    main()
