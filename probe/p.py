import json, urllib.request
API="https://api.elections.kalshi.com/trade-api/v2"
def get(p):
    return json.load(urllib.request.urlopen(urllib.request.Request(API+p,headers={"User-Agent":"primo"}),timeout=30))
out=[]
T="KXMVECROSSCATEGORY-S20265PVOW4T4E4PCYKW6-OXE7QWEFF"
try:
    m=get("/markets/"+T)["market"]
    out.append(json.dumps({k:m.get(k) for k in ["title","yes_sub_title","no_sub_title","status","result","yes_ask","yes_bid","last_price","close_time","expected_expiration_time"]}))
    legs=m.get("mve_selected_legs") or []
    out.append("LEGS %d"%len(legs))
    for l in legs:
        t=l.get("market_ticker"); side=l.get("side")
        try:
            x=get("/markets/"+t)["market"]
            out.append(json.dumps({"t":t,"side":side,"title":x.get("title"),"yes":x.get("yes_sub_title"),"status":x.get("status"),"result":x.get("result"),"ask":x.get("yes_ask"),"bid":x.get("yes_bid"),"last":x.get("last_price"),"exp":x.get("expected_expiration_time")}))
        except Exception as e: out.append("leg err %s %s"%(t,e))
except Exception as e: out.append("ERR %s"%e)
open("probe.txt","w").write("\n".join(out))
