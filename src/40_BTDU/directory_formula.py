from __future__ import annotations
"""BTDU directory formulation and export.

This module never removes or modifies the source directory. It snapshots regular files,
builds a BTDU corpus formula, and can materialize the directory to an empty destination
for independent verification. Reclamation, if any, is deliberately outside this module.
"""
from pathlib import Path, PurePosixPath
from typing import Any
import hashlib
import json
import os
import stat
import sys
import time

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from corpus_formula import build_corpus_formula, reconstruct_corpus_formula

SCHEMA="entity-btdu-directory-formula-v1"

def _canon(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def _sha(value:Any)->str:
    raw=value if isinstance(value,(bytes,bytearray,memoryview)) else _canon(value)
    return hashlib.sha256(bytes(raw)).hexdigest()

def _hash_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda:fh.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def _safe_rel(value:str)->Path:
    p=PurePosixPath(str(value))
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("unsafe directory-relative path")
    return Path(*p.parts)

def _tree_root(rows:list[dict[str,Any]])->str:
    h=hashlib.sha256()
    for row in sorted(rows,key=lambda r:str(r["path"])):
        h.update(str(row["path"]).encode("utf-8"))
        h.update(b"\0")
        h.update(str(int(row["bytes"])).encode("ascii"))
        h.update(b"\0")
        h.update(str(row["sha256"]).encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()

def scan_directory(source_root:str|Path)->dict[str,Any]:
    root=Path(source_root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    files=[]
    directories=[]
    unsupported=[]
    for current,dirnames,filenames in os.walk(root,topdown=True,followlinks=False):
        cur=Path(current)
        keep=[]
        for name in sorted(dirnames):
            path=cur/name
            rel=path.relative_to(root).as_posix()
            st=os.lstat(path)
            attrs=int(getattr(st,"st_file_attributes",0))
            if stat.S_ISLNK(st.st_mode) or bool(attrs & 0x400):
                unsupported.append({"path":rel,"kind":"reparse_or_symlink"})
                continue
            if not stat.S_ISDIR(st.st_mode):
                unsupported.append({"path":rel,"kind":"non_directory_node"})
                continue
            directories.append({"path":rel,"mtime_ns":int(st.st_mtime_ns)})
            keep.append(name)
        dirnames[:]=keep
        for name in sorted(filenames):
            path=cur/name
            rel=path.relative_to(root).as_posix()
            st=os.lstat(path)
            attrs=int(getattr(st,"st_file_attributes",0))
            if stat.S_ISLNK(st.st_mode) or bool(attrs & 0x400) or not stat.S_ISREG(st.st_mode):
                unsupported.append({"path":rel,"kind":"non_regular_or_reparse"})
                continue
            if int(getattr(st,"st_nlink",1))>1:
                unsupported.append({"path":rel,"kind":"hardlinked_file"})
                continue
            files.append({
                "path":rel,
                "bytes":int(st.st_size),
                "sha256":_hash_file(path),
                "mtime_ns":int(st.st_mtime_ns),
                "attributes":attrs,
            })
    files.sort(key=lambda r:r["path"])
    directories.sort(key=lambda r:r["path"])
    basic=[{"path":r["path"],"bytes":r["bytes"],"sha256":r["sha256"]} for r in files]
    return {
        "schema":"entity-btdu-directory-scan-v1",
        "source_root":str(root),
        "files":files,
        "directories":directories,
        "unsupported":unsupported,
        "file_count":len(files),
        "directory_count":len(directories),
        "source_bytes":sum(int(r["bytes"]) for r in files),
        "tree_sha256":_tree_root(basic),
        "metadata_sha256":_sha({
            "files":[{"path":r["path"],"mtime_ns":r["mtime_ns"],"attributes":r["attributes"]} for r in files],
            "directories":directories,
        }),
        "formula_eligible":not unsupported,
    }

def build_directory_formula(*,source_root:str|Path,asset_root:str|Path,
                            owner_lineage:str,owner_entity_id:str,
                            controller_entity_id:str|None=None,
                            read_size:int=1024*1024)->dict[str,Any]:
    source=Path(source_root).resolve()
    asset=Path(asset_root).resolve()
    asset.mkdir(parents=True,exist_ok=True)
    scan=scan_directory(source)
    if scan["unsupported"]:
        raise RuntimeError("directory contains filesystem structures not supported by v1")
    rows=[{"path":r["path"],"bytes":r["bytes"],"sha256":r["sha256"]} for r in scan["files"]]
    manifest={
        "schema":"entity-btdu-directory-corpus-manifest-v1",
        "files":len(rows),
        "bytes":sum(int(r["bytes"]) for r in rows),
        "tree_manifest_sha256":_tree_root(rows),
        "manifest":rows,
    }
    manifest_path=asset/"source_manifest.json"
    manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8")
    formula_path=asset/"directory.btduformula"
    build=build_corpus_formula(
        source_root=source,
        manifest_path=manifest_path,
        state_root=asset/"state",
        formula_path=formula_path,
        read_size=read_size,
    )
    if not build.get("pass") or int(build.get("payload_objects",-1))!=0:
        raise RuntimeError("directory BTDU formulation failed")
    identity={
        "schema":SCHEMA,
        "owner_lineage":str(owner_lineage),
        "owner_entity_id":str(owner_entity_id),
        "controller_entity_id":str(controller_entity_id or owner_entity_id),
        "tree_sha256":scan["tree_sha256"],
        "metadata_sha256":scan["metadata_sha256"],
        "formula_sha256":build["formula_sha256"],
        "entropy_storage_root":build["storage_verification"]["storage_root"],
    }
    descriptor={
        **identity,
        "asset_ref":"btdu-dir:"+_sha(identity),
        "source_root_label":str(source),
        "source_bytes":scan["source_bytes"],
        "file_count":scan["file_count"],
        "directory_count":scan["directory_count"],
        "files":scan["files"],
        "directories":scan["directories"],
        "formula_file":"directory.btduformula",
        "state_directory":"state",
        "build":build,
        "created_at_ns":time.time_ns(),
        "source_is_not_modified":True,
    }
    (asset/"directory_formula.json").write_text(
        json.dumps(descriptor,indent=2,sort_keys=True),encoding="utf-8")
    return descriptor

def load_directory_formula(asset_root:str|Path)->dict[str,Any]:
    doc=json.loads((Path(asset_root)/"directory_formula.json").read_text(encoding="utf-8"))
    if doc.get("schema")!=SCHEMA:
        raise ValueError("unsupported directory formula schema")
    return doc

def export_directory_formula(*,asset_root:str|Path,output_root:str|Path)->dict[str,Any]:
    asset=Path(asset_root).resolve()
    target=Path(output_root).resolve()
    descriptor=load_directory_formula(asset)
    if target.exists() and any(target.iterdir()):
        raise FileExistsError("directory formula export target must be empty")
    target.mkdir(parents=True,exist_ok=True)
    rebuilt=reconstruct_corpus_formula(
        formula_path=asset/descriptor["formula_file"],
        state_root=asset/descriptor["state_directory"],
        output_root=target,
    )
    for row in sorted(descriptor["directories"],key=lambda r:len(PurePosixPath(r["path"]).parts)):
        (target/_safe_rel(row["path"])).mkdir(parents=True,exist_ok=True)
    check=scan_directory(target)
    passed=(
        bool(rebuilt.get("pass"))
        and check["tree_sha256"]==descriptor["tree_sha256"]
        and check["source_bytes"]==descriptor["source_bytes"]
        and check["file_count"]==descriptor["file_count"]
        and not check["unsupported"]
    )
    return {
        "schema":"entity-btdu-directory-export-v1",
        "pass":passed,
        "asset_ref":descriptor["asset_ref"],
        "output_root":str(target),
        "tree_sha256":check["tree_sha256"],
        "files_verified":check["file_count"],
        "bytes_verified":check["source_bytes"],
        "source_mutated":False,
    }

def compare_source_and_export(*,asset_root:str|Path,source_root:str|Path,
                              exported_root:str|Path)->dict[str,Any]:
    descriptor=load_directory_formula(asset_root)
    source=scan_directory(source_root)
    exported=scan_directory(exported_root)
    source_exact=(
        source["tree_sha256"]==descriptor["tree_sha256"]
        and source["metadata_sha256"]==descriptor["metadata_sha256"]
        and not source["unsupported"]
    )
    export_exact=(
        exported["tree_sha256"]==descriptor["tree_sha256"]
        and exported["source_bytes"]==descriptor["source_bytes"]
        and exported["file_count"]==descriptor["file_count"]
        and not exported["unsupported"]
    )
    return {
        "schema":"entity-btdu-directory-comparison-v1",
        "pass":source_exact and export_exact,
        "asset_ref":descriptor["asset_ref"],
        "source_exact":source_exact,
        "export_exact":export_exact,
        "tree_sha256":descriptor["tree_sha256"],
        "source_bytes":descriptor["source_bytes"],
        "file_count":descriptor["file_count"],
        "source_mutated":False,
    }
