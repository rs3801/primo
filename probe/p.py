import urllib.request, json, datetime
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}),timeout=60).read())
    except Exception as e: return {"ERR":str(e)}
out=[]
d=get("https://site.api.espn.com/apis/site/v2/sports/football/college-football/injuries")
teams=d.get("injuries",[]); out.append("teams %d"%len(teams))
recent=0; cut=(datetime.datetime.utcnow()-datetime.timedelta(days=30)).isoformat()
for t in teams:
    rows=t.get("injuries",[]); r=[x for x in rows if (x.get("date") or "")>=cut]
    recent+=len(r)
    if t.get("displayName") in ("Texas Longhorns","Ole Miss Rebels","Oklahoma Sooners","Mississippi State Bulldogs"):
        out.append("## %s total %d recent %d"%(t["displayName"],len(rows),len(r)))
        for x in rows[:15]: out.append("  %s %s %s | %s | %s"%(x.get("date"),x.get("status"),(x.get("athlete") or {}).get("displayName"),(x.get("athlete") or {}).get("position",{}).get("abbreviation") if isinstance((x.get("athlete") or {}).get("position"),dict) else "", (x.get("shortComment") or "")[:160]))
out.append("recent entries in 30 days across all teams: %d"%recent)
open("probe.txt","w").write("\n".join(out))
