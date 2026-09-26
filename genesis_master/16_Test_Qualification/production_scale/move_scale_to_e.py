from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\production_scale\run_million_scale.py")
s=p.read_text(encoding='utf-8')
s=s.replace("STATE=Path(r\"<LOCAL_DRIVE>/ENTITY_PRODUCTION_SCALE_STATE\")","STATE=Path(r\"<LOCAL_DRIVE>/ENTITY_PRODUCTION_SCALE_STATE\")")
s=s.replace("ASSET_BATCH=5_000","ASSET_BATCH=10_000").replace("EVENT_BATCH=10_000","EVENT_BATCH=25_000")
s=s.replace("MIN_FREE=700*1024*1024","MIN_FREE=10*1024*1024*1024")
s=s.replace("def free_bytes(): return shutil.disk_usage('<LOCAL_DRIVE>/').free","def free_bytes(): return shutil.disk_usage(str(STATE.anchor)).free")
s=s.replace("    if os.name=='nt': subprocess.run(['compact','/c','/i','/q',str(STATE)],capture_output=True,text=True)\n","")
p.write_text(s,encoding='utf-8'); print('scale state moved to E and batch sizes increased')
