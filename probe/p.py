import urllib.request, json
UA={"User-Agent":"Mozilla/5.0 Chrome/124","Accept":"application/json"}
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=20).read())
    except Exception as e: return {"ERR":str(e)[:150]}
out=[]
E="https://site.api.espn.com/apis/site/v2/sports/"
for path,q in [("football/nfl","?week=8&seasontype=2"),("basketball/nba","?dates=20261021"),("hockey/nhl","?dates=20261021"),("baseball/mlb","?dates=20261020"),("soccer/eng.1","?dates=20261024"),("football/college-football","?groups=80&week=9")]:
    sb=get(E+path+"/scoreboard"+q); evs=sb.get("events",[])
    if not evs: out.append("%s no events %s"%(path,str(sb)[:100])); continue
    ev=evs[0]; d=get(E+path+"/summary?event="+ev["id"])
    out.append("##### %s %s | keys %s"%(path,ev["name"],list(d.keys())))
    for k in ["lastFiveGames","headToHeadGames","seasonseries","againstTheSpread","standings"]:
        if d.get(k) is not None: out.append("  %s: %s"%(k,json.dumps(d[k])[:700]))
    comp=ev["competitions"][0]
    out.append("  records: %s"%json.dumps([c.get("records") for c in comp["competitors"]])[:300])
# tennis
for lg in ["atp","wta"]:
    sb=get(E+"tennis/%s/scoreboard?dates=20261012"%lg)
    out.append("##### tennis %s keys %s events %d"%(lg,list(sb.keys()),len(sb.get("events",[]))))
    for ev in sb.get("events",[])[:1]:
        out.append("  ev keys %s name %s"%(list(ev.keys()),ev.get("name")))
        gs=ev.get("groupings") or []
        out.append("  groupings %d"%len(gs))
        if gs:
            c=gs[0]["competitions"][0]; out.append("  comp sample %s"%json.dumps(c)[:1200])
        cs=ev.get("competitions") or []
        if cs: out.append("  comp sample2 %s"%json.dumps(cs[0])[:1200])
for r in ["tennis_atp","tennis_wta"]:
    d=get("https://api.github.com/repos/JeffSackmann/%s/commits?per_page=1"%r)
    out.append("%s last commit %s"%(r,json.dumps(d)[:250] if isinstance(d,dict) else d[0]["commit"]["committer"]["date"]))
    d=get("https://api.github.com/repos/JeffSackmann/%s/contents"%r)
    out.append("  files: %s"%[x["name"] for x in d if isinstance(x,dict) and ("2025" in x["name"] or "2026" in x["name"] or "2024" in x["name"])] if isinstance(d,list) else d)
open("probe.txt","w").write("\n".join(out))
