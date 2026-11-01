import subprocess, os
env = dict(os.environ, NTFY_TOPIC="")
rr = subprocess.run(["python3", "scripts/alerts.py"], capture_output=True, text=True, env=env)
open("probe.txt", "w").write(rr.stdout[-4000:] + rr.stderr[-1500:])
