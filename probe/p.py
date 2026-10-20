import urllib.request, json, sys
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36","Accept":"application/json"}
def get(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=20); return r.status, r.read().decode("utf-8","replace")
    except Exception as e: return getattr(e,"code",0), str(e)[:200]
out=[]
for u in ["https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard",
 "https://api.sofascore.com/api/v1/sport/tennis/scheduled-events/2026-10-20",
 "https://www.sofascore.com/api/v1/sport/tennis/scheduled-events/2026-10-20",
 "https://www.thesportsdb.com/api/v1/json/3/searchplayers.php?p=Andrea%20De%20Marchi",
 "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
 "https://api.sofascore.com/api/v1/sport/table-tennis/scheduled-events/2026-10-20",
 "https://api.sofascore.com/api/v1/sport/esports/scheduled-events/2026-10-20"]:
    c,b=get(u); out.append("=== %s\nHTTP %s\n%s"%(u,c,b[:300]))
c,b=get("https://api.sofascore.com/api/v1/sport/tennis/scheduled-events/2026-10-20")
try:
    ev=json.loads(b)["events"]; e=[x for x in ev if "Marchi" in json.dumps(x)] or ev
    i=e[0]["id"]; out.append("EVENT %s %s vs %s"%(i,e[0]["homeTeam"]["name"],e[0]["awayTeam"]["name"]))
    for k in ["h2h","pregame-form"]:
        c,b=get("https://api.sofascore.com/api/v1/event/%s/%s"%(i,k)); out.append("=== %s HTTP %s\n%s"%(k,c,b[:900]))
    c,b=get("https://api.sofascore.com/api/v1/event/%s/h2h/events"%e[0]["customId"]); out.append("=== h2h events HTTP %s\n%s"%(c,b[:900]))
except Exception as x: out.append("ERR %s"%x)
# ESPN NFL summary h2h
c,b=get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard")
try:
    eid=json.loads(b)["events"][0]["id"]; c,b=get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event="+eid)
    d=json.loads(b); out.append("NFL summary keys %s"%list(d.keys())); out.append("lastFive %s"%json.dumps(d.get("lastFiveGames"))[:600]); out.append("h2h %s"%json.dumps(d.get("headToHeadGames") or d.get("seasonseries"))[:600])
except Exception as x: out.append("ERR %s"%x)
open("probe.txt","w").write("\n".join(out))
