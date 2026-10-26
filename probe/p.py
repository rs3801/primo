import subprocess, json
r = subprocess.run(["python3", "scripts/fetch_sharp.py"], capture_output=True, text=True)
t = open("data/sharp.js").read()
d = json.loads(t[t.index("{"):t.rindex("}") + 1])
out = [r.stdout[-1500:], r.stderr[-800:], "size %d" % len(t)]
for s in ("Football", "Tennis", "Soccer", "Basketball"):
    gs = [g for g in d["games"] if g["s"] == s][:3]
    for g in gs: out.append(json.dumps(g)[:700])
open("probe.txt", "w").write("\n".join(out))
