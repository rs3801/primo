import subprocess; r=subprocess.run(["python3","scripts/fetch_sharp.py"],capture_output=True,text=True); open("probe.txt","w").write(r.stdout[-800:]+r.stderr[-500:])
