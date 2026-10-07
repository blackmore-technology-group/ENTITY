from __future__ import annotations
"""ENTITY/BTDU lineage-bound directory assets.

Directory contents are formulated into BTDU atom-tape recipes. The directory asset
itself stores only lineage, namespace, filesystem metadata and reconstruction roots.
Conventional files may be retired only after an independent reconstruction gate passes.
"""
from pathlib import Path, PurePosixPath
from typing import Any
import hashlib
import json
import os
import stat
import tempfile
import time
import sys

_HERE=Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0,str(_HERE))

from corpus_formula import build_corpus_formula, reconstruct_corpus_formula

ASSET_SCHEMA="entity-btdu-directory-asset-v1"
RETIREMENT_SCHEMA="entity-btdu-directory-retirement-v1"
EXPORT_SCHEMA="entity-btdu-directory-export-v1"

def _canon(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def _sha(value:Any)->str:
    raw=value if isinstance(value,(bytes,bytearray)) else _canon(value)
    return hashlib.sha256(bytes(raw)).hexdigest()

def _file_sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda:fh.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def _safe_rel(text:str)->Path:
    p=PurePosixPath(str(text))
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("unsafe directory asset path")
    return Path(*p.parts)

def _tree_hash(files:list[dict[str,Any]])->str:
    h=hashlib.sha256()
    for row in sorted(files,key=lambda r:str(r["path"])):
        h.update(str(row["path"]).encode("utf-8")); h.update(b"\0")
        h.update(str(int(row["bytes"])).encode("ascii")); h.update(b"\0")
        h.update(str(row["sha256"]).encode("ascii")); h.update(b"\n")
    return h.hexdigest()

def scan_directory(source_root:str|Path)->dict[str,Any]:
    """Create a stable regular-file snapshot and detect unsupported filesystem nodes."""
    root=Path(source_root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    files=[]; dirs=[]; unsupported=[]
    for current,dirnames,filenames in os.walk(root,topdown=True,followlinks=False):
        cur=Path(current)
        kept=[]
        for name in sorted(dirnames):
            p=cur/name
            rel=p.relative_to(root).as_posix()
            st=os.lstat(p)
            attrs=int(getattr(st,"st_file_attributes",0))
            is_reparse=bool(attrs & 0x400)
            if stat.S_ISLNK(st.st_mode) or is_reparse:
                unsupported.append({"path":rel,"kind":"reparse_or_symlink","attributes":attrs})
                continue
            if not stat.S_ISDIR(st.st_mode):
                unsupported.append({"path":rel,"kind":"non_directory_node","mode":int(st.st_mode)})
                continue
            dirs.append({"path":rel,"mtime_ns":int(st.st_mtime_ns),"mode":int(st.st_mode)})
            kept.append(name)
        dirnames[:]=kept
        for name in sorted(filenames):
            p=cur/name
            rel=p.relative_to(root).as_posix()
            st=os.lstat(p)
            attrs=int(getattr(st,"st_file_attributes",0))
            is_reparse=bool(attrs & 0x400)
            if stat.S_ISLNK(st.st_mode) or is_reparse or not stat.S_ISREG(st.st_mode):
                unsupported.append({"path":rel,"kind":"non_regular_or_reparse_file","mode":int(st.st_mode),"attributes":attrs})
                continue
            if int(getattr(st,"st_nlink",1))>1:
                unsupported.append({"path":rel,"kind":"hardlinked_file","links":int(st.st_nlink)})
                continue
            files.append({
                "path":rel,"bytes":int(st.st_size),"sha256":_file_sha(p),
                "mtime_ns":int(st.st_mtime_ns),"mode":int(st.st_mode),
                "attributes":attrs,
            })
    files.sort(key=lambda r:r["path"]); dirs.sort(key=lambda r:r["path"])
    corpus_files=[{"path":r["path"],"bytes":r["bytes"],"sha256":r["sha256"]} for r in files]
    return {
        "schema":"entity-btdu-directory-scan-v1",
        "source_root":str(root),
        "files":files,"directories":dirs,"unsupported":unsupported,
        "file_count":len(files),"directory_count":len(dirs),
        "source_bytes":sum(int(r["bytes"]) for r in files),
        "tree_sha256":_tree_hash(corpus_files),
        "metadata_sha256":_sha({"files":[{k:r[k] for k in ("path","mtime_ns","mode","attributes")} for r in files],
                                "directories":dirs}),
        "retirement_eligible":not unsupported,
    }

def _write_corpus_manifest(scan:dict[str,Any],path:Path)->dict[str,Any]:
    rows=[{"path":r["path"],"bytes":int(r["bytes"]),"sha256":r["sha256"]} for r in scan["files"]]
    doc={"schema":"entity-btdu-directory-corpus-manifest-v1",
         "files":len(rows),"bytes":sum(r["bytes"] for r in rows),
         "tree_manifest_sha256":_tree_hash(rows),"manifest":rows}
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(doc,indent=2,sort_keys=True),encoding="utf-8")
    return doc

def formulate_directory_asset(*,source_root:str|Path,asset_root:str|Path,
                              owner_lineage:str,owner_entity_id:str,
                              controller_entity_id:str|None=None,
                              read_size:int=1024*1024)->dict[str,Any]:
    source=Path(source_root).resolve()
    asset_root=Path(asset_root).resolve()
    asset_root.mkdir(parents=True,exist_ok=True)
    scan=scan_directory(source)
    if scan["unsupported"]:
        raise RuntimeError("directory contains unsupported filesystem nodes; retirement blocked")
    manifest_path=asset_root/"source_manifest.json"
    corpus=_write_corpus_manifest(scan,manifest_path)
    formula_path=asset_root/"directory.btduformula"
    build=build_corpus_formula(source_root=source,manifest_path=manifest_path,
                              state_root=asset_root/"state",formula_path=formula_path,
                              read_size=read_size)
    if not build.get("pass") or int(build.get("payload_objects",-1))!=0:
        raise RuntimeError("BTDU directory formulation failed")
    identity_body={
        "schema":ASSET_SCHEMA,
        "owner_lineage":str(owner_lineage),
        "owner_entity_id":str(owner_entity_id),
        "tree_sha256":scan["tree_sha256"],
        "metadata_sha256":scan["metadata_sha256"],
        "formula_sha256":build["formula_sha256"],
        "entropy_storage_root":build["storage_verification"]["storage_root"],
    }
    asset_ref="btdu-dir:"+_sha(identity_body)
    descriptor={
        **identity_body,
        "asset_ref":asset_ref,
        "controller_entity_id":str(controller_entity_id or owner_entity_id),
        "original_root_label":str(source),
        "file_count":scan["file_count"],
        "directory_count":scan["directory_count"],
        "source_bytes":scan["source_bytes"],
        "formula_file":"directory.btduformula",
        "state_directory":"state",
        "files":[{k:r[k] for k in ("path","bytes","sha256","mtime_ns","mode","attributes")} for r in scan["files"]],
        "directories":scan["directories"],
        "unsupported":[],
        "retirement_policy":{
            "requires_independent_reconstruction":True,
            "requires_exact_tree_hash":True,
            "requires_source_unchanged":True,
            "conventional_payload_objects_allowed":False,
        },
        "build":build,
        "created_at_ns":time.time_ns(),
    }
    descriptor_path=asset_root/"directory_asset.json"
    descriptor_path.write_text(json.dumps(descriptor,indent=2,sort_keys=True),encoding="utf-8")
    return descriptor

def load_directory_asset(asset_root:str|Path)->dict[str,Any]:
    root=Path(asset_root).resolve()
    doc=json.loads((root/"directory_asset.json").read_text(encoding="utf-8"))
    if doc.get("schema")!=ASSET_SCHEMA:
        raise ValueError("unsupported directory asset schema")
    return doc

def export_directory_asset(*,asset_root:str|Path,output_root:str|Path,
                           restore_timestamps:bool=True)->dict[str,Any]:
    asset_root=Path(asset_root).resolve()
    output=Path(output_root).resolve()
    doc=load_directory_asset(asset_root)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("directory asset export target must be empty")
    output.mkdir(parents=True,exist_ok=True)
    result=reconstruct_corpus_formula(formula_path=asset_root/doc["formula_file"],
                                     state_root=asset_root/doc["state_directory"],
                                     output_root=output)
    if not result.get("pass") or result["tree_sha256"]!=doc["tree_sha256"]:
        raise RuntimeError("directory asset reconstruction failed")
    for row in sorted(doc["directories"],key=lambda r:len(PurePosixPath(r["path"]).parts)):
        (output/_safe_rel(row["path"])).mkdir(parents=True,exist_ok=True)
    if restore_timestamps:
        for row in doc["files"]:
            p=output/_safe_rel(row["path"])
            os.utime(p,ns=(int(row["mtime_ns"]),int(row["mtime_ns"])))
        for row in sorted(doc["directories"],key=lambda r:len(PurePosixPath(r["path"]).parts),reverse=True):
            p=output/_safe_rel(row["path"])
            os.utime(p,ns=(int(row["mtime_ns"]),int(row["mtime_ns"])))
    verify=scan_directory(output)
    expected_paths={r["path"] for r in doc["files"]}
    actual_paths={r["path"] for r in verify["files"]}
    passed=(verify["tree_sha256"]==doc["tree_sha256"] and expected_paths==actual_paths
            and verify["source_bytes"]==doc["source_bytes"] and not verify["unsupported"])
    return {"schema":EXPORT_SCHEMA,"pass":passed,"asset_ref":doc["asset_ref"],
            "output_root":str(output),"tree_sha256":verify["tree_sha256"],
            "files_verified":verify["file_count"],"bytes_verified":verify["source_bytes"],
            "reconstruction":result}

def retirement_gate(*,asset_root:str|Path,source_root:str|Path,
                    verification_root:str|Path)->dict[str,Any]:
    doc=load_directory_asset(asset_root)
    live=scan_directory(source_root)
    stable=(live["tree_sha256"]==doc["tree_sha256"] and live["metadata_sha256"]==doc["metadata_sha256"]
            and not live["unsupported"])
    if not stable:
        return {"schema":RETIREMENT_SCHEMA,"pass":False,"asset_ref":doc["asset_ref"],
                "reason":"source_changed_or_unsupported","source_stable":False}
    verify_root=Path(verification_root)
    if verify_root.exists() and any(verify_root.iterdir()):
        raise FileExistsError("retirement verification root must be empty")
    exported=export_directory_asset(asset_root=asset_root,output_root=verify_root)
    passed=bool(exported["pass"]) and stable
    return {"schema":RETIREMENT_SCHEMA,"pass":passed,"asset_ref":doc["asset_ref"],
            "source_stable":stable,"independent_reconstruction_pass":bool(exported["pass"]),
            "tree_sha256":doc["tree_sha256"],"source_bytes":doc["source_bytes"],
            "source_file_count":doc["file_count"],
            "retirement_authorized":passed,
            "source_deleted":False,
            "note":"Deletion is a separate explicit operation after this receipt is persisted."}

def retire_directory_source(*,asset_root:str|Path,source_root:str|Path,
                            retirement_receipt:dict[str,Any],confirmed:bool=False)->dict[str,Any]:
    """Delete one source directory only after a persisted successful retirement gate."""
    source=Path(source_root).resolve()
    doc=load_directory_asset(asset_root)
    if not confirmed:
        raise PermissionError("explicit retirement confirmation required")
    if not retirement_receipt.get("pass") or retirement_receipt.get("asset_ref")!=doc["asset_ref"]:
        raise PermissionError("valid directory retirement receipt required")
    if source.parent==source:
        raise PermissionError("refusing to retire a filesystem root")
    live=scan_directory(source)
    if live["tree_sha256"]!=doc["tree_sha256"] or live["metadata_sha256"]!=doc["metadata_sha256"]:
        raise RuntimeError("source changed after retirement gate")
    shutil.rmtree(source)
    return {"schema":"entity-btdu-directory-source-retired-v1","pass":not source.exists(),
            "asset_ref":doc["asset_ref"],"retired_root":str(source),
            "bytes_released_logical":doc["source_bytes"],"source_deleted":not source.exists()}
