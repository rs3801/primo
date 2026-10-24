import urllib.request, json
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}),timeout=30).read())
    except Exception as e: return {"ERR":str(e)}
out=[]
E="https://site.api.espn.com/apis/site/v2/sports/football/college-football"
C="https://sports.core.api.espn.com/v2/sports/football/leagues/college-football"
for u in [E+"/injuries", E+"/teams/251/injuries", C+"/teams/251/injuries?limit=50", E+"/teams/251", E+"/news?team=251&limit=10", "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"]:
    d=get(u); out.append("=== "+u+"\n"+json.dumps(d)[:1500])
sb=get(E+"/scoreboard?groups=80&limit=300")
ev=[e for e in sb.get("events",[]) if "Texas Longhorns" in json.dumps(e) and "Ole Miss" in json.dumps(e)]
if ev:
    d=get(E+"/summary?event="+ev[0]["id"]); out.append("SUMMARY keys "+str(list(d.keys())))
    out.append("injuries: "+json.dumps(d.get("injuries"))[:1500])
    out.append("news: "+json.dumps([(a.get("headline"),a.get("description")) for a in (d.get("news") or {}).get("articles",[])])[:2500])
open("probe.txt","w").write("\n".join(out))
