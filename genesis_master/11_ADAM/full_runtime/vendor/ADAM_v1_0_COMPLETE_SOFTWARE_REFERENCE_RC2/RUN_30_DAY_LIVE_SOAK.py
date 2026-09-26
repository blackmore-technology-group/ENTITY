"""Wall-clock 30-day qualification runner. This is provided but was not executed in the build session."""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
from adam_v42.soak import run_logical_soak

p=argparse.ArgumentParser(); p.add_argument('--root', default='artifacts/live_30_day'); p.add_argument('--days', type=int, default=30)
a=p.parse_args(); root=Path(a.root); root.mkdir(parents=True, exist_ok=True)
start=time.time(); deadline=start+a.days*86400; iteration=0
while time.time()<deadline:
    report=run_logical_soak(root/f'interval_{iteration:05d}', logical_days=1, cycles_per_day=24)
    (root/'heartbeat.json').write_text(json.dumps({'iteration':iteration,'started':start,'deadline':deadline,'last_report':report.__dict__},indent=2,sort_keys=True))
    iteration+=1
    time.sleep(max(0, 3600-(time.time()-start-iteration*3600)))
