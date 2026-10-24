import urllib.request, json
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=30).read())
    except Exception as e: return {"ERR":str(e)}
out=[]
for path,q in [("football/college-football","?groups=80"),("basketball/nba",""),("hockey/nhl",""),("soccer/eng.1",""),("football/nfl","")]:
    sb=get("https://site.api.espn.com/apis/site/v2/sports/"+path+"/scoreboard"+q)
    live=[e for e in sb.get("events",[]) if ((e.get("status") or {}).get("type") or {}).get("state")=="in"]
    out.append("##### %s live %d"%(path,len(live)))
    if not live: continue
    e=live[0]; c=e["competitions"][0]
    out.append("scoreboard situation: "+json.dumps(c.get("situation"))[:700])
    out.append("scoreboard competitor stats: "+json.dumps([ (x.get("team",{}).get("abbreviation"), [ (s.get("name"),s.get("displayValue")) for s in (x.get("statistics") or [])][:12]) for x in c.get("competitors",[])])[:700])
    d=get("https://site.api.espn.com/apis/site/v2/sports/"+path+"/summary?event="+e["id"])
    out.append("summary keys "+str(list(d.keys())))
    wp=d.get("winprobability") or []; out.append("wp len %d last %s first %s"%(len(wp), json.dumps(wp[-1:])[:200], json.dumps(wp[:1])[:200]))
    out.append("situation: "+json.dumps(d.get("situation"))[:600])
    bx=(d.get("boxscore") or {}).get("teams") or []
    out.append("box: "+json.dumps([ (t.get("team",{}).get("abbreviation"), [(s.get("name"),s.get("displayValue")) for s in t.get("statistics",[])][:25]) for t in bx])[:1500])
    out.append("header status: "+json.dumps(((d.get("header") or {}).get("competitions") or [{}])[0].get("status"))[:300])
open("probe.txt","w").write("\n".join(out))
