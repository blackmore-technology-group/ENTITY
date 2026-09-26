from __future__ import annotations
from pathlib import Path
import argparse, base64, hashlib, hmac, importlib.util, ipaddress, json, mimetypes, os, re, secrets, shutil, socket, socketserver, sqlite3, struct, subprocess, sys, tempfile, threading, time, uuid, zipfile
import dataclasses, datetime, typing
import urllib.request, urllib.error
import fastapi, uvicorn
import cryptography  # bundled dependency for dynamically loaded canonical modules
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

APP_NAME = "ENTITY"
VERSION = "1.0.0-rc2.1"

def install_root() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent

def core_root() -> Path:
    override = os.environ.get("ENTITY_CORE_ROOT")
    return Path(override).resolve() if override else install_root() / "core"

def default_state() -> Path:
    override = os.environ.get("ENTITY_STATE_DIR")
    if override: return Path(override).resolve()
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base / "Blackmore Technology Group" / "ENTITY" / "state"

def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader: raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def gateway_health(port: int = 8787):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.75) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None

def _gateway_module(state: Path):
    os.environ["ENTITY_STATE_DIR"] = str(state.resolve())
    return load_module(f"entity_product_gateway_{os.getpid()}_{int(time.time()*1000)}", core_root() / "14_Protocols_SDK" / "open_entity_sdk" / "entity_open_sdk_gateway.py")

def start_gateway_background(state: Path, port: int = 8787):
    state=state.resolve(); current=gateway_health(port)
    if current:
        active=Path(str(current.get("state_dir") or "")).resolve()
        if active != state: raise RuntimeError(f"ENTITY gateway port {port} already serves different state: {active}")
        return {"active":True,"reused":True,"port":port,"state_dir":str(state)}
    if getattr(sys,"frozen",False):
        cli=install_root()/"ENTITY_CLI.exe"
        if not cli.is_file(): raise RuntimeError(f"ENTITY_CLI.exe missing: {cli}")
        flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
        subprocess.Popen([str(cli),"--state",str(state),"serve","--port",str(port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
    else:
        mod=_gateway_module(state); server=uvicorn.Server(uvicorn.Config(mod.app,host="127.0.0.1",port=port,log_level="warning",access_log=False))
        threading.Thread(target=server.run,name="ENTITY-OpenSDK-Gateway",daemon=True).start()
    for _ in range(150):
        health=gateway_health(port)
        if health: return {"active":True,"reused":False,"port":port,"state_dir":health.get("state_dir")}
        time.sleep(0.1)
    raise RuntimeError("ENTITY Open SDK gateway failed to start")

def sdk_for(state: Path):
    root = core_root()
    mod = load_module("entity_product_simple_sdk", root / "14_Protocols_SDK" / "simple_sdk" / "canonical_simple_entity_sdk.py")
    return mod.SimpleEntitySDK(state)

def portability_for(state: Path):
    root = core_root()
    ident = load_module("entity_product_identity", root / "01_Core_Runtime" / "identity" / "canonical_identity.py")
    port = load_module("entity_product_portability", root / "15_Operations" / "backups" / "canonical_portable_state.py")
    vault = ident.EntityIdentityVault(state)
    return vault, port.PortableStateManager(state, vault)

def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()

def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def cmd_status(args):
    state = Path(args.state).resolve(); sdk = sdk_for(state)
    out = sdk.status(); out.update({"product":APP_NAME,"version":VERSION,"state":str(state),"core":str(core_root()),"gateway":gateway_health()})
    return out

def cmd_serve(args):
    state=Path(args.state).resolve(); mod=_gateway_module(state)
    server=uvicorn.Server(uvicorn.Config(mod.app,host="127.0.0.1",port=args.port,log_level="info",access_log=True))
    server.run(); return {"stopped":True,"port":args.port,"state_dir":str(state)}

def cmd_create_entity(args):
    sdk = sdk_for(Path(args.state)); meta = {"created_by":"ENTITY Windows","product_version":VERSION}
    return sdk.create_entity(args.name, entity_type=args.type, alias=args.alias, metadata=meta)

def cmd_create_device(args):
    sdk = sdk_for(Path(args.state)); meta = {"role":"device","platform":"windows","product_version":VERSION}
    return sdk.create_entity(args.name, entity_type="system", alias=args.alias, metadata=meta)

def cmd_create_app(args):
    sdk = sdk_for(Path(args.state))
    return sdk.create_application(args.name, args.alias, controller_entity_id=args.controller,
                                  metadata={"created_by":"ENTITY Windows","product_version":VERSION})

def cmd_pair(args):
    sdk = sdk_for(Path(args.state))
    out = sdk.pair_device(principal_entity_id=args.principal, application_entity_id=args.app,
                          device_entity_id=args.device, display_name=args.name, alias=args.alias,
                          metadata={"product_version":VERSION})
    if args.out: save_json(Path(args.out), out)
    return out

def cmd_register(args):
    sdk = sdk_for(Path(args.state)); binding = load_json(Path(args.binding)); p = Path(args.file).resolve()
    return sdk.register_asset(binding, content_sha256=sha_file(p), size_bytes=p.stat().st_size,
                              media_type=args.media_type, title=args.title or p.name,
                              asset_kind=args.kind, classification=args.classification,
                              metadata={"source_filename":p.name,"product_version":VERSION})

def cmd_event(args):
    sdk = sdk_for(Path(args.state)); binding = load_json(Path(args.binding))
    digest = hashlib.sha256(args.payload.encode("utf-8")).hexdigest()
    return sdk.record_event(binding, event_type=args.event_type, payload_sha256=digest,
                            evidence_origin="DIRECT_OBSERVATION", confidence=1.0)

def cmd_export(args):
    return sdk_for(Path(args.state)).export_entity(args.entity, Path(args.dest))

def cmd_verify_export(args):
    return sdk_for(Path(args.state)).verify_export(Path(args.dest))

def cmd_backup(args):
    state = Path(args.state); _, manager = portability_for(state)
    result = manager.create_encrypted_backup(Path(args.dest))
    key_path = Path(args.key_out)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(result["key_b64"] + "\n", encoding="utf-8")
    safe = dict(result); safe["key_b64"] = "WRITTEN_TO_KEY_FILE"; safe["key_file"] = str(key_path)
    return safe

def cmd_restore(args):
    _, manager = portability_for(Path(args.state))
    key = base64.urlsafe_b64decode(Path(args.key_file).read_text(encoding="utf-8").strip())
    return manager.restore_encrypted_backup(Path(args.backup), key, Path(args.target_state))

def cmd_verify_state(args):
    vault, _ = portability_for(Path(args.state)); manifest = vault.load_manifest(args.entity)
    return {"valid":vault.verify_manifest(manifest),"entity_id":args.entity,"state":str(Path(args.state).resolve())}

def build_parser():
    p=argparse.ArgumentParser(prog="ENTITY",description="ENTITY Windows 1.0 RC2")
    p.add_argument("--state",default=str(default_state()))
    sub=p.add_subparsers(dest="command")
    s=sub.add_parser("status"); s.set_defaults(func=cmd_status)
    s=sub.add_parser("serve"); s.add_argument("--port",type=int,default=8787); s.set_defaults(func=cmd_serve)
    s=sub.add_parser("create-entity"); s.add_argument("--name",required=True); s.add_argument("--alias"); s.add_argument("--type",default="person"); s.set_defaults(func=cmd_create_entity)
    s=sub.add_parser("create-device"); s.add_argument("--name",required=True); s.add_argument("--alias"); s.set_defaults(func=cmd_create_device)
    s=sub.add_parser("create-app"); s.add_argument("--name",required=True); s.add_argument("--alias",required=True); s.add_argument("--controller"); s.set_defaults(func=cmd_create_app)
    s=sub.add_parser("pair"); s.add_argument("--principal",required=True); s.add_argument("--app",required=True); s.add_argument("--device",required=True); s.add_argument("--name",required=True); s.add_argument("--alias",required=True); s.add_argument("--out"); s.set_defaults(func=cmd_pair)
    s=sub.add_parser("register"); s.add_argument("--binding",required=True); s.add_argument("--file",required=True); s.add_argument("--title"); s.add_argument("--kind",default="DATA"); s.add_argument("--classification",default="PRIVATE"); s.add_argument("--media-type",default="application/octet-stream"); s.set_defaults(func=cmd_register)
    s=sub.add_parser("event"); s.add_argument("--binding",required=True); s.add_argument("--event-type",required=True); s.add_argument("--payload",required=True); s.set_defaults(func=cmd_event)
    s=sub.add_parser("export"); s.add_argument("--entity",required=True); s.add_argument("--dest",required=True); s.set_defaults(func=cmd_export)
    s=sub.add_parser("verify-export"); s.add_argument("--dest",required=True); s.set_defaults(func=cmd_verify_export)
    s=sub.add_parser("backup"); s.add_argument("--dest",required=True); s.add_argument("--key-out",required=True); s.set_defaults(func=cmd_backup)
    s=sub.add_parser("restore"); s.add_argument("--backup",required=True); s.add_argument("--key-file",required=True); s.add_argument("--target-state",required=True); s.set_defaults(func=cmd_restore)
    s=sub.add_parser("verify-state"); s.add_argument("--entity",required=True); s.set_defaults(func=cmd_verify_state)
    return p

def preferred_local_person_identity(sdk, username: str | None = None, override: str | None = None):
    requested=str(override or os.environ.get("ENTITY_ACTIVE_IDENTITY") or "").strip()
    if requested:
        entity_id=sdk.resolve_entity_id(requested)
        return sdk.identity.load_manifest(entity_id)
    people=[m for m in sdk.identity.list_local() if str(m.get("entity_type") or "").lower()=="person"]
    if not people:
        return None
    user=str(username if username is not None else os.environ.get("USERNAME") or os.environ.get("USER") or "").strip().casefold()
    if user:
        matches=[]
        for manifest in people:
            aliases=[str(x).casefold() for x in (manifest.get("aliases") or [])]
            display=str(manifest.get("display_name") or "").casefold()
            if user==display or user in display.split() or any(a==user or a.startswith(user+".") for a in aliases):
                matches.append(manifest)
        if len(matches)==1:
            return matches[0]
    if len(people)==1:
        return people[0]
    return None

def launch_gui(state: Path, gateway=None):
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog
    sdk=sdk_for(state)
    active=preferred_local_person_identity(sdk)
    active_text="Not automatically selected"
    if active:
        aliases=list(active.get("aliases") or [])
        alias=aliases[0] if aliases else ""
        active_text=f"{active.get('display_name')}  {alias}  {active.get('entity_id')}"
    root=tk.Tk(); root.title(f"ENTITY {VERSION}"); root.geometry("900x560")
    tk.Label(root,text="ENTITY",font=("Segoe UI",26,"bold")).pack(pady=(18,2))
    tk.Label(root,text="Persistent identity, authority, provenance and portable history",font=("Segoe UI",10)).pack()
    info=tk.StringVar(value=f"Active identity: {active_text}\nState: {state}\nCore: {core_root()}\nGateway: {gateway or gateway_health()}")
    tk.Label(root,textvariable=info,justify="left",anchor="w").pack(fill="x",padx=24,pady=14)
    log=tk.Text(root,height=16,wrap="word"); log.pack(fill="both",expand=True,padx=24,pady=8)
    def show(v): log.delete("1.0","end"); log.insert("end",json.dumps(v,indent=2,default=str))
    def status():
        try: show(cmd_status(argparse.Namespace(state=str(state))))
        except Exception as e: messagebox.showerror("ENTITY",str(e))
    def create_person():
        name=simpledialog.askstring("Create Entity","Display name:"); alias=simpledialog.askstring("Create Entity","Alias (optional, e.g. name.entity):")
        if name:
            try: show(sdk.create_entity(name,entity_type="person",alias=alias or None,metadata={"created_by":"ENTITY Windows","product_version":VERSION}))
            except Exception as e: messagebox.showerror("ENTITY",str(e))
    def export_entity_gui():
        target=active
        entity_ref=str(target.get("entity_id")) if target else simpledialog.askstring(
            "Export My Entity","Entity ID or alias (for example shawn.blackmore.entity):"
        )
        if not entity_ref:
            return
        dest=filedialog.askdirectory(title="Choose export folder")
        if dest:
            try: show(sdk.export_entity(entity_ref,Path(dest)))
            except Exception as e: messagebox.showerror("ENTITY",str(e))
    buttons=tk.Frame(root); buttons.pack(fill="x",padx=24,pady=(4,14))
    tk.Button(buttons,text="Status",command=status,width=16).pack(side="left",padx=4)
    tk.Button(buttons,text="Create Entity",command=create_person,width=16).pack(side="left",padx=4)
    tk.Button(buttons,text="Export My Entity",command=export_entity_gui,width=18).pack(side="left",padx=4)
    tk.Button(buttons,text="Close",command=root.destroy,width=12).pack(side="right",padx=4)
    status(); root.mainloop()

def main():
    parser=build_parser(); args=parser.parse_args()
    if not args.command:
        state=Path(args.state).resolve(); gateway=start_gateway_background(state); launch_gui(state,gateway); return 0
    try:
        out=args.func(args); print(json.dumps(out,indent=2,sort_keys=True,default=str))
        if isinstance(out,dict) and out.get("valid") is False: return 2
        return 0
    except Exception as exc:
        print(json.dumps({"status":"ERROR","error":str(exc),"command":args.command},indent=2),file=sys.stderr)
        return 2

if __name__=="__main__": raise SystemExit(main())



