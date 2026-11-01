import urllib.request, json
r = urllib.request.urlopen(urllib.request.Request("https://ntfy.sh/primo-2544a51391/json?poll=1&since=4h", headers={"User-Agent": "x"}), timeout=30).read().decode()
out = []
for line in r.splitlines():
    try: m = json.loads(line)
    except Exception: continue
    out.append("%s | %s | %s" % (m.get("time"), m.get("title"), (m.get("message") or "")[:300]))
open("probe.txt", "w").write("\n".join(out))
