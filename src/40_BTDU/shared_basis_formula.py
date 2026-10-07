from __future__ import annotations
"""BTDU shared-basis reconstructive formulation.

This codec stores a compact recipe against an already-qualified BTDU English/code/math
basis plus only the local/residual information required for exact reconstruction.
The source payload is never needed by the decoder.
"""
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
import argparse, hashlib, json, lzma, re, sqlite3, struct, zlib

SCHEMA="entity-btdu-shared-basis-formula-v1"
MAGIC_ZLIB=b"BTDUFR2\0"
MAGIC_LZMA=b"BTDUFR3\0"
MAGIC_ATOM=b"BTDUFR4\0"
MAGIC=MAGIC_ATOM
HEADER=struct.Struct(">8sIIII")
TAG_CODE=1
TAG_ENGLISH=2
TAG_MATH=3
TAG_LOCAL=4
TAG_LITERAL=5
TOKEN_RE=re.compile(rb"[A-Za-z_][A-Za-z0-9_]*|[0-9]+(?:\.[0-9]+)*|[ \t\r\n]+|[^A-Za-z0-9_\s]+")

def _canon(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def _sha_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _sha_path(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda:fh.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def _varint(n:int)->bytes:
    n=int(n)
    if n<0: raise ValueError("varint requires non-negative integer")
    out=bytearray()
    while True:
        b=n&0x7f
        n >>= 7
        if n: out.append(b|0x80)
        else:
            out.append(b)
            return bytes(out)

def _read_varint(buf:bytes,pos:int,end:int)->tuple[int,int]:
    shift=0
    value=0
    while pos<end:
        b=buf[pos]; pos+=1
        value |= (b&0x7f)<<shift
        if not (b&0x80): return value,pos
        shift += 7
        if shift>63: raise ValueError("varint overflow")
    raise ValueError("truncated varint")

def _basis_root(namespace:str,values:list[bytes])->str:
    h=hashlib.sha256()
    h.update(SCHEMA.encode()); h.update(b"\0"); h.update(namespace.encode()); h.update(b"\0")
    for value in values:
        h.update(_varint(len(value))); h.update(value)
    return h.hexdigest()

def _atom_basis_root(namespace:str,entries:list[tuple[str,bytes]])->str:
    h=hashlib.sha256()
    h.update(SCHEMA.encode()); h.update(b"\0ATOM-ID\0"); h.update(namespace.encode()); h.update(b"\0")
    for atom_id,value in entries:
        aid=str(atom_id).encode("ascii")
        h.update(_varint(len(aid))); h.update(aid)
        h.update(_varint(len(value))); h.update(value)
    return h.hexdigest()

def load_shared_basis(btdu_db:str|Path)->dict[str,Any]:
    """Load a formulation basis bound to canonical BTDU atom identities.

    Compact recipe ordinals are deterministic positions in atom-ID order. They are
    therefore local encodings of canonical atom identities, not references to an
    external language list. Legacy value-sorted views remain available only so older
    BTDUFR2/BTDUFR3 proof recipes can still be reconstructed.
    """
    db=sqlite3.connect(str(btdu_db),timeout=30)
    try:
        specs=[
            ("code","select atom_id,value_text from language_nodes where node_kind='code_token' and value_text is not null",256,False),
            ("english","select atom_id,lemma from english_lemmas where lemma is not null",128,True),
            ("math","select atom_id,name from math_terms where name is not null",256,False),
        ]
        collected={}
        for namespace,sql,max_bytes,lower in specs:
            by_value={}
            for atom_id,value in db.execute(sql):
                text=str(value).lower() if lower else str(value)
                raw=text.encode("utf-8")
                if not raw or len(raw)>max_bytes: continue
                aid=str(atom_id)
                previous=by_value.get(raw)
                if previous is None or aid<previous:
                    by_value[raw]=aid
            entries=sorted(((aid,raw) for raw,aid in by_value.items()),key=lambda item:item[0])
            legacy_values=sorted(by_value)
            collected[namespace]={
                "entries":entries,
                "values":[raw for _,raw in entries],
                "atom_ids":[aid for aid,_ in entries],
                "legacy_values":legacy_values,
            }
    finally:
        db.close()
    code=collected["code"]; english=collected["english"]; math=collected["math"]
    return {
        "code":code["values"],"english":english["values"],"math":math["values"],
        "code_atom_ids":code["atom_ids"],"english_atom_ids":english["atom_ids"],"math_atom_ids":math["atom_ids"],
        "code_map":{v:i for i,v in enumerate(code["values"])},
        "english_map":{v:i for i,v in enumerate(english["values"])},
        "math_map":{v:i for i,v in enumerate(math["values"])},
        "roots":{
            "code":_atom_basis_root("code",code["entries"]),
            "english":_atom_basis_root("english",english["entries"]),
            "math":_atom_basis_root("math",math["entries"]),
        },
        "legacy":{
            "code":code["legacy_values"],"english":english["legacy_values"],"math":math["legacy_values"],
            "roots":{
                "code":_basis_root("code",code["legacy_values"]),
                "english":_basis_root("english",english["legacy_values"]),
                "math":_basis_root("math",math["legacy_values"]),
            },
        },
        "basis_identity":"canonical-btdu-atom-id",
    }

def iter_tokens(raw:bytes)->Iterable[bytes]:
    """Tokenize semantic spans while preserving arbitrary binary gaps literally."""
    pos=0
    for match in TOKEN_RE.finditer(raw):
        if match.start()>pos:
            gap=raw[pos:match.start()]
            if gap: yield gap
        token=match.group(0)
        if token: yield token
        pos=match.end()
    if pos<len(raw):
        tail=raw[pos:]
        if tail: yield tail

def _shared_ref(token:bytes,basis:dict[str,Any])->tuple[int,int]|None:
    idx=basis["code_map"].get(token)
    if idx is not None: return TAG_CODE,idx
    if token.isascii() and token==token.lower():
        idx=basis["english_map"].get(token)
        if idx is not None: return TAG_ENGLISH,idx
    idx=basis["math_map"].get(token)
    if idx is not None: return TAG_MATH,idx
    return None

def _encode_local_dict(values:list[bytes])->bytes:
    out=bytearray(_varint(len(values)))
    for value in values:
        out.extend(_varint(len(value))); out.extend(value)
    return bytes(out)

def _decode_local_dict(raw:bytes)->list[bytes]:
    n,pos=_read_varint(raw,0,len(raw))
    out=[]
    for _ in range(n):
        size,pos=_read_varint(raw,pos,len(raw))
        end=pos+size
        if end>len(raw): raise ValueError("truncated local dictionary")
        out.append(raw[pos:end]); pos=end
    if pos!=len(raw): raise ValueError("trailing local dictionary bytes")
    return out

def _safe_relative(path_text:str)->Path:
    p=PurePosixPath(path_text)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("unsafe recipe path")
    return Path(*p.parts)

def build_formula(*,source_root:str|Path,corpus_manifest:str|Path,btdu_db:str|Path,output:str|Path)->dict[str,Any]:
    source_root=Path(source_root)
    doc=json.loads(Path(corpus_manifest).read_text(encoding="utf-8"))
    rows=list(doc["manifest"])
    basis=load_shared_basis(btdu_db)
    unmatched=Counter()
    source_bytes=0
    for row in rows:
        fp=source_root/_safe_relative(str(row["path"]))
        raw=fp.read_bytes()
        if len(raw)!=int(row["bytes"]) or _sha_bytes(raw)!=str(row["sha256"]):
            raise ValueError("source manifest mismatch: "+str(row["path"]))
        source_bytes+=len(raw)
        for token in iter_tokens(raw):
            if _shared_ref(token,basis) is None:
                unmatched[token]+=1
    local=[]
    for token,count in unmatched.items():
        if count<2 or len(token)<2: continue
        # Conservative pre-compression benefit test. The final tape is compressed too.
        ref_cost=count*3
        literal_cost=count*(len(token)+2)
        dict_cost=len(token)+4
        if literal_cost>ref_cost+dict_cost:
            local.append(token)
    local.sort()
    local_map={v:i for i,v in enumerate(local)}
    tape=bytearray()
    manifest=[]
    coverage={"code_bytes":0,"english_bytes":0,"math_bytes":0,"local_bytes":0,"literal_bytes":0,
              "code_refs":0,"english_refs":0,"math_refs":0,"local_refs":0,"literal_runs":0}
    for row in rows:
        raw=(source_root/_safe_relative(str(row["path"]))).read_bytes()
        start=len(tape)
        pending=bytearray()
        def flush_literal()->None:
            if not pending: return
            tape.append(TAG_LITERAL); tape.extend(_varint(len(pending))); tape.extend(pending)
            coverage["literal_bytes"]+=len(pending); coverage["literal_runs"]+=1
            pending.clear()
        token_count=0
        for token in iter_tokens(raw):
            token_count+=1
            shared=_shared_ref(token,basis)
            if shared is not None:
                flush_literal()
                tag,idx=shared
                tape.append(tag); tape.extend(_varint(idx))
                if tag==TAG_CODE:
                    coverage["code_bytes"]+=len(token); coverage["code_refs"]+=1
                elif tag==TAG_ENGLISH:
                    coverage["english_bytes"]+=len(token); coverage["english_refs"]+=1
                else:
                    coverage["math_bytes"]+=len(token); coverage["math_refs"]+=1
                continue
            idx=local_map.get(token)
            if idx is not None:
                flush_literal()
                tape.append(TAG_LOCAL); tape.extend(_varint(idx))
                coverage["local_bytes"]+=len(token); coverage["local_refs"]+=1
            else:
                pending.extend(token)
        flush_literal()
        end=len(tape)
        manifest.append({
            "path":str(row["path"]),"bytes":len(raw),"sha256":str(row["sha256"]),
            "recipe_offset":start,"recipe_bytes":end-start,"token_count":token_count,
        })
    basis_meta={
        "schema":"entity-btdu-formulation-basis-v1",
        "projection":"code_tokens+lowercase_english_lemmas+math_term_names",
        "counts":{"code":len(basis["code"]),"english":len(basis["english"]),"math":len(basis["math"])},
        "roots":basis["roots"],
        "identity":"canonical-btdu-atom-id",
        "atom_id_counts":{"code":len(basis["code_atom_ids"]),"english":len(basis["english_atom_ids"]),"math":len(basis["math_atom_ids"])},
        "corpus_tree_manifest_sha256":doc["tree_manifest_sha256"],
    }
    manifest_doc={"schema":"entity-btdu-formula-file-manifest-v1","files":manifest,
                  "source_bytes":source_bytes,"source_files":len(manifest)}
    basis_raw=_canon(basis_meta)
    manifest_raw=_canon(manifest_doc)
    local_raw=_encode_local_dict(local)
    tape_raw=bytes(tape)
    manifest_z=lzma.compress(manifest_raw,format=lzma.FORMAT_XZ,preset=9)
    local_z=lzma.compress(local_raw,format=lzma.FORMAT_XZ,preset=9)
    tape_z=lzma.compress(tape_raw,format=lzma.FORMAT_XZ,preset=9)
    header=HEADER.pack(MAGIC_ATOM,len(basis_raw),len(manifest_z),len(local_z),len(tape_z))
    payload=header+basis_raw+manifest_z+local_z+tape_z
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(payload)
    coverage["shared_basis_bytes"]=coverage["code_bytes"]+coverage["english_bytes"]+coverage["math_bytes"]
    coverage["shared_basis_fraction"]=coverage["shared_basis_bytes"]/source_bytes if source_bytes else 0.0
    coverage["local_reuse_fraction"]=coverage["local_bytes"]/source_bytes if source_bytes else 0.0
    coverage["literal_fraction"]=coverage["literal_bytes"]/source_bytes if source_bytes else 0.0
    return {
        "schema":SCHEMA,"formula_path":str(out),"formula_sha256":_sha_path(out),
        "source_files":len(manifest),"source_bytes":source_bytes,
        "recipe_bytes":len(payload),"reduction_fraction":1-(len(payload)/source_bytes) if source_bytes else 0.0,
        "basis":basis_meta,"local_dictionary_entries":len(local),"physical_codec":"lzma-xz-preset9",
        "components":{
            "header_bytes":HEADER.size,"basis_metadata_bytes":len(basis_raw),
            "manifest_raw_bytes":len(manifest_raw),"manifest_stored_bytes":len(manifest_z),
            "local_dictionary_raw_bytes":len(local_raw),"local_dictionary_stored_bytes":len(local_z),
            "formula_tape_raw_bytes":len(tape_raw),"formula_tape_stored_bytes":len(tape_z),
        },
        "coverage":coverage,
    }

def _load_formula(path:str|Path,btdu_db:str|Path)->tuple[dict[str,Any],list[dict[str,Any]],list[bytes],bytes]:
    raw=Path(path).read_bytes()
    if len(raw)<HEADER.size: raise ValueError("truncated formula")
    magic,nb,nm,nl,nt=HEADER.unpack(raw[:HEADER.size])
    legacy=False
    if magic==MAGIC_ZLIB:
        decompress=zlib.decompress; legacy=True
    elif magic==MAGIC_LZMA:
        decompress=lzma.decompress; legacy=True
    elif magic==MAGIC_ATOM:
        decompress=lzma.decompress
    else:
        raise ValueError("invalid formula magic")
    pos=HEADER.size
    basis_meta=json.loads(raw[pos:pos+nb].decode("utf-8")); pos+=nb
    manifest=json.loads(decompress(raw[pos:pos+nm]).decode("utf-8")); pos+=nm
    local=_decode_local_dict(decompress(raw[pos:pos+nl])); pos+=nl
    tape=decompress(raw[pos:pos+nt]); pos+=nt
    if pos!=len(raw): raise ValueError("trailing formula bytes")
    loaded=load_shared_basis(btdu_db)
    if legacy:
        basis={
            "code":loaded["legacy"]["code"],"english":loaded["legacy"]["english"],"math":loaded["legacy"]["math"],
            "roots":loaded["legacy"]["roots"]
        }
    else:
        basis=loaded
        if basis_meta.get("identity")!="canonical-btdu-atom-id":
            raise ValueError("canonical atom formula missing atom-identity basis")
    counts={"code":len(basis["code"]),"english":len(basis["english"]),"math":len(basis["math"])}
    if basis_meta.get("roots")!=basis["roots"] or basis_meta.get("counts")!=counts:
        raise ValueError("BTDU shared basis root/count mismatch")
    return basis,list(manifest["files"]),local,tape

def reconstruct_formula(*,formula:str|Path,btdu_db:str|Path,output_root:str|Path)->dict[str,Any]:
    basis,manifest,local,tape=_load_formula(formula,btdu_db)
    root=Path(output_root); root.mkdir(parents=True,exist_ok=True)
    verified=0; total=0
    for row in manifest:
        start=int(row["recipe_offset"]); end=start+int(row["recipe_bytes"])
        if start<0 or end>len(tape): raise ValueError("recipe slice out of bounds")
        pos=start; out=bytearray()
        while pos<end:
            tag=tape[pos]; pos+=1
            if tag in (TAG_CODE,TAG_ENGLISH,TAG_MATH,TAG_LOCAL):
                idx,pos=_read_varint(tape,pos,end)
                if tag==TAG_CODE: value=basis["code"][idx]
                elif tag==TAG_ENGLISH: value=basis["english"][idx]
                elif tag==TAG_MATH: value=basis["math"][idx]
                else: value=local[idx]
                out.extend(value)
            elif tag==TAG_LITERAL:
                n,pos=_read_varint(tape,pos,end); stop=pos+n
                if stop>end: raise ValueError("literal exceeds recipe slice")
                out.extend(tape[pos:stop]); pos=stop
            else:
                raise ValueError("unknown formula tag")
        target=root/_safe_relative(str(row["path"]))
        target.parent.mkdir(parents=True,exist_ok=True)
        data=bytes(out)
        if len(data)!=int(row["bytes"]) or _sha_bytes(data)!=str(row["sha256"]):
            raise ValueError("reconstructed hash/length mismatch: "+str(row["path"]))
        target.write_bytes(data)
        verified+=1; total+=len(data)
    return {"schema":"entity-btdu-formula-reconstruction-v1","pass":verified==len(manifest),
            "files_verified":verified,"bytes_verified":total,"formula_sha256":_sha_path(Path(formula))}

def main()->None:
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd",required=True)
    b=sub.add_parser("build"); b.add_argument("--source-root",required=True); b.add_argument("--manifest",required=True); b.add_argument("--btdu-db",required=True); b.add_argument("--output",required=True); b.add_argument("--result")
    r=sub.add_parser("reconstruct"); r.add_argument("--formula",required=True); r.add_argument("--btdu-db",required=True); r.add_argument("--output-root",required=True); r.add_argument("--result")
    ns=ap.parse_args()
    if ns.cmd=="build":
        result=build_formula(source_root=ns.source_root,corpus_manifest=ns.manifest,btdu_db=ns.btdu_db,output=ns.output)
    else:
        result=reconstruct_formula(formula=ns.formula,btdu_db=ns.btdu_db,output_root=ns.output_root)
    if getattr(ns,"result",None):
        Path(ns.result).write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__": main()
