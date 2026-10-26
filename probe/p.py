import subprocess; r=subprocess.run(["python3","scripts/fetch_players.py"],capture_output=True,text=True); open("probe.txt","w").write(r.stdout[-1500:]+r.stderr[-1500:])
