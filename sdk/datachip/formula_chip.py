"""EXPERIMENTAL formula-native ENTITY DataChip v0.2.

A strictly bounded, deterministic, interpreter-only DAG with fully portable
entropy. This is NOT the frozen ENTITY protocol or BTDU's authority. SHA-256
proves byte integrity, not owner identity or permission.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterator
import zipfile

from .processor import DataChipError, _canon, _sha, _zipinfo, _pairwise_no_duplicates

SCHEMA = "entity-datachip-formula-v0.2"
MAX_OUTPUT = 64 * 1024 * 1024
MAX_NODES = 8192
MAX_LITERAL = 1024 * 1024
MAX_DEPTH = 64
MAX_MANIFEST = 2 * 1024 * 1024
MAX_CHILDREN = 2048
MAX_ARCHIVE = MAX_OUTPUT + MAX_MANIFEST + MAX_NODES * 200
OPS = {"ATOM", "ENTROPY", "CONCAT", "REPEAT", "SLICE"}
HEXDIGITS = set("0123456789abcdef")


def _is_hash(value: Any) -> bool:
    return type(value) is str and len(value) == 64 and set(value) <= HEXDIGITS


def _number(value: Any, maximum: int) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise DataChipError("invalid formula number")
    return value


def _name(digest: str) -> str:
    return "entropy/" + digest + ".bin"


def _validate(doc: Any) -> dict[str, Any]:
    keys = {"schema", "chip_id", "formula_object_ref",
            "content_sha256", "content_bytes", "root", "nodes"}
    if type(doc) is not dict or set(doc) != keys or doc["schema"] != SCHEMA:
        raise DataChipError("unsupported DataChip formula schema")
    if doc["formula_object_ref"] is not None:
        ref = doc["formula_object_ref"]
        if type(ref) is not str or not (1 <= len(ref) <= 300):
            raise DataChipError("invalid BTDU reference")
    if not _is_hash(doc["content_sha256"]):
        raise DataChipError("invalid content digest")
    n = _number(doc["content_bytes"], MAX_OUTPUT)
    nodes = doc["nodes"]
    if type(nodes) is not list or not 1 <= len(nodes) <= MAX_NODES:
        raise DataChipError("node limit exceeded")
    root = _number(doc["root"], len(nodes) - 1)
    sizes: list[int] = []
    depths: list[int] = []
    for idx, node in enumerate(nodes):
        if type(node) is not dict:
            raise DataChipError("malformed DAG node")
        op = node.get("op")
        if type(op) is not str or op not in OPS:
            raise DataChipError("unknown DAG operation")
        size = _number(node.get("bytes"), MAX_OUTPUT)
        deps: list[int] = []
        if op == "ATOM":
            if set(node) != {"op", "bytes", "atom"} or size != 1:
                raise DataChipError("invalid atom")
            _number(node["atom"], 255)
        elif op == "ENTROPY":
            if set(node) != {"op", "bytes", "sha256"} or not 1 <= size <= MAX_LITERAL:
                raise DataChipError("invalid entropy node")
            if not _is_hash(node["sha256"]):
                raise DataChipError("invalid entropy hash")
        elif op == "CONCAT":
            if set(node) != {"op", "bytes", "children"}:
                raise DataChipError("invalid concat")
            child = node["children"]
            if type(child) is not list or len(child) > MAX_CHILDREN:
                raise DataChipError("too many concat children")
            deps = [_number(v, idx - 1) for v in child]
            if size != sum(sizes[i] for i in deps):
                raise DataChipError("concat length mismatch")
        elif op == "REPEAT":
            if set(node) != {"op", "bytes", "child", "count"}:
                raise DataChipError("invalid repeat")
            deps = [_number(node["child"], idx - 1)]
            count = _number(node["count"], MAX_OUTPUT)
            if count < 1 or sizes[deps[0]] == 0 or sizes[deps[0]] > MAX_LITERAL:
                raise DataChipError("invalid repeat basis/count")
            if size != sizes[deps[0]] * count:
                raise DataChipError("repeat expansion/size mismatch")
        else:
            if set(node) != {"op", "bytes", "child", "offset"}:
                raise DataChipError("invalid slice")
            deps = [_number(node["child"], idx - 1)]
            start = _number(node["offset"], MAX_OUTPUT)
            if sizes[deps[0]] > MAX_LITERAL or start + size > sizes[deps[0]]:
                raise DataChipError("slice range unsupported")
        depth = 1 + max((depths[i] for i in deps), default=0)
        if depth > MAX_DEPTH:
            raise DataChipError("DAG depth limit")
        sizes.append(size)
        depths.append(depth)
    if sizes[root] != n:
        raise DataChipError("root size mismatch")
    chip_id = doc["chip_id"]
    if type(chip_id) is not str or chip_id != "edc:formula:sha256:" + _sha(_canon({k:v for k,v in doc.items() if k!="chip_id"})):
        raise DataChipError("manifest identity digest mismatch")
    return doc


def _open(zf: zipfile.ZipFile) -> dict[str, Any]:
    infos = zf.infolist()
    if len(infos) > MAX_NODES + 1:
        raise DataChipError("archive member limit")
    if sum(item.file_size for item in infos) > MAX_OUTPUT + MAX_MANIFEST:
        raise DataChipError("archive stored bytes limit")
    names = [i.filename for i in infos]
    if len(set(names)) != len(names) or "manifest.json" not in names:
        raise DataChipError("duplicate or missing archive member")
    for info in infos:
        if info.compress_type != zipfile.ZIP_STORED or info.flag_bits & 1:
            raise DataChipError("encrypted/compressed members not supported")
        mode = (info.external_attr >> 16) & 0o170000
        if mode not in (0, 0o100000):
            raise DataChipError("non-file archive entry")
        if info.file_size > MAX_LITERAL and info.filename != "manifest.json":
            raise DataChipError("oversized archive member")
    manifest_info=zf.getinfo("manifest.json")
    if manifest_info.file_size > MAX_MANIFEST or manifest_info.compress_type != zipfile.ZIP_STORED:
        raise DataChipError("invalid manifest size")
    try:
        raw = zf.read("manifest.json")
        doc=json.loads(raw,object_pairs_hook=_pairwise_no_duplicates)
    except (UnicodeError, ValueError, OverflowError) as e:
        raise DataChipError("malformed manifest") from e
    _validate(doc)
    if raw != _canon(doc):
        raise DataChipError("noncanonical manifest")
    entropy={}
    for node in doc["nodes"]:
        if node["op"]=="ENTROPY":
            digest=node["sha256"]
            if digest in entropy and entropy[digest]!=node["bytes"]:
                raise DataChipError("conflicting entropy lengths")
            entropy[digest]=node["bytes"]
    expected={"manifest.json"} | {_name(x) for x in entropy}
    if set(names)!=expected:
        raise DataChipError("missing or unexpected entropy member")
    for key,length in entropy.items():
        if zf.getinfo(_name(key)).file_size != length:
            raise DataChipError("entropy member length mismatch")
    return doc


def inspect_formula(path: str | Path) -> dict[str, Any]:
    try:
        if Path(path).stat().st_size > MAX_ARCHIVE:
            raise DataChipError("archive physical size limit")
        with zipfile.ZipFile(path) as zf:
            return _open(zf)
    except (OSError, zipfile.BadZipFile, EOFError) as e:
        raise DataChipError("invalid formula archive") from e


def _evaluate(zf:zipfile.ZipFile, nodes:list[dict[str,Any]], index:int) -> Iterator[bytes]:
    node=nodes[index]
    op=node["op"]
    if op=="ATOM":
        yield bytes([node["atom"]])
    elif op=="ENTROPY":
        raw=zf.read(_name(node["sha256"]))
        if len(raw)!=node["bytes"] or _sha(raw)!=node["sha256"]:
            raise DataChipError("entropy digest mismatch")
        yield raw
    elif op=="CONCAT":
        for i in node["children"]:
            yield from _evaluate(zf,nodes,i)
    elif op=="REPEAT":
        # Validation limits a repeat basis to 1MiB and output to 64MiB.
        basis=b"".join(_evaluate(zf,nodes,node["child"]))
        if len(basis)!=nodes[node["child"]]["bytes"]:
            raise DataChipError("repeat basis mismatch")
        remaining=node["count"]
        per=max(1,MAX_LITERAL // len(basis))
        while remaining:
            n=min(remaining,per)
            yield basis*n
            remaining-=n
    else:
        data=b"".join(_evaluate(zf,nodes,node["child"]))
        if len(data)!=nodes[node["child"]]["bytes"]:
            raise DataChipError("slice basis mismatch")
        yield data[node["offset"]:node["offset"]+node["bytes"]]


def _verified_chunks(zf:zipfile.ZipFile, doc:dict[str,Any]) -> Iterator[bytes]:
    digest=sha256()
    size=0
    for part in _evaluate(zf,doc["nodes"],doc["root"]):
        size+=len(part)
        if size>MAX_OUTPUT:
            raise DataChipError("output limit exceeded")
        digest.update(part)
        yield part
    if size!=doc["content_bytes"] or digest.hexdigest()!=doc["content_sha256"]:
        raise DataChipError("formula output hash/length mismatch")


def verify_formula(path: str | Path) -> dict[str, Any]:
    try:
        if Path(path).stat().st_size > MAX_ARCHIVE:
            raise DataChipError("archive physical size limit")
        with zipfile.ZipFile(path) as zf:
            doc=_open(zf)
            for _ in _verified_chunks(zf,doc):
                pass
            return {"chip_id":doc["chip_id"],"integrity_verified":True,
                    "formula_native":True,"content_sha256":doc["content_sha256"],
                    "content_bytes":doc["content_bytes"],
                    "issuer_authenticated":False,"rights_authorized":False}
    except (OSError, zipfile.BadZipFile, EOFError) as e:
        raise DataChipError("invalid formula archive") from e


def _write_formula(nodes:list[dict[str,Any]],root:int,entropy:dict[str,bytes],
                   target:str|Path,content_sha256:str,content_bytes:int,
                   source_ref:str|None=None) -> dict[str,Any]:
    doc={"schema":SCHEMA,"formula_object_ref":source_ref,"nodes":nodes,
         "root":root,"content_sha256":content_sha256,"content_bytes":content_bytes}
    doc["chip_id"]="edc:formula:sha256:"+_sha(_canon(doc))
    _validate(doc)
    output=Path(target)
    if output.exists() or output.is_symlink():
        raise FileExistsError(str(output))
    output.parent.mkdir(parents=True,exist_ok=True)
    tempname=None
    try:
        with tempfile.NamedTemporaryFile(prefix=".edcf-",dir=output.parent,
                                         suffix=".tmp",delete=False) as tmp:
            tempname=tmp.name
        with zipfile.ZipFile(tempname,"w",allowZip64=True) as zf:
            for digest in sorted(entropy):
                data=entropy[digest]
                if len(data)>MAX_LITERAL or _sha(data)!=digest:
                    raise DataChipError("invalid portable entropy")
                zf.writestr(_zipinfo(_name(digest)),data)
            raw=_canon(doc)
            if len(raw)>MAX_MANIFEST:
                raise DataChipError("manifest too large")
            zf.writestr(_zipinfo("manifest.json"),raw)
        verification=verify_formula(tempname)
        if not verification["integrity_verified"]:
            raise DataChipError("failed to verify staged chip")
        os.link(tempname,output)
    finally:
        if tempname:
            Path(tempname).unlink(missing_ok=True)
    return doc


def pack_formula_bytes(data: bytes,target:str|Path) -> dict[str,Any]:
    """Create an executable-free native formula DAG from up to 64MiB of input."""
    data=bytes(data)
    if len(data)>MAX_OUTPUT:
        raise DataChipError("input exceeds formula cap")
    nodes:list[dict[str,Any]]=[]
    entropy:dict[str,bytes]={}
    def append(node:dict[str,Any]) -> int:
        if len(nodes)>=MAX_NODES:
            raise DataChipError("too many formula nodes")
        nodes.append(node)
        return len(nodes)-1
    def literal(raw:bytes) -> int:
        if len(raw)==1:
            return append({"op":"ATOM","bytes":1,"atom":raw[0]})
        if len(raw)>MAX_LITERAL:
            parts=[literal(raw[i:i+MAX_LITERAL]) for i in range(0,len(raw),MAX_LITERAL)]
            return append({"op":"CONCAT","bytes":len(raw),"children":parts})
        h=_sha(raw)
        entropy[h]=raw
        return append({"op":"ENTROPY","bytes":len(raw),"sha256":h})
    if not data:
        root=append({"op":"CONCAT","bytes":0,"children":[]})
    else:
        # Deliberate simple repeat compiler (not general-purpose compression).
        max_period=min(len(data)//4,4096)
        period=0
        probe=data[:min(len(data),8192)]
        for p in range(1,max_period+1):
            if probe[p:] != probe[:-p]:
                continue
            if data[p:] == data[:-p]:
                period=p
                break
        if period:
            basis=literal(data[:period])
            repeat_count,remainder=divmod(len(data),period)
            rep=append({"op":"REPEAT","bytes":period*repeat_count,
                        "child":basis,"count":repeat_count})
            if remainder:
                tail=literal(data[:remainder])
                root=append({"op":"CONCAT","bytes":len(data),"children":[rep,tail]})
            else:
                root=rep
        else:
            root=literal(data)
    return _write_formula(nodes,root,entropy,target,_sha(data),len(data))


def pack_formula_from_btdu(kernel:Any,object_id:str,target:str|Path) -> dict[str,Any]:
    """Port selected REAL BTDU DAG nodes (ATOM/LITERAL/CONCAT/REPEAT/SLICE).

    Semantic-tape nodes are converted into portable entropy leaves because
    their complete globally shared atom dictionary is not yet transferred.
    No kernel state is modified. This is bounded by the 64MiB v0.2 contract.
    """
    obj=kernel.object_record(object_id)
    if obj["size_bytes"]>MAX_OUTPUT or not kernel.verify_object(object_id,deep=True).get("pass"):
        raise DataChipError("unverified or oversized BTDU source")
    nodes:list[dict[str,Any]]=[]
    entropy:dict[str,bytes]={}
    memo:dict[str,int]={}
    def put(node:dict[str,Any]) -> int:
        if len(nodes)>=MAX_NODES:
            raise DataChipError("source graph exceeds node cap")
        nodes.append(node)
        return len(nodes)-1
    def visit(btdu_id:str,depth:int=0) -> int:
        if btdu_id in memo:
            return memo[btdu_id]
        if depth>MAX_DEPTH-1:
            raise DataChipError("source graph exceeds depth cap")
        row=kernel._node(btdu_id)
        op=str(row["kind"])
        recipe=json.loads(row["recipe_json"])
        size=int(row["output_bytes"])
        if op=="ATOM":
            result=put({"op":"ATOM","bytes":1,"atom":int(recipe["atom"])})
        elif op in ("LITERAL","SEMANTIC_TAPE"):
            # Uses the verified existing BTDU materializer to resolve semantic
            # tape when independent basis packaging is not available.
            raw=b"".join(kernel._iter_node(btdu_id))
            if len(raw)!=size or _sha(raw)!=row["output_sha256"]:
                raise DataChipError("BTDU leaf digest mismatch")
            if not raw:
                result=put({"op":"CONCAT","bytes":0,"children":[]})
            elif len(raw)==1:
                result=put({"op":"ATOM","bytes":1,"atom":raw[0]})
            else:
                indices=[]
                for pos in range(0,len(raw),MAX_LITERAL):
                    part=raw[pos:pos+MAX_LITERAL]
                    h=_sha(part)
                    entropy[h]=part
                    indices.append(put({"op":"ENTROPY","bytes":len(part),"sha256":h}))
                result=indices[0] if len(indices)==1 else put({
                    "op":"CONCAT","bytes":len(raw),"children":indices})
        elif op=="CONCAT":
            children=[visit(str(c),depth+1) for c in recipe["children"]]
            result=put({"op":"CONCAT","bytes":size,"children":children})
        elif op=="REPEAT":
            child=visit(str(recipe["child"]),depth+1)
            result=put({"op":"REPEAT","bytes":size,"child":child,
                        "count":int(recipe["count"])})
        elif op=="SLICE":
            child=visit(str(recipe["child"]),depth+1)
            result=put({"op":"SLICE","bytes":size,"child":child,
                        "offset":int(recipe["offset"])})
        else:
            raise DataChipError("unsupported BTDU source opcode")
        memo[btdu_id]=result
        return result
    root=visit(str(obj["root_node_id"]))
    return _write_formula(nodes,root,entropy,target,str(obj["content_sha256"]),
                          int(obj["size_bytes"]),source_ref=str(object_id))


def export_formula(path:str|Path,target:str|Path, *,
                   authorize:Any) -> dict[str,Any]:
    """Stream verified reconstruction to a new file after host decision.

    Never derive approval solely from unsigned chip metadata.
    """
    if not callable(authorize):
        raise PermissionError("trusted host rights approval is required")
    doc=inspect_formula(path)
    if authorize("dataplane:export",doc) is not True:
        raise PermissionError("host rights approval denied")
    output=Path(target)
    if output.exists() or output.is_symlink():
        raise FileExistsError(str(output))
    output.parent.mkdir(parents=True,exist_ok=True)
    tmpname=None
    try:
        with tempfile.NamedTemporaryFile(prefix=".edcf-export-",suffix=".tmp",
                                         dir=output.parent,delete=False) as tmp:
            tmpname=tmp.name
            with zipfile.ZipFile(path) as zf:
                checked=_open(zf)
                if checked!=doc:
                    raise DataChipError("manifest changed before authorized export")
                for part in _verified_chunks(zf,doc):
                    tmp.write(part)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.link(tmpname,output)
    finally:
        if tmpname:
            Path(tmpname).unlink(missing_ok=True)
    return {"chip_id":doc["chip_id"],"bytes":doc["content_bytes"],
            "sha256":doc["content_sha256"],"authorized_by":"external_host_policy"}
