import urllib.request, json
out=[]
def head(u):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Origin":"https://rs3801.github.io","Accept":"application/json"}),timeout=30)
        h=dict(r.headers); b=r.read()[:600].decode("utf-8","replace")
        return r.status, {k:v for k,v in h.items() if "access-control" in k.lower()}, b
    except Exception as e: return 0, str(e)[:200], ""
for u in ["https://api.elections.kalshi.com/trade-api/v2/markets?limit=2&status=open",
          "https://api.elections.kalshi.com/trade-api/v2/milestones?limit=1&category=Sports",
          "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=80",
          "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event=401909834"]:
    s,h,b=head(u); out.append("=== %s\n%s %s\n%s"%(u,s,h,b[:300]))
# live data endpoints on Kalshi
d=json.loads(urllib.request.urlopen(urllib.request.Request("https://api.elections.kalshi.com/trade-api/v2/milestones?limit=5&category=Sports&minimum_start_date=2026-10-24T00:00:00Z",headers={"User-Agent":"Mozilla/5.0"}),timeout=30).read())
for m in d.get("milestones",[])[:2]:
    for path in ["/live_data/%s/milestone/%s"%(m.get("type"),m.get("id")), "/live_data/milestone/%s"%m.get("id")]:
        s,h,b=head("https://api.elections.kalshi.com/trade-api/v2"+path); out.append("LIVE %s -> %s %s %s"%(path,s,h,b[:500]))
open("probe.txt","w").write("\n".join(map(str,out)))
