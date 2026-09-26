from pathlib import Path
import sqlite3,json,shutil
root=Path(r'<LOCAL_DRIVE>/ENTITY_PRODUCTION_SCALE_STATE')
out={'exists':root.exists(),'free_gb':round(shutil.disk_usage('<LOCAL_DRIVE>/').free/1024**3,3),'files':[]}
if root.exists():
    for p in root.rglob('*.sqlite'):
        d={'path':str(p),'mb':round(p.stat().st_size/1024**2,2)}
        try:
            con=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True,timeout=1)
            tabs=[x[0] for x in con.execute("select name from sqlite_master where type='table'")]
            d['counts']={}
            for t in tabs[:10]:
                try: d['counts'][t]=con.execute('select count(*) from '+t).fetchone()[0]
                except Exception: pass
            con.close()
        except Exception as e: d['error']=str(e)
        out['files'].append(d)
print(json.dumps(out,indent=2))
