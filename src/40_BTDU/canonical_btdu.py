from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Iterable
import hashlib, json, mimetypes, os, sqlite3, subprocess, sys, time

HERE=Path(__file__).resolve().parent
SRC=HERE.parent
FULL_ADAM_RUNTIME=SRC/"11_ADAM"/"full_runtime"
if str(FULL_ADAM_RUNTIME) not in sys.path: sys.path.insert(0,str(FULL_ADAM_RUNTIME))
from canonical_full_adam_runtime import EntityFullAdamRuntime

BTDU_VERSION="3.4.2"
BTDU_SCHEMA="blackmore-technology-data-universe-v1"
BTDU_CANONICAL_OWNER_ENTITY_ID="ent2-6eoiiztjyhmyh2tbr5psmofcduwvjledubhoiqwo6mjfoqkn6ica"
BTDU_CANONICAL_OWNER_ALIAS="shawn.blackmore.entity"
BTG_STEWARD_ENTITY_ID="ent2-kkov66eoh23h3zgr4pe4njsbkayn2kxad6vfyirqvuqrty52clpa"
ENTITY_PROTOCOL_ENTITY_ID="ent2-m3nofxtv3zwldhwuonw3h67hqjh2zambrhj4kaaulncpt4amkcua"
GENESIS_PRIMITIVES=("ENTITY","AUTHORITY","RIGHT","EVENT","VALUE")
GENESIS_MARKET_LIFECYCLE=("DCO","INSTRUMENT","LISTING","DISCLOSURE","ORDER_RFQ_AUCTION","PRICE_DISCOVERY","TRADE","CLEARING","SETTLEMENT","ENTITLEMENT","USAGE","DERIVED_OUTPUT","ECONOMIC_CONSEQUENCE")

def canon(v:Any)->bytes: return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def sha256(v:Any)->str: return hashlib.sha256(bytes(v) if isinstance(v,(bytes,bytearray)) else canon(v)).hexdigest()
def now_ms()->int: return int(time.time()*1000)

class BlackmoreTechnologyDataUniverse:
    """ENTITY-governed information substrate built on the existing ADAM runtime.

    ENTITY remains authority/rights/economics. ADAM remains the atom/bond state engine.
    BTDU adds governed information topology and derived query indexes. NIKI receives only
    bounded projections. Mirrored lineage never creates ownership or entitlement itself.
    """
    def __init__(self,state_dir:str|Path,*,authorization_verifier:Callable[[Mapping[str,Any]],bool],sovereign_entity_id:str,protocol_entity_id:str=ENTITY_PROTOCOL_ENTITY_ID,steward_entity_id:str=BTG_STEWARD_ENTITY_ID,enable_network_reference:bool=False):
        if authorization_verifier is None: raise ValueError("ENTITY authorization verifier is required")
        if not str(sovereign_entity_id).startswith(("ent1-","ent2-")): raise ValueError("sovereign Entity ID required")
        self.root=Path(state_dir); self.root.mkdir(parents=True,exist_ok=True)
        self.authorization_verifier=authorization_verifier; self.sovereign_entity_id=str(sovereign_entity_id); self.protocol_entity_id=str(protocol_entity_id); self.steward_entity_id=str(steward_entity_id)
        self.runtime=EntityFullAdamRuntime(self.root/"adam",authorization_verifier=authorization_verifier,enable_network_reference=enable_network_reference)
        self.atomic=self.runtime.atomic; self.evidence=self.runtime.evidence; self.db_path=self.root/"btdu_index.sqlite"
        self._init_db(); self._load_adam_extensions(); self._ensure_root()

    def _load_adam_extensions(self):
        from adam_v44.bond_algebra import BondAlgebra,FirstClassBond,HyperBond,HyperRole,BondFamily,ConfidenceClass
        from adam_v42.distributed import SovereignErasureStore
        self.BondAlgebra=BondAlgebra; self.FirstClassBond=FirstClassBond; self.HyperBond=HyperBond; self.HyperRole=HyperRole; self.BondFamily=BondFamily; self.ConfidenceClass=ConfidenceClass; self.SovereignErasureStore=SovereignErasureStore

    def _db(self):
        db=sqlite3.connect(self.db_path); db.row_factory=sqlite3.Row; return db

    def _init_db(self):
        with self._db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS objects(object_ref TEXT PRIMARY KEY,atom_id TEXT NOT NULL UNIQUE,logical_path TEXT NOT NULL,content_sha256 TEXT NOT NULL,size_bytes INTEGER NOT NULL,media_type TEXT NOT NULL,evidence_object_id TEXT NOT NULL,source_entity_id TEXT NOT NULL,controller_entity_id TEXT NOT NULL,rights_holder_entity_id TEXT,provenance_ref TEXT NOT NULL,created_at_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS edges(bond_id TEXT PRIMARY KEY,source_atom_id TEXT NOT NULL,predicate TEXT NOT NULL,target_atom_id TEXT NOT NULL,source_ref TEXT NOT NULL,target_ref TEXT NOT NULL,metadata_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS economic_nodes(node_ref TEXT PRIMARY KEY,atom_id TEXT NOT NULL UNIQUE,node_kind TEXT NOT NULL,metadata_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS economic_edges(edge_id TEXT PRIMARY KEY,source_ref TEXT NOT NULL,predicate TEXT NOT NULL,target_ref TEXT NOT NULL,source_atom_id TEXT NOT NULL,target_atom_id TEXT NOT NULL,bond_id TEXT NOT NULL,evidence_sha256 TEXT,metadata_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS repository_manifests(manifest_id TEXT PRIMARY KEY,repository_path TEXT NOT NULL,git_commit_sha1 TEXT,git_tree_sha1 TEXT,tracked_files INTEGER NOT NULL,aggregate_sha256 TEXT NOT NULL,atomic_root TEXT NOT NULL,manifest_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_btdu_object_sha ON objects(content_sha256);
            CREATE INDEX IF NOT EXISTS idx_btdu_edge_source ON edges(source_ref,predicate);
            CREATE INDEX IF NOT EXISTS idx_btdu_econ_source ON economic_edges(source_ref,predicate);
            ''')

    def _authorize(self,receipt:Mapping[str,Any]):
        if not self.authorization_verifier(dict(receipt)): raise PermissionError("ENTITY authorization verification failed; BTDU mutation denied")
    def _commit(self,ops:list[dict],*,metadata:dict[str,Any]):
        if ops: self.atomic.commit(ops,metadata=metadata,capability=self.runtime._capability)
    def _put_atom(self,kind:str,value:Any,metadata:dict[str,Any]|None=None)->str:
        metadata=dict(metadata or {}); aid=self.atomic.atom_id(kind,value,metadata)
        if aid not in self.atomic.atoms: self._commit([{"op":"put_atom","atom_id":aid,"kind":kind,"value":value,"metadata":metadata}],metadata={"btdu":"put_atom","kind":kind})
        return aid
    def _put_atoms(self,rows:Iterable[tuple[str,Any,dict[str,Any]]],*,reason:str)->list[str]:
        ids=[]; ops=[]
        for kind,value,metadata in rows:
            aid=self.atomic.atom_id(kind,value,metadata); ids.append(aid)
            if aid not in self.atomic.atoms: ops.append({"op":"put_atom","atom_id":aid,"kind":kind,"value":value,"metadata":metadata})
        self._commit(ops,metadata={"btdu":reason,"count":len(ops)}); return ids
    def _bond(self,source_atom_id:str,predicate:str,target_atom_id:str,*,source_ref:str,target_ref:str,context:str,metadata:dict[str,Any])->str:
        bid,op=self.atomic.bond_op(source_atom_id,str(predicate),target_atom_id,context=str(context),metadata=dict(metadata))
        if op: self._commit([op],metadata={"btdu":"bond","predicate":str(predicate)})
        with self._db() as db: db.execute("INSERT OR REPLACE INTO edges VALUES(?,?,?,?,?,?,?)",(bid,source_atom_id,str(predicate),target_atom_id,str(source_ref),str(target_ref),json.dumps(metadata,sort_keys=True)))
        return bid

    def _ensure_root(self):
        root_ref=f"btdu:{self.sovereign_entity_id}"
        rows=[("btdu_root",{"schema":BTDU_SCHEMA,"version":BTDU_VERSION,"root_ref":root_ref,"sovereign_entity_id":self.sovereign_entity_id,"protocol_entity_id":self.protocol_entity_id,"steward_entity_id":self.steward_entity_id},{"authority_model":"ENTITY","state_engine":"ADAM","advisory_reasoner":"NIKI","raw_compression_replacement":False}),
              ("entity_ref",{"entity_id":self.sovereign_entity_id},{"role":"sovereign_authority"}),
              ("entity_ref",{"entity_id":self.protocol_entity_id},{"role":"protocol_origin"}),
              ("entity_ref",{"entity_id":self.steward_entity_id},{"role":"steward"})]
        self.root_atom_id,self.sovereign_atom_id,self.protocol_atom_id,self.steward_atom_id=self._put_atoms(rows,reason="initialize_root")
        boundary={"protocol_origin_is_not_asset_provenance":True,"protocol_origin_does_not_transfer_user_asset_ownership":True,"economic_participation_requires_explicit_terms":True,"automatic_protocol_royalty_bps":0}
        self._bond(self.root_atom_id,"governed_by",self.sovereign_atom_id,source_ref=root_ref,target_ref=self.sovereign_entity_id,context="BTDU_AUTHORITY",metadata=boundary)
        self._bond(self.root_atom_id,"uses_protocol",self.protocol_atom_id,source_ref=root_ref,target_ref=self.protocol_entity_id,context="BTDU_PROTOCOL",metadata=boundary)
        self._bond(self.protocol_atom_id,"stewarded_by",self.steward_atom_id,source_ref=self.protocol_entity_id,target_ref=self.steward_entity_id,context="BTDU_PROTOCOL",metadata=boundary)
        self.install_genesis_contract()

    def install_genesis_contract(self)->dict[str,Any]:
        pids=self._put_atoms([("btdu_genesis_primitive",{"name":n},{"immutable_semantic":True}) for n in GENESIS_PRIMITIVES],reason="genesis_primitives")
        mids=self._put_atoms([("btdu_market_stage",{"name":n},{"genesis_market_semantic":True}) for n in GENESIS_MARKET_LIFECYCLE],reason="genesis_market_lifecycle")
        md={"btdu_is_additive":True,"genesis_semantics_preserved":True,"rights_not_created_by_topology":True,"economic_entitlement_not_created_by_topology":True}
        for aid,n in zip(pids,GENESIS_PRIMITIVES): self._bond(self.root_atom_id,"preserves_genesis_primitive",aid,source_ref=f"btdu:{self.sovereign_entity_id}",target_ref=n,context="BTDU_GENESIS_INVARIANT",metadata=md)
        for i in range(len(mids)-1): self._bond(mids[i],"precedes",mids[i+1],source_ref=GENESIS_MARKET_LIFECYCLE[i],target_ref=GENESIS_MARKET_LIFECYCLE[i+1],context="BTDU_GENESIS_MARKET_LIFECYCLE",metadata=md)
        return {"schema":"entity-btdu-genesis-contract-v1","primitives":list(GENESIS_PRIMITIVES),"market_lifecycle":list(GENESIS_MARKET_LIFECYCLE),"btdu_is_additive":True}

    def materialize_primitive_bytes(self,authorization_receipt:Mapping[str,Any])->dict[str,Any]:
        self._authorize(authorization_receipt)
        ids=self._put_atoms([("byte",i,{"width":8,"btdu_primitive":True}) for i in range(256)],reason="materialize_primitive_bytes")
        return {"schema":"entity-btdu-byte-universe-v1","count":len(ids),"unique":len(set(ids))}

    def encode_exact_bytes(self,name:str,data:bytes,authorization_receipt:Mapping[str,Any],*,chunk_size:int=256)->dict[str,Any]:
        self._authorize(authorization_receipt)
        if chunk_size<16 or chunk_size>4096: raise ValueError("chunk_size must be 16..4096")
        byte_ids=self._put_atoms([("byte",i,{"width":8,"btdu_primitive":True}) for i in range(256)],reason="primitive_bytes")
        chunk_ids=[]; ops=[]
        for offset in range(0,len(data),chunk_size):
            block=data[offset:offset+chunk_size]; members=[{"role":"byte","order":i,"ref":byte_ids[b]} for i,b in enumerate(block)]; meta={"offset":offset,"length":len(block),"sha256":sha256(block)}
            cid=self.atomic.compound_id("BTDU_BYTE_CHUNK",members,meta); chunk_ids.append(cid)
            if cid not in self.atomic.compounds: ops.append({"op":"put_compound","compound_id":cid,"kind":"BTDU_BYTE_CHUNK","members":members,"metadata":meta})
            if len(ops)>=128: self._commit(ops,metadata={"btdu":"byte_chunks","name":str(name)}); ops=[]
        self._commit(ops,metadata={"btdu":"byte_chunks","name":str(name)})
        root_members=[{"role":"chunk","order":i,"ref":ref} for i,ref in enumerate(chunk_ids)]; root_meta={"name":str(name),"size_bytes":len(data),"sha256":sha256(data),"encoding":"raw-bytes"}
        root_id=self.atomic.compound_id("BTDU_EXACT_OBJECT",root_members,root_meta)
        if root_id not in self.atomic.compounds: self._commit([{"op":"put_compound","compound_id":root_id,"kind":"BTDU_EXACT_OBJECT","members":root_members,"metadata":root_meta}],metadata={"btdu":"exact_object","name":str(name)})
        return {"schema":"entity-btdu-exact-byte-object-v1","compound_id":root_id,"size_bytes":len(data),"sha256":sha256(data),"chunks":len(chunk_ids)}

    def reconstruct_exact_bytes(self,compound_id:str)->bytes:
        def walk(ref:str)->bytes:
            if ref in self.atomic.atoms:
                atom=self.atomic.atoms[ref]
                if atom.kind!="byte": raise ValueError("non-byte atom in exact byte compound")
                return bytes([int(atom.value)])
            comp=self.atomic.compounds.get(ref)
            if comp is None: raise KeyError(ref)
            return b"".join(walk(m["ref"]) for m in sorted(comp.members,key=lambda x:x["order"]))
        return walk(str(compound_id))

    def ingest_bytes(self,*,logical_path:str,data:bytes,authorization_receipt:Mapping[str,Any],source_entity_id:str,controller_entity_id:str,rights_holder_entity_id:str|None=None,provenance_ref:str,media_type:str="application/octet-stream")->dict[str,Any]:
        self._authorize(authorization_receipt); raw=bytes(data); content_sha=sha256(raw)
        exact=self.evidence.ingest_evidence(raw,media_type=str(media_type),name=Path(str(logical_path)).name or "btdu-object")
        encoded=self.encode_exact_bytes(str(logical_path),raw,authorization_receipt,chunk_size=4096)
        object_ref="btdu-object:"+sha256({"logical_path":str(logical_path).replace("\\","/"),"content_sha256":content_sha,"source_entity_id":str(source_entity_id)})
        value={"schema":"entity-btdu-object-v1","object_ref":object_ref,"logical_path":str(logical_path).replace("\\","/"),"content_sha256":content_sha,"size_bytes":len(raw),"evidence_object_id":exact.object_id,"exact_compound_id":encoded["compound_id"],"media_type":str(media_type)}
        object_atom=self._put_atom("btdu_object",value,{"exact_content_externalized":True})
        refs=[("source",source_entity_id,"data_origin"),("controller",controller_entity_id,"data_controller")]
        if rights_holder_entity_id: refs.append(("rights_holder",rights_holder_entity_id,"rights_holder"))
        ref_ids=self._put_atoms([("entity_ref",{"entity_id":str(eid)},{"role":role}) for _,eid,role in refs],reason="object_entity_refs")
        evidence_atom=self._put_atom("evidence_ref",{"object_id":exact.object_id,"sha256":content_sha},{"media_type":str(media_type)})
        provenance_atom=self._put_atom("provenance_ref",{"ref":str(provenance_ref)},{"source_entity_id":str(source_entity_id)})
        boundary={"protocol_origin_is_not_asset_provenance":True,"topology_does_not_create_ownership":True,"topology_does_not_create_economic_entitlement":True}
        self._bond(object_atom,"contained_in",self.root_atom_id,source_ref=object_ref,target_ref=f"btdu:{self.sovereign_entity_id}",context="BTDU_MEMBERSHIP",metadata=boundary)
        self._bond(object_atom,"represented_by_evidence",evidence_atom,source_ref=object_ref,target_ref=exact.object_id,context="BTDU_EVIDENCE",metadata={"sha256":content_sha})
        self._bond(object_atom,"atomized_as",encoded["compound_id"],source_ref=object_ref,target_ref=encoded["compound_id"],context="BTDU_EXACT_ATOMIZATION",metadata={"sha256":content_sha,"primitive":"byte","recursive_compounds":True})
        self._bond(object_atom,"provenance_recorded_as",provenance_atom,source_ref=object_ref,target_ref=str(provenance_ref),context="BTDU_PROVENANCE",metadata={"source_entity_id":str(source_entity_id)})
        for (label,eid,role),atom_id in zip(refs,ref_ids):
            predicate={"source":"sourced_from","controller":"controlled_by","rights_holder":"rights_asserted_by"}[label]
            md=dict(boundary,role=role,assertion_explicit=(label=="rights_holder"))
            self._bond(object_atom,predicate,atom_id,source_ref=object_ref,target_ref=str(eid),context="BTDU_PROVENANCE_RIGHTS",metadata=md)
        with self._db() as db:
            db.execute('''INSERT OR REPLACE INTO objects(object_ref,atom_id,logical_path,content_sha256,size_bytes,media_type,evidence_object_id,source_entity_id,controller_entity_id,rights_holder_entity_id,provenance_ref,created_at_ms) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(object_ref,object_atom,value["logical_path"],content_sha,len(raw),str(media_type),exact.object_id,str(source_entity_id),str(controller_entity_id),str(rights_holder_entity_id) if rights_holder_entity_id else None,str(provenance_ref),now_ms()))
        return dict(value,atom_id=object_atom,source_entity_id=str(source_entity_id),controller_entity_id=str(controller_entity_id),rights_holder_entity_id=str(rights_holder_entity_id) if rights_holder_entity_id else None,provenance_ref=str(provenance_ref))

    def ingest_file(self,path:str|Path,authorization_receipt:Mapping[str,Any],**kwargs:Any)->dict[str,Any]:
        p=Path(path)
        if not p.is_file(): raise FileNotFoundError(str(p))
        media=kwargs.pop("media_type",None) or mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        return self.ingest_bytes(logical_path=kwargs.pop("logical_path",p.name),data=p.read_bytes(),authorization_receipt=authorization_receipt,media_type=media,**kwargs)

    @staticmethod
    def _git(repo:Path,*args:str)->str:
        return subprocess.check_output([os.environ.get("ENTITY_GIT_BIN","git"),"-C",str(repo),*args],stderr=subprocess.STDOUT).decode("utf-8","replace").strip()

    def ingest_repository(self,repo_path:str|Path,authorization_receipt:Mapping[str,Any],*,source_entity_id:str,controller_entity_id:str,rights_holder_entity_id:str|None,provenance_ref:str)->dict[str,Any]:
        self._authorize(authorization_receipt); repo=Path(repo_path).resolve(); raw=subprocess.check_output([os.environ.get("ENTITY_GIT_BIN","git"),"-C",str(repo),"ls-files","-z"]); tracked=[x.decode("utf-8","surrogateescape") for x in raw.split(b"\0") if x]
        commit=self._git(repo,"rev-parse","HEAD"); tree=self._git(repo,"rev-parse","HEAD^{tree}"); objects=[]
        for rel in tracked:
            p=repo/rel
            if not p.is_file(): continue
            objects.append(self.ingest_file(p,authorization_receipt,logical_path=rel,source_entity_id=source_entity_id,controller_entity_id=controller_entity_id,rights_holder_entity_id=rights_holder_entity_id,provenance_ref=f"{provenance_ref}@{commit}:{rel}"))
        aggregate=sha256([(o["logical_path"],o["content_sha256"],o["object_ref"]) for o in objects])
        manifest={"schema":"entity-btdu-repository-ingest-v1","btdu_version":BTDU_VERSION,"repository_path":str(repo),"git_commit_sha1":commit,"git_tree_sha1":tree,"tracked_files":len(objects),"aggregate_sha256":aggregate,"atomic_root":self.atomic.root_hash,"sovereign_entity_id":self.sovereign_entity_id,"source_entity_id":str(source_entity_id),"controller_entity_id":str(controller_entity_id),"rights_holder_entity_id":str(rights_holder_entity_id) if rights_holder_entity_id else None,"protocol_origin_is_separate":True,"economic_rights_not_created_by_ingest":True}
        manifest_id="btdu-repo:"+sha256(manifest); manifest["manifest_id"]=manifest_id
        with self._db() as db: db.execute("INSERT OR REPLACE INTO repository_manifests VALUES(?,?,?,?,?,?,?,?,?)",(manifest_id,str(repo),commit,tree,len(objects),aggregate,self.atomic.root_hash,json.dumps(manifest,sort_keys=True),now_ms()))
        ma=self._put_atom("btdu_repository_manifest",manifest,{"authority_root":self.sovereign_entity_id})
        self._bond(ma,"contained_in",self.root_atom_id,source_ref=manifest_id,target_ref=f"btdu:{self.sovereign_entity_id}",context="BTDU_REPOSITORY",metadata={"economic_rights_not_created_by_ingest":True})
        return manifest

    def mirror_economic_lineage(self,*,nodes:list[dict[str,Any]],edges:list[dict[str,Any]],authorization_receipt:Mapping[str,Any],evidence_sha256:str|None=None)->dict[str,Any]:
        self._authorize(authorization_receipt); node_map={}
        for node in nodes:
            ref=str(node["ref"]); kind=str(node["kind"]).upper(); md=dict(node.get("metadata") or {})
            aid=self._put_atom("btdu_economic_ref",{"ref":ref,"kind":kind},{"mirror_only":True,"economic_authority":"ENTITY"}); node_map[ref]=aid
            with self._db() as db: db.execute("INSERT OR REPLACE INTO economic_nodes VALUES(?,?,?,?)",(ref,aid,kind,json.dumps(md,sort_keys=True)))
        mirrored=[]
        for edge in edges:
            s,p,t=str(edge["source"]),str(edge["predicate"]),str(edge["target"])
            if s not in node_map or t not in node_map: raise KeyError("economic edge references unknown node")
            md=dict(edge.get("metadata") or {}); md.update({"mirror_only":True,"creates_rights":False,"creates_ownership":False,"creates_economic_entitlement":False,"economic_effects_require_entity_economy":True,"protocol_tax_bps":0})
            bid=self._bond(node_map[s],p,node_map[t],source_ref=s,target_ref=t,context="BTDU_ECONOMIC_LINEAGE",metadata=md)
            edge_id="btdu-econ:"+sha256({"s":s,"p":p,"t":t,"evidence_sha256":evidence_sha256,"metadata":md})
            with self._db() as db: db.execute("INSERT OR REPLACE INTO economic_edges VALUES(?,?,?,?,?,?,?,?,?)",(edge_id,s,p,t,node_map[s],node_map[t],bid,str(evidence_sha256) if evidence_sha256 else None,json.dumps(md,sort_keys=True)))
            mirrored.append({"edge_id":edge_id,"source":s,"predicate":p,"target":t,"bond_id":bid})
        lineage_root=sha256({"nodes":sorted((str(n["ref"]),str(n["kind"]).upper()) for n in nodes),"edges":sorted((x["source"],x["predicate"],x["target"]) for x in mirrored),"evidence_sha256":evidence_sha256})
        return {"schema":"entity-btdu-economic-lineage-mirror-v1","nodes":len(nodes),"edges":len(mirrored),"lineage_root":lineage_root,"atomic_root":self.atomic.root_hash,"mirror_only":True,"rights_created":False,"economic_entitlements_created":False,"protocol_tax_bps":0}

    def mirror_genesis_market_chain(self,authorization_receipt:Mapping[str,Any],*,prefix:str="genesis",evidence_sha256:str|None=None)->dict[str,Any]:
        nodes=[{"ref":f"{prefix}:{n.lower()}","kind":n} for n in GENESIS_MARKET_LIFECYCLE]
        edges=[{"source":nodes[i]["ref"],"predicate":"precedes","target":nodes[i+1]["ref"],"metadata":{"genesis_market_semantics":True}} for i in range(len(nodes)-1)]
        return self.mirror_economic_lineage(nodes=nodes,edges=edges,authorization_receipt=authorization_receipt,evidence_sha256=evidence_sha256)

    def passport_binding(self,object_ref:str)->dict[str,Any]:
        with self._db() as db:
            row=db.execute("SELECT object_ref,atom_id,content_sha256,controller_entity_id,source_entity_id,rights_holder_entity_id FROM objects WHERE object_ref=?",(str(object_ref),)).fetchone()
        if not row: raise KeyError(object_ref)
        return {"schema":"entity-btdu-passport-binding-v1","btdu_version":BTDU_VERSION,
                "universe_root":self.atomic.root_hash,"object_ref":row["object_ref"],"object_atom_id":row["atom_id"],
                "content_sha256":row["content_sha256"],"sovereign_entity_id":self.sovereign_entity_id,
                "controller_entity_id":row["controller_entity_id"],"source_entity_id":row["source_entity_id"],
                "rights_holder_entity_id":row["rights_holder_entity_id"],"protocol_origin_is_not_asset_provenance":True,
                "topology_does_not_create_ownership":True,"topology_does_not_create_economic_entitlement":True,
                "automatic_protocol_royalty_bps":0}

    def project_object_context(self,object_ref:str)->dict[str,Any]:
        with self._db() as db:
            obj=db.execute("SELECT * FROM objects WHERE object_ref=?",(str(object_ref),)).fetchone()
            if not obj: raise KeyError(object_ref)
            edges=db.execute("SELECT predicate,target_ref,metadata_json FROM edges WHERE source_ref=? ORDER BY predicate,target_ref",(str(object_ref),)).fetchall()
        lines=[f"{object_ref} {row['predicate']} {row['target_ref']}" for row in edges]
        return {"schema":"niki-btdu-context-v1","object_ref":str(object_ref),"content_sha256":obj["content_sha256"],"size_bytes":int(obj["size_bytes"]),"context":"\n".join(lines),"raw_content_included":False,"authority_transferred_to_niki":False,"execution_authority":"ENTITY","state_engine":"ADAM"}

    def reconstruct_object(self,object_ref:str)->bytes:
        with self._db() as db: row=db.execute("SELECT evidence_object_id,content_sha256 FROM objects WHERE object_ref=?",(str(object_ref),)).fetchone()
        if not row: raise KeyError(object_ref)
        raw=self.evidence.exact.reconstruct(row["evidence_object_id"])
        if sha256(raw)!=row["content_sha256"]: raise RuntimeError("BTDU exact evidence reconstruction hash mismatch")
        return raw

    def list_objects(self)->list[dict[str,Any]]:
        with self._db() as db: rows=db.execute("SELECT * FROM objects ORDER BY logical_path,object_ref").fetchall()
        return [dict(r) for r in rows]

    def repository_manifests(self)->list[dict[str,Any]]:
        with self._db() as db: rows=db.execute("SELECT manifest_json FROM repository_manifests ORDER BY created_at_ms,manifest_id").fetchall()
        return [json.loads(r["manifest_json"]) for r in rows]

    def verify(self,*,deep:bool=True)->dict[str,Any]:
        atomic=self.runtime.verify(); problems=[]; objects=self.list_objects()
        if deep:
            for row in objects:
                try:
                    raw=self.evidence.exact.reconstruct(row["evidence_object_id"])
                    if sha256(raw)!=row["content_sha256"]: problems.append("hash:"+row["object_ref"])
                    with self._db() as db: atomized=db.execute("SELECT target_ref FROM edges WHERE source_ref=? AND predicate='atomized_as'",(row["object_ref"],)).fetchone()
                    if not atomized or sha256(self.reconstruct_exact_bytes(atomized["target_ref"]))!=row["content_sha256"]: problems.append("atomization:"+row["object_ref"])
                except Exception: problems.append("reconstruct:"+row["object_ref"])
        primitive_targets=set(GENESIS_PRIMITIVES)
        with self._db() as db:
            present={r["target_ref"] for r in db.execute("SELECT target_ref FROM edges WHERE predicate='preserves_genesis_primitive'").fetchall()}
            econ_edges=[dict(r) for r in db.execute("SELECT * FROM economic_edges").fetchall()]
        if not primitive_targets.issubset(present): problems.append("genesis_primitives")
        return {"schema":"entity-btdu-verification-v1","btdu_version":BTDU_VERSION,"pass":bool(atomic.get("pass")) and not problems,"atomic":atomic,"atomic_root":self.atomic.root_hash,"sovereign_entity_id":self.sovereign_entity_id,"protocol_entity_id":self.protocol_entity_id,"objects":len(objects),"economic_lineage_edges":len(econ_edges),"genesis_primitives_preserved":primitive_targets.issubset(present),"protocol_origin_is_not_asset_provenance":True,"automatic_protocol_royalty_bps":0,"problems":problems}

    def close(self): self.runtime.close()
    def __enter__(self): return self
    def __exit__(self,exc_type,exc,tb): self.close()
