import urllib.request
req = urllib.request.Request("https://ntfy.sh/primo-2544a51391", data="Primo alerts are connected. You'll get a buzz when an underdog is ahead, tied or close late in a game, or when Kalshi's live price is well below ESPN's live chance.".encode(), method="POST", headers={"Title": "Primo alerts are on", "Tags": "white_check_mark", "Click": "https://rs3801.github.io/primo/"})
r = urllib.request.urlopen(req, timeout=20).read()
open("probe.txt", "w").write(r.decode()[:500])
