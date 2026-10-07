from __future__ import annotations
"""BTDU corpus formulation over primitive atom-tape recipes.

A corpus is retained as:
  1) one compact ordered recipe describing paths and atom-tape segment identities; and
  2) a deduplicated entropy reservoir containing only irreducible primitive-byte atom tapes.

No conventional file/payload object is required for reconstruction.
"""
from pathlib import Path, PurePosixPath
from typing import Any
import argparse, hashlib, json, lzma, os, struct, sys, time

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
from storage_kernel import BTDUStorageKernel, BTDUStorageIntegrityError

SCHEMA="entity-btdu-corpus-formula-v1"
MAGIC=b"BTDUCF01"
HEADER=struct.Struct(">8sQ32s")

def _canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def _sha_bytes(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def _safe_relative(text:str)->Path:
    p=PurePosixPath(str(text))
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("unsafe corpus recipe path")
    return Path(*p.parts)

def _tree_root(rows:list[dict[str,Any]])->str:
    h=hashlib.sha256()
    for row in sorted(rows,key=lambda r:str(r["path"])):
        h.update(str(row["path"]).encode("utf-8")); h.update(b"\0")
        h.update(str(int(row["bytes"])).encode("ascii")); h.update(b"\0")
        h.update(str(row["sha256"]).encode("ascii")); h.update(b"\n")
    return h.hexdigest()

def _write_formula(path:Path,doc:dict[str,Any])->dict[str,Any]:
    raw=_canon(doc)
    stored=lzma.compress(raw,format=lzma.FORMAT_XZ,preset=6)
    header=HEADER.pack(MAGIC,len(stored),hashlib.sha256(raw).digest())
    payload=header+stored
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(payload)
    return {"raw_recipe_bytes":len(raw),"stored_recipe_bytes":len(payload),
            "formula_sha256":_sha_bytes(payload)}

def _read_formula(path:Path)->dict[str,Any]:
    raw=path.read_bytes()
    if len(raw)<HEADER.size: raise ValueError("truncated corpus formula")
    magic,n,digest=HEADER.unpack(raw[:HEADER.size])
    if magic!=MAGIC: raise ValueError("invalid corpus formula magic")
    stored=raw[HEADER.size:]
    if len(stored)!=int(n): raise ValueError("corpus formula stored length mismatch")
    body=lzma.decompress(stored)
    if hashlib.sha256(body).digest()!=digest: raise ValueError("corpus formula digest mismatch")
    doc=json.loads(body.decode("utf-8"))
    if doc.get("schema")!=SCHEMA: raise ValueError("unsupported corpus formula schema")
    return doc

def _disk_bytes(root:Path)->int:
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())

def build_corpus_formula(*,source_root:str|Path,manifest_path:str|Path,state_root:str|Path,
                         formula_path:str|Path,read_size:int=1024*1024)->dict[str,Any]:
    started=time.time()
    source_root=Path(source_root)
    manifest=json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    source_files=list(manifest["manifest"])
    expected_tree=str(manifest["tree_manifest_sha256"])
    if _tree_root(source_files)!=expected_tree:
        raise ValueError("input corpus manifest root mismatch")
    state_root=Path(state_root)
    store=BTDUStorageKernel(state_root/"entropy",min_chunk=64*1024,avg_chunk=256*1024,
                            max_chunk=max(read_size,256*1024),compression=True)
    entries=[]
    corpus_ref="btdu-corpus:"+expected_tree
    for i,row in enumerate(source_files,1):
        rel=str(row["path"])
        path=source_root/_safe_relative(rel)
        if not path.is_file(): raise FileNotFoundError(str(path))
        path_ref=corpus_ref+":"+hashlib.sha256(rel.encode("utf-8")).hexdigest()
        recipe=store.put_atom_tape_path(path,recipe_ref=path_ref,
                                        content_defined=False,read_size=read_size)
        if int(recipe["size_bytes"])!=int(row["bytes"]) or str(recipe["content_sha256"])!=str(row["sha256"]):
            raise BTDUStorageIntegrityError("source changed during formulation: "+rel)
        entries.append({"path":rel,"bytes":int(row["bytes"]),"sha256":str(row["sha256"]),
                        "atom_tape":recipe})
        if i%100==0:
            print(f"formulated {i}/{len(source_files)} files",flush=True)
    with store._db() as db:
        payload_objects=int(db.execute("select count(*) from payloads").fetchone()[0])
    if payload_objects!=0:
        raise BTDUStorageIntegrityError("corpus formulation created conventional payload objects")
    stats=store.stats()
    doc={"schema":SCHEMA,"formula_version":"1.0.0","corpus_ref":corpus_ref,
         "source_tree_sha256":expected_tree,"source_files":len(entries),
         "source_bytes":sum(int(x["bytes"]) for x in entries),"files":entries,
         "primitive_atom_universe_size":256,"conventional_file_storage_required":False,
         "conventional_payload_objects":0,
         "entropy_storage_root":store.storage_root(),
         "chunking":{"mode":"fixed-stream-blocks","read_size":int(read_size)}}
    formula_path=Path(formula_path)
    fstats=_write_formula(formula_path,doc)
    primary_bytes=int(stats["segment_bytes"])+int(fstats["stored_recipe_bytes"])
    operational_bytes=_disk_bytes(state_root)+int(fstats["stored_recipe_bytes"])
    source_bytes=int(doc["source_bytes"])
    result={"schema":"entity-btdu-corpus-formula-build-result-v1","pass":True,
            "formula_path":str(formula_path),"formula_sha256":fstats["formula_sha256"],
            "source_tree_sha256":expected_tree,"source_files":len(entries),"source_bytes":source_bytes,
            "recipe_bytes":fstats["stored_recipe_bytes"],"recipe_raw_bytes":fstats["raw_recipe_bytes"],
            "entropy_segment_bytes":int(stats["segment_bytes"]),
            "entropy_unique_raw_bytes":int(stats["unique_raw_chunk_bytes"]),
            "entropy_stored_chunk_bytes":int(stats["stored_chunk_bytes"]),
            "unique_chunks":int(stats["unique_chunks"]),
            "primary_authoritative_bytes":primary_bytes,
            "operational_on_disk_bytes":operational_bytes,
            "primary_reduction_fraction":1-primary_bytes/source_bytes if source_bytes else 0.0,
            "operational_reduction_fraction":1-operational_bytes/source_bytes if source_bytes else 0.0,
            "dedup_fraction":float(stats.get("dedup_fraction",0.0)),
            "payload_objects":payload_objects,"duration_seconds":time.time()-started,
            "storage_verification":store.verify(deep=False)}
    return result

def reconstruct_corpus_formula(*,formula_path:str|Path,state_root:str|Path,
                               output_root:str|Path)->dict[str,Any]:
    started=time.time()
    doc=_read_formula(Path(formula_path))
    store=BTDUStorageKernel(Path(state_root)/"entropy",min_chunk=64*1024,avg_chunk=256*1024,
                            max_chunk=max(int(doc["chunking"]["read_size"]),256*1024),compression=True)
    if store.storage_root()!=str(doc["entropy_storage_root"]):
        raise BTDUStorageIntegrityError("entropy storage root mismatch")
    out=Path(output_root); out.mkdir(parents=True,exist_ok=True)
    verified=[]
    for i,row in enumerate(doc["files"],1):
        target=out/_safe_relative(str(row["path"]))
        receipt=store.materialize_atom_tape_recipe(dict(row["atom_tape"]),target)
        if int(receipt["bytes"])!=int(row["bytes"]) or str(receipt["sha256"])!=str(row["sha256"]):
            raise BTDUStorageIntegrityError("reconstructed file mismatch: "+str(row["path"]))
        verified.append({"path":str(row["path"]),"bytes":int(row["bytes"]),"sha256":str(row["sha256"])})
        if i%100==0:
            print(f"reconstructed {i}/{len(doc['files'])} files",flush=True)
    tree=_tree_root(verified)
    return {"schema":"entity-btdu-corpus-formula-reconstruction-v1",
            "pass":tree==str(doc["source_tree_sha256"]) and len(verified)==int(doc["source_files"]),
            "files_verified":len(verified),"bytes_verified":sum(x["bytes"] for x in verified),
            "tree_sha256":tree,"expected_tree_sha256":str(doc["source_tree_sha256"]),
            "duration_seconds":time.time()-started}

def main()->None:
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd",required=True)
    b=sub.add_parser("build")
    b.add_argument("--source-root",required=True); b.add_argument("--manifest",required=True)
    b.add_argument("--state-root",required=True); b.add_argument("--formula",required=True)
    b.add_argument("--read-size",type=int,default=1024*1024); b.add_argument("--result")
    r=sub.add_parser("reconstruct")
    r.add_argument("--formula",required=True); r.add_argument("--state-root",required=True)
    r.add_argument("--output-root",required=True); r.add_argument("--result")
    ns=ap.parse_args()
    if ns.cmd=="build":
        result=build_corpus_formula(source_root=ns.source_root,manifest_path=ns.manifest,
                                    state_root=ns.state_root,formula_path=ns.formula,read_size=ns.read_size)
    else:
        result=reconstruct_corpus_formula(formula_path=ns.formula,state_root=ns.state_root,
                                         output_root=ns.output_root)
    if getattr(ns,"result",None):
        Path(ns.result).write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__": main()
