from pathlib import Path
p=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network\17_Release\product\entity_windows_v1\entity_runtime.py')
s=p.read_text(encoding='utf-8')
s=s.replace('out = sdk.status(); out.update({"product":APP_NAME,"version":VERSION,"state":str(state),"core":str(core_root())})', 'out = sdk.status(); out.update({"product":APP_NAME,"version":VERSION,"state":str(state),"core":str(core_root()),"gateway":gateway_health()})')
anchor='def cmd_create_entity(args):\n'
insert='''def cmd_serve(args):\n    state=Path(args.state).resolve(); mod=_gateway_module(state)\n    server=uvicorn.Server(uvicorn.Config(mod.app,host="127.0.0.1",port=args.port,log_level="info",access_log=True))\n    server.run(); return {"stopped":True,"port":args.port,"state_dir":str(state)}\n\n'''
if insert not in s: s=s.replace(anchor,insert+anchor)
s=s.replace('s=sub.add_parser("status"); s.set_defaults(func=cmd_status)', 's=sub.add_parser("status"); s.set_defaults(func=cmd_status)\n    s=sub.add_parser("serve"); s.add_argument("--port",type=int,default=8787); s.set_defaults(func=cmd_serve)')
s=s.replace('def launch_gui(state: Path):', 'def launch_gui(state: Path, gateway=None):')
s=s.replace('info=tk.StringVar(value=f"State: {state}\\nCore: {core_root()}")', 'info=tk.StringVar(value=f"State: {state}\\nCore: {core_root()}\\nGateway: {gateway or gateway_health()}")')
s=s.replace('launch_gui(Path(args.state).resolve()); return 0', 'state=Path(args.state).resolve(); gateway=start_gateway_background(state); launch_gui(state,gateway); return 0')
p.write_text(s,encoding='utf-8')
print('PATCH2_OK')