import json, urllib.request
def get(u): return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"primo"}),timeout=30))
out=[]
d=get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard")
for e in d["events"]:
  c=e["competitions"][0]; st=c["status"]
  out.append("G %s | %s | %s"%(e["shortName"],st["type"]["shortDetail"]," ".join(t["team"]["abbreviation"]+" "+str(t.get("score")) for t in c["competitors"])))
  if "POR" in e["shortName"] and "LAL" in e["shortName"]:
    s=get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event="+e["id"])
    for tb in s.get("boxscore",{}).get("players",[]):
      sx=tb["statistics"][0]; keys=sx["names"]
      for a in sx["athletes"]:
        if a.get("stats"): out.append("P %s %s %s"%(tb["team"]["abbreviation"],a["athlete"]["displayName"],dict(zip(keys,a["stats"]))))
    for t in s.get("boxscore",{}).get("teams",[]):
      out.append("T %s %s"%(t["team"]["abbreviation"],{x["label"]:x["displayValue"] for x in t.get("statistics",[])}))
    pl=s.get("plays",[])
    out.append("PLAYS %d"%len(pl))
    for p in pl[-25:]: out.append("pl %s %s %s-%s %s"%(p.get("period",{}).get("number"),p.get("clock",{}).get("displayValue"),p.get("awayScore"),p.get("homeScore"),p.get("text")))
    # lead changes / scoring by quarter
    for t in c["competitors"]: out.append("Q %s %s"%(t["team"]["abbreviation"],[x.get("value") for x in t.get("linescores",[])]))
    wp=s.get("winprobability",[])
    if wp: out.append("WP last %s"%wp[-1])
    out.append("LC %s"%json.dumps({k:v for k,v in (s.get("header",{}).get("competitions",[{}])[0]).items() if k in("leadChanges",)}))
open("probe.txt","w").write("\n".join(out))
