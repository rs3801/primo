import json, urllib.request
def get(u):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "primo-family-app/1.0"}), timeout=30))
    except Exception as e: return {"err": str(e)}
A = "https://api.elections.kalshi.com/trade-api/v2"
out = []
for ev in ["KXNCAAFGAME-26OCT31MICHRUTG", "KXNCAAFGAME-26OCT31SMUSYR"]:
    d = get(A + "/markets?event_ticker=" + ev)
    for m in d.get("markets", []):
        out.append(json.dumps({k: m.get(k) for k in ("ticker", "status", "yes_sub_title", "yes_bid_dollars", "yes_ask_dollars", "close_time", "expected_expiration_time", "volume_fp")}))
    out.append(json.dumps(get(A + "/events/" + ev))[:600])
open("probe.txt", "w").write("\n".join(out))
