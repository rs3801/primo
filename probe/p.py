import subprocess, os, json, time, sys
d = json.load(open("live.json")); d["ts"] = time.time(); json.dump(d, open("live.json", "w"))   # treat as fresh for the test
env = dict(os.environ, NTFY_TOPIC="")
rr = subprocess.run(["python3", "scripts/alerts.py"], capture_output=True, text=True, env=env)
sys.path.insert(0, "scripts"); import alerts
out = [rr.stdout[-5000:] + rr.stderr[-1500:]]
open("probe.txt", "w").write("\n".join(out))
