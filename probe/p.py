import json, urllib.request
API="https://api.elections.kalshi.com/trade-api/v2"
def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"primo"}),timeout=30))
out=[]
T="KXMVECROSSCATEGORY-S2026BDZ4YWWSKYKVFZYQ-2R3NKYHC4"
try:
    m=get(API+"/markets/"+T)["market"]
    out.append(json.dumps({k:m.get(k) for k in ["status","result","close_time"]}))
    for l in m.get("mve_selected_legs") or []:
        t=l.get("market_ticker")
        try:
            x=get(API+"/markets/"+t)["market"]
            out.append(json.dumps({"t":t,"side":l.get("side"),"title":x.get("title"),"status":x.get("status"),"result":x.get("result"),"bid":x.get("yes_bid_dollars") or x.get("yes_bid"),"ask":x.get("yes_ask_dollars") or x.get("yes_ask"),"last":x.get("last_price_dollars") or x.get("last_price"),"exp":x.get("expected_expiration_time")}))
        except Exception as e: out.append("leg err %s %s"%(t,e))
except Exception as e: out.append("ERR %s"%e)
for lg in ["basketball/nba","basketball/mens-college-basketball","football/college-football","hockey/nhl"]:
    try:
        d=get("https://site.api.espn.com/apis/site/v2/sports/%s/scoreboard?dates=20261106-20261107&limit=300"%lg)
        for e in d.get("events",[]):
            c=e["competitions"][0]; st=c["status"]["type"]
            out.append("G %s | %s | %s | %s"%(lg.split('/')[1],e["shortName"],st.get("shortDetail")," ".join(t["team"]["abbreviation"]+" "+str(t.get("score")) for t in c["competitors"])))
            if lg.endswith("nba") and st.get("state")!="pre":
                try:
                    s=get("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event="+e["id"])
                    for tb in s.get("boxscore",{}).get("players",[]):
                        sx=tb["statistics"][0]; keys=sx["names"]
                        for a in sx["athletes"]:
                            if a.get("stats"): out.append("P %s %s %s"%(e["shortName"],a["athlete"]["displayName"],dict(zip(keys,a["stats"]))))
                except Exception as ex: out.append("box err %s"%ex)
    except Exception as ex: out.append("sb err %s %s"%(lg,ex))
open("probe.txt","w").write("\n".join(out))
