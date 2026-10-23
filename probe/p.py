import urllib.request, json
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=30).read())
    except Exception as e: return {"ERR":str(e)}
out=[]
for u in ["https://site.api.espn.com/apis/v2/sports/football/college-football/standings?group=80",
          "https://site.api.espn.com/apis/v2/sports/football/college-football/standings",
          "https://site.api.espn.com/apis/v2/sports/football/college-football/standings?group=17"]:
    d=get(u); out.append("=== "+u+" keys "+str(list(d.keys())))
    def walk(n,depth=0):
        st=n.get("standings") or {}; e=st.get("entries") or []
        out.append("  "*depth+"%s | entries %d | children %d"%(n.get("name") or n.get("abbreviation"),len(e),len(n.get("children") or [])))
        if e and depth<3: out.append("  "*depth+"  first: "+json.dumps({"team":e[0].get("team",{}).get("displayName"),"stats":[(x.get("name"),x.get("type"),x.get("value"),x.get("displayValue")) for x in e[0].get("stats",[])][:12]})[:700])
        for c in (n.get("children") or [])[:4]: walk(c,depth+1)
    walk(d)
open("probe.txt","w").write("\n".join(out))
