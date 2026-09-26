from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, sys

PRODUCT="ENTITY"
VERSION="1.0.0-rc2.1"

def bundle_root()->Path:
    if getattr(sys,"frozen",False) and hasattr(sys,"_MEIPASS"): return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

def default_install()->Path:
    base=Path(os.environ.get("LOCALAPPDATA") or Path.home())
    return base/"Blackmore Technology Group"/"ENTITY"

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def verify_payload(root:Path)->dict:
    manifest_path=root/"PRODUCT_MANIFEST.json"
    if not manifest_path.is_file(): raise RuntimeError("PRODUCT_MANIFEST.json missing")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8-sig")); failures=[]
    for item in manifest.get("files") or []:
        p=root/str(item["path"])
        if not p.is_file(): failures.append({"path":item["path"],"reason":"missing"}); continue
        if p.stat().st_size!=int(item["bytes"]) or sha256(p)!=item["sha256"]:
            failures.append({"path":item["path"],"reason":"integrity_mismatch"})
    if failures: raise RuntimeError(f"payload verification failed: {len(failures)} file(s)")
    return {"valid":True,"files":len(manifest.get("files") or []),"manifest_sha256":sha256(manifest_path)}

def shortcut(target:Path,link:Path):
    link.parent.mkdir(parents=True,exist_ok=True)
    ps=("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('"+str(link).replace("'","''")+"');"
        "$s.TargetPath='"+str(target).replace("'","''")+"';$s.WorkingDirectory='"+str(target.parent).replace("'","''")+"';$s.Save()")
    subprocess.run(["powershell","-NoProfile","-Command",ps],check=False,capture_output=True)

def install(dest:Path,shortcuts:bool=True)->dict:
    src=bundle_root()/"payload"
    if not src.is_dir(): raise RuntimeError(f"installer payload missing: {src}")
    source_verification=verify_payload(src)
    dest=dest.resolve(); dest.mkdir(parents=True,exist_ok=True)
    for item in src.iterdir():
        out=dest/item.name
        if item.is_dir(): shutil.copytree(item,out,dirs_exist_ok=True)
        else: shutil.copy2(item,out)
    installed_verification=verify_payload(dest)
    exe=dest/"ENTITY.exe"
    if not exe.is_file(): raise RuntimeError("ENTITY.exe missing after install")
    if shortcuts:
        desktop=Path(os.environ.get("USERPROFILE",Path.home()))/"Desktop"/"ENTITY.lnk"
        start=Path(os.environ.get("APPDATA",Path.home()))/"Microsoft"/"Windows"/"Start Menu"/"Programs"/"ENTITY.lnk"
        shortcut(exe,desktop); shortcut(exe,start)
    marker={"product":PRODUCT,"version":VERSION,"install_dir":str(dest),"runtime":str(exe),"state_dir":str(default_install()/"state"),"source_verification":source_verification,"installed_verification":installed_verification,"private_keys_bundled":False}
    (dest/"INSTALLATION.json").write_text(json.dumps(marker,indent=2)+"\n",encoding="utf-8")
    return marker

def main():
    p=argparse.ArgumentParser(prog="ENTITY_Setup")
    p.add_argument("--install-dir",default=str(default_install()))
    p.add_argument("--no-shortcuts",action="store_true")
    p.add_argument("--launch",action="store_true")
    args=p.parse_args()
    try:
        result=install(Path(args.install_dir),not args.no_shortcuts)
        print(json.dumps(result,indent=2))
        if args.launch: subprocess.Popen([result["runtime"]])
        return 0
    except Exception as exc:
        print(json.dumps({"status":"ERROR","error":str(exc)},indent=2),file=sys.stderr); return 2

if __name__=="__main__": raise SystemExit(main())



