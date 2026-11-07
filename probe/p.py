import sys, json; sys.path.insert(0, "probe")
import alerts_t as A
out=[]
for lg in ["basketball/nba","basketball/mens-college-basketball"]:
  d=A.get(A.ESPN+lg+"/scoreboard"+("?groups=50&limit=300" if "college" in lg else "")) or {}
  for e in d.get("events",[])[:60]:
    c=e["competitions"][0]; st=c["status"]
    if st["type"]["state"] not in ("in","post"): continue
    H=[x for x in c["competitors"] if x["homeAway"]=="home"][0]; Aw=[x for x in c["competitors"] if x["homeAway"]=="away"][0]
    for dog,fav,home in ((Aw,H,False),):
      try:
        r=A.game_story(lg,e["id"],"Basketball",dog["team"]["id"],fav["team"]["id"],home,dog["team"]["shortDisplayName"],fav["team"]["shortDisplayName"])
        diff=int(float(dog["score"]))-int(float(fav["score"]))
        left=A.mins_left("Basketball",lg,st.get("period"),st.get("displayClock"))
        out.append(e["shortName"]+" "+st["type"]["shortDetail"]+" | "+A.story_line("Basketball",r[5],dog["team"]["shortDisplayName"],fav["team"]["shortDisplayName"],diff,left,r[4],r[2],None)+" | flow "+json.dumps(r[5]))
      except Exception as ex: out.append("err %s %s"%(e["shortName"],ex))
    if len(out)>12: break
open("probe.txt","w").write("\n".join(out))
