import urllib.request, re, json
out = []
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept": "text/html,application/json"}
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=25) as r:
            b = r.read(); return r.status, r.geturl(), b.decode("utf8", "replace")
    except Exception as e:
        return getattr(e, "code", None), u, str(e)[:300] + (" " + e.read().decode("utf8","replace")[:300] if hasattr(e, "read") else "")
for u in ["https://predictions.draftkings.com/", "https://predictions.draftkings.com/sports", "https://www.draftkings.com/predictions",
          "https://sportsbook.draftkings.com/", "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusca/v1/leagues/88808",
          "https://sportsbook-nash.draftkings.com/api/sportscontent/dkusnj/v1/leagues/88808"]:
    st, fu, b = get(u)
    out.append(f"== {u} -> {st} {fu} len={len(b)}")
    out.append(b[:600].replace("\n", " "))
    hosts = sorted(set(re.findall(r"https?://[a-z0-9.-]*(?:draftkings|dkn|railbird)[a-z0-9.-]*", b)))[:40]
    out.append("hosts: " + " ".join(hosts))
    js = re.findall(r'src="([^"]+\.js)"', b)[:8]; out.append("js: " + " ".join(js))
    out.append("api-ish: " + " ".join(sorted(set(re.findall(r'["\'](/api/[^"\']{3,80})', b)))[:30]))
open("probe.txt", "w").write("\n".join(out))
