import urllib.request, json, traceback, datetime
UA={"User-Agent":"Mozilla/5.0","Accept":"application/json"}
K="https://api.elections.kalshi.com/trade-api/v2"
def get(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30).read())
    except Exception as e: return {"ERR":str(e)[:200]}
out=[]
try:
    s=open("data/prices.js").read(); D=json.loads(s[s.index("{"):s.rindex("}")+1])
    codes=[r[1] for r in D["G"] if r[0]=="Tennis"][:6]
    out.append("tennis codes %s"%codes)
    ser=[x for x in D["SER"] if "TENNIS" in x[0].upper() or "ATP" in x[0] or "WTA" in x[0] or "ITF" in x[0]][:10]; out.append("series %s"%ser)
    for code in codes[:3]:
        for st in set(x[0] for x in ser):
            ev=get(K+"/events/%s-%s?with_nested_markets=true"%(st,code))
            if "event" in ev:
                e=ev["event"]; out.append("EVENT %s keys %s"%(e.get("event_ticker"),list(e.keys())))
                m=(e.get("markets") or ev.get("markets") or [{}])[0]
                out.append(" market fields: "+json.dumps({k:m.get(k) for k in m if any(w in k for w in ["time","date","status","occurrence","expir","result","close","open","can_close"])}))
                out.append(" event extra: "+json.dumps({k:e.get(k) for k in e if k not in("markets",)})[:600])
                ms=get(K+"/milestones?limit=5&related_event_ticker=%s"%e.get("event_ticker")); out.append(" milestones: "+json.dumps(ms)[:1200])
                break
    ms=get(K+"/milestones?limit=3&category=Sports"); out.append("milestones generic: "+json.dumps(ms)[:1500])
except Exception: out.append(traceback.format_exc())
open("probe.txt","w").write("\n".join(map(str,out)))
