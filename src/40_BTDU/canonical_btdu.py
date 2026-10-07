from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Iterable
from contextlib import contextmanager
import gc, hashlib, json, mimetypes, os, sqlite3, subprocess, sys, time, threading

HERE=Path(__file__).resolve().parent
SRC=HERE.parent
if str(HERE) not in sys.path: sys.path.insert(0,str(HERE))
from storage_kernel import BTDUStorageKernel, STORAGE_VERSION as BTDU_STORAGE_VERSION, STORAGE_SCHEMA as BTDU_STORAGE_SCHEMA
from formula_kernel import BTDUFormulaKernel, FORMULA_VERSION as BTDU_FORMULA_VERSION, FORMULA_SCHEMA as BTDU_FORMULA_SCHEMA
FULL_ADAM_RUNTIME=SRC/"11_ADAM"/"full_runtime"
if str(FULL_ADAM_RUNTIME) not in sys.path: sys.path.insert(0,str(FULL_ADAM_RUNTIME))
from canonical_full_adam_runtime import EntityFullAdamRuntime

BTDU_VERSION="3.4.2"
BTDU_SCHEMA="blackmore-technology-data-universe-v1"
BTDU_BUILD_REVISION="v3.4.3+btdu-reconstructive-formula.one-authoritative-payload.20261004"
BTDU_CANONICAL_OWNER_ENTITY_ID="ent2-6eoiiztjyhmyh2tbr5psmofcduwvjledubhoiqwo6mjfoqkn6ica"
BTDU_CANONICAL_OWNER_ALIAS="shawn.blackmore.entity"
BTG_STEWARD_ENTITY_ID="ent2-kkov66eoh23h3zgr4pe4njsbkayn2kxad6vfyirqvuqrty52clpa"
ENTITY_PROTOCOL_ENTITY_ID="ent2-m3nofxtv3zwldhwuonw3h67hqjh2zambrhj4kaaulncpt4amkcua"
GENESIS_PRIMITIVES=("ENTITY","AUTHORITY","RIGHT","EVENT","VALUE")
GENESIS_MARKET_LIFECYCLE=("DCO","INSTRUMENT","LISTING","DISCLOSURE","ORDER_RFQ_AUCTION","PRICE_DISCOVERY","TRADE","CLEARING","SETTLEMENT","ENTITLEMENT","USAGE","DERIVED_OUTPUT","ECONOMIC_CONSEQUENCE")

def canon(v:Any)->bytes: return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def sha256(v:Any)->str: return hashlib.sha256(bytes(v) if isinstance(v,(bytes,bytearray)) else canon(v)).hexdigest()
def now_ms()->int: return int(time.time()*1000)

CROSS_DOMAIN_BRIDGE_SPECS=(
    ("addition",("add","addition"),"+"),
    ("subtraction",("subtract",),"-"),
    ("multiplication",("multiply",),"*"),
    ("division",("divide",),"/"),
    ("equality",("equal",),"="),
    ("less_than",("less",),"<"),
    ("greater_than",("greater",),">"),
)

def install_cross_domain_bridge_index(db:sqlite3.Connection,authorization_record:Mapping[str,Any]|None=None)->dict[str,Any]:
    """Build the governed cross-domain bridge as a rebuildable derived SQLite index.

    This deliberately does not mutate the signed ADAM journal. The source English,
    mathematical orientation and code records remain the provenance-bearing records;
    the bridge stores deterministic references plus the signed/verified authorization
    receipt supplied by the caller.
    """
    db.row_factory=sqlite3.Row
    db.execute("PRAGMA busy_timeout=30000")
    tables={r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required={"english_lemmas","language_nodes","language_relations","orientation_occurrences"}
    if not required.issubset(tables):
        raise RuntimeError("cross-domain bridge requires ingested English, code and mathematics/orientation tables")
    expected=["concept_ref","math_operator","code_token_ref","english_refs_json","metadata_json","bridge_hash"]
    existing=[r["name"] for r in db.execute("PRAGMA table_info(semantic_bridges)")] if "semantic_bridges" in tables else []
    if existing and existing!=expected:
        db.execute("DROP TABLE semantic_bridges")
    db.execute("""CREATE TABLE IF NOT EXISTS semantic_bridges(
        concept_ref TEXT PRIMARY KEY,math_operator TEXT NOT NULL,code_token_ref TEXT NOT NULL,
        english_refs_json TEXT NOT NULL,metadata_json TEXT NOT NULL,bridge_hash TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS semantic_bridge_manifests(
        manifest_id TEXT PRIMARY KEY,manifest_json TEXT NOT NULL,authorization_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_language_relation_bridge ON language_relations(predicate,source_ref,target_ref)")
    # Rebuild only the derived bridge predicates; all source corpus relations are preserved.
    db.execute("DELETE FROM language_relations WHERE predicate IN ('maps_to_math_semantic','realized_as_code_token')")
    db.execute("DELETE FROM semantic_bridges")
    relations=[]; installed=[]
    boundary={"governed_semantic_bridge":True,"derived_index":True,"rights_created":False,
              "ownership_created":False,"economic_entitlement_created":False,
              "source_provenance_preserved":True,"signed_adam_journal_mutated":False}
    for concept,lemmas,operator in CROSS_DOMAIN_BRIDGE_SPECS:
        concept_ref="math-semantic:"+concept
        code_ref="code-token:"+operator
        op_count=int(db.execute("SELECT count(*) FROM orientation_occurrences WHERE original_operator=?",(operator,)).fetchone()[0])
        code=db.execute("SELECT node_ref FROM language_nodes WHERE node_kind='code_token' AND value_text=? ORDER BY node_ref LIMIT 1",(operator,)).fetchone()
        q="SELECT lemma_ref,lemma,pos FROM english_lemmas WHERE lower(lemma) IN ("+",".join("?" for _ in lemmas)+") ORDER BY lemma_ref"
        erows=db.execute(q,tuple(x.lower() for x in lemmas)).fetchall()
        if op_count<=0 or code is None or not erows: continue
        english_refs=[str(r["lemma_ref"]) for r in erows]
        md=dict(boundary,bridge_concept=concept,math_operator_occurrences=op_count)
        bridge_hash=sha256({"schema":"entity-btdu-cross-domain-concept-v1","concept_ref":concept_ref,
                            "math_operator":operator,"code_token_ref":str(code["node_ref"]),"english_refs":english_refs})
        db.execute("INSERT OR REPLACE INTO semantic_bridges VALUES(?,?,?,?,?,?)",
            (concept_ref,operator,str(code["node_ref"]),json.dumps(english_refs,sort_keys=True),json.dumps(md,sort_keys=True),bridge_hash))
        for erow in erows:
            rmd=dict(md,source_lemma=str(erow["lemma"]),source_pos=str(erow["pos"]))
            rr="bridge-rel:"+sha256({"s":str(erow["lemma_ref"]),"p":"maps_to_math_semantic","t":concept_ref})
            db.execute("INSERT OR REPLACE INTO language_relations VALUES(?,?,?,?,?,?)",
                (rr,str(erow["lemma_ref"]),"maps_to_math_semantic",concept_ref,None,json.dumps(rmd,sort_keys=True)))
            relations.append((str(erow["lemma_ref"]),"maps_to_math_semantic",concept_ref))
        rr="bridge-rel:"+sha256({"s":concept_ref,"p":"realized_as_code_token","t":str(code["node_ref"])})
        db.execute("INSERT OR REPLACE INTO language_relations VALUES(?,?,?,?,?,?)",
            (rr,concept_ref,"realized_as_code_token",str(code["node_ref"]),None,json.dumps(md,sort_keys=True)))
        relations.append((concept_ref,"realized_as_code_token",str(code["node_ref"])))
        installed.append({"concept":concept,"concept_ref":concept_ref,"math_operator":operator,
                          "code_token_ref":str(code["node_ref"]),"english_refs":english_refs,
                          "math_operator_occurrences":op_count,"bridge_hash":bridge_hash})
    root=sha256({"schema":"entity-btdu-cross-domain-bridge-root-v1","relations":sorted(relations)})
    manifest={"schema":"entity-btdu-cross-domain-bridge-install-v2","build_revision":BTDU_BUILD_REVISION,
              "concepts":len(installed),"relations":len(relations),"bridge_root":root,"installed":installed,
              **boundary}
    manifest_id="bridge-manifest:"+sha256(manifest)
    db.execute("INSERT OR REPLACE INTO semantic_bridge_manifests VALUES(?,?,?,?)",
        (manifest_id,json.dumps(manifest,sort_keys=True),json.dumps(dict(authorization_record or {}),sort_keys=True),now_ms()))
    return dict(manifest,manifest_id=manifest_id)

class BlackmoreTechnologyDataUniverse:
    """ENTITY-governed information substrate built on the existing ADAM runtime.

    ENTITY remains authority/rights/economics. ADAM remains the atom/bond state engine.
    BTDU adds governed information topology and derived query indexes. NIKI receives only
    bounded projections. Mirrored lineage never creates ownership or entitlement itself.
    """
    def __init__(self,state_dir:str|Path,*,authorization_verifier:Callable[[Mapping[str,Any]],bool],sovereign_entity_id:str,protocol_entity_id:str=ENTITY_PROTOCOL_ENTITY_ID,steward_entity_id:str=BTG_STEWARD_ENTITY_ID,enable_network_reference:bool=False,storage_encryption_key:bytes|None=None):
        if authorization_verifier is None: raise ValueError("ENTITY authorization verifier is required")
        if not str(sovereign_entity_id).startswith(("ent1-","ent2-")): raise ValueError("sovereign Entity ID required")
        self.root=Path(state_dir); self.root.mkdir(parents=True,exist_ok=True)
        self._write_lock=threading.RLock()
        self.authorization_verifier=authorization_verifier; self.sovereign_entity_id=str(sovereign_entity_id); self.protocol_entity_id=str(protocol_entity_id); self.steward_entity_id=str(steward_entity_id)
        if storage_encryption_key is None:
            raw_key=os.environ.get("BTDU_STORAGE_MASTER_KEY_HEX")
            if raw_key:
                storage_encryption_key=bytes.fromhex(raw_key)
        self.storage=BTDUStorageKernel(self.root/"storage",encryption_key=storage_encryption_key)
        self.formulas=BTDUFormulaKernel(self.root/"formula",reservoir=self.storage,encryption_key=storage_encryption_key)
        self.runtime=EntityFullAdamRuntime(self.root/"adam",authorization_verifier=authorization_verifier,enable_network_reference=enable_network_reference)
        self.atomic=self.runtime.atomic; self.evidence=self.runtime.evidence; self.db_path=self.root/"btdu_index.sqlite"
        self._init_db(); self._load_adam_extensions(); self._load_orientation_layer(); self._ensure_root()

    def _load_adam_extensions(self):
        from adam_v44.bond_algebra import BondAlgebra,FirstClassBond,HyperBond,HyperRole,BondFamily,ConfidenceClass
        from adam_v42.distributed import SovereignErasureStore
        self.BondAlgebra=BondAlgebra; self.FirstClassBond=FirstClassBond; self.HyperBond=HyperBond; self.HyperRole=HyperRole; self.BondFamily=BondFamily; self.ConfidenceClass=ConfidenceClass; self.SovereignErasureStore=SovereignErasureStore

    def _load_orientation_layer(self):
        import importlib.util
        path=HERE/"orientation_topology.py"
        spec=importlib.util.spec_from_file_location("entity_btdu_orientation_topology",path)
        mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
        self.orientation=mod.BTDUOrientationLayer(self)

    @contextmanager
    def _db(self):
        db=sqlite3.connect(self.db_path,timeout=30.0); db.row_factory=sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        try:
            with db:
                yield db
        finally:
            db.close()

    def _init_db(self):
        with self._db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")
            db.executescript('''
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS objects(object_ref TEXT PRIMARY KEY,atom_id TEXT NOT NULL UNIQUE,logical_path TEXT NOT NULL,content_sha256 TEXT NOT NULL,size_bytes INTEGER NOT NULL,media_type TEXT NOT NULL,evidence_object_id TEXT NOT NULL,source_entity_id TEXT NOT NULL,controller_entity_id TEXT NOT NULL,rights_holder_entity_id TEXT,provenance_ref TEXT NOT NULL,created_at_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS edges(bond_id TEXT PRIMARY KEY,source_atom_id TEXT NOT NULL,predicate TEXT NOT NULL,target_atom_id TEXT NOT NULL,source_ref TEXT NOT NULL,target_ref TEXT NOT NULL,metadata_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS economic_nodes(node_ref TEXT PRIMARY KEY,atom_id TEXT NOT NULL UNIQUE,node_kind TEXT NOT NULL,metadata_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS economic_edges(edge_id TEXT PRIMARY KEY,source_ref TEXT NOT NULL,predicate TEXT NOT NULL,target_ref TEXT NOT NULL,source_atom_id TEXT NOT NULL,target_atom_id TEXT NOT NULL,bond_id TEXT NOT NULL,evidence_sha256 TEXT,metadata_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS repository_manifests(manifest_id TEXT PRIMARY KEY,repository_path TEXT NOT NULL,git_commit_sha1 TEXT,git_tree_sha1 TEXT,tracked_files INTEGER NOT NULL,aggregate_sha256 TEXT NOT NULL,atomic_root TEXT NOT NULL,manifest_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS object_payloads(object_ref TEXT PRIMARY KEY,storage_object_id TEXT NOT NULL,manifest_sha256 TEXT NOT NULL,merkle_root TEXT NOT NULL,chunk_count INTEGER NOT NULL,authoritative INTEGER NOT NULL DEFAULT 1,migrated_from_legacy INTEGER NOT NULL DEFAULT 0,bound_at_ms INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_object_payload_storage ON object_payloads(storage_object_id);
            CREATE TABLE IF NOT EXISTS object_formulas(object_ref TEXT PRIMARY KEY,formula_object_id TEXT NOT NULL,formula_sha256 TEXT NOT NULL,root_node_id TEXT NOT NULL,authoritative INTEGER NOT NULL DEFAULT 1,migrated_from_legacy INTEGER NOT NULL DEFAULT 0,bound_at_ms INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_object_formula_id ON object_formulas(formula_object_id);
            CREATE TABLE IF NOT EXISTS language_nodes(node_ref TEXT PRIMARY KEY,atom_id TEXT NOT NULL,node_kind TEXT NOT NULL,language TEXT,value_text TEXT,metadata_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS language_relations(relation_ref TEXT PRIMARY KEY,source_ref TEXT NOT NULL,predicate TEXT NOT NULL,target_ref TEXT NOT NULL,bond_id TEXT,metadata_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS english_lemmas(lemma_ref TEXT PRIMARY KEY,atom_id TEXT NOT NULL,lemma TEXT NOT NULL,pos TEXT NOT NULL,synset_count INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS semantic_bridges(concept_ref TEXT PRIMARY KEY,math_operator TEXT NOT NULL,code_token_ref TEXT NOT NULL,english_refs_json TEXT NOT NULL,metadata_json TEXT NOT NULL,bridge_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS semantic_bridge_manifests(manifest_id TEXT PRIMARY KEY,manifest_json TEXT NOT NULL,authorization_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS primitive_byte_atoms(
              byte_value INTEGER PRIMARY KEY CHECK(byte_value>=0 AND byte_value<=255),
              atom_id TEXT NOT NULL UNIQUE,
              atom_sha256 TEXT NOT NULL UNIQUE,
              installed_at_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS directory_assets(
              asset_ref TEXT PRIMARY KEY,atom_id TEXT NOT NULL UNIQUE,
              owner_lineage TEXT NOT NULL,owner_entity_id TEXT NOT NULL,
              controller_entity_id TEXT NOT NULL,tree_sha256 TEXT NOT NULL,
              metadata_sha256 TEXT NOT NULL,formula_sha256 TEXT NOT NULL,
              entropy_storage_root TEXT NOT NULL,source_bytes INTEGER NOT NULL,
              file_count INTEGER NOT NULL,descriptor_json TEXT NOT NULL,
              registered_at_ms INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_directory_assets_lineage ON directory_assets(owner_lineage,owner_entity_id);
            CREATE INDEX IF NOT EXISTS idx_language_relation_bridge ON language_relations(predicate,source_ref,target_ref);
            CREATE INDEX IF NOT EXISTS idx_btdu_object_sha ON objects(content_sha256);
            CREATE INDEX IF NOT EXISTS idx_btdu_edge_source ON edges(source_ref,predicate);
            CREATE INDEX IF NOT EXISTS idx_btdu_econ_source ON economic_edges(source_ref,predicate);
            ''')

    def _authorize(self,receipt:Mapping[str,Any]):
        if not self.authorization_verifier(dict(receipt)): raise PermissionError("ENTITY authorization verification failed; BTDU mutation denied")
    def _commit(self,ops:list[dict],*,metadata:dict[str,Any]):
        if not ops: return
        with self._write_lock:
            self.atomic.commit(ops,metadata=metadata,capability=self.runtime._capability)
    def _put_atom(self,kind:str,value:Any,metadata:dict[str,Any]|None=None)->str:
        with self._write_lock:
            metadata=dict(metadata or {}); aid=self.atomic.atom_id(kind,value,metadata)
            if aid not in self.atomic.atoms: self._commit([{"op":"put_atom","atom_id":aid,"kind":kind,"value":value,"metadata":metadata}],metadata={"btdu":"put_atom","kind":kind})
            return aid
    def _put_atoms(self,rows:Iterable[tuple[str,Any,dict[str,Any]]],*,reason:str)->list[str]:
        with self._write_lock:
            ids=[]; ops=[]
            for kind,value,metadata in rows:
                aid=self.atomic.atom_id(kind,value,metadata); ids.append(aid)
                if aid not in self.atomic.atoms: ops.append({"op":"put_atom","atom_id":aid,"kind":kind,"value":value,"metadata":metadata})
            self._commit(ops,metadata={"btdu":reason,"count":len(ops)}); return ids
    def install_primitive_byte_atom_universe(self,authorization_receipt:Mapping[str,Any])->dict[str,Any]:
        """Install the 256 exact computing-byte atoms into canonical BTDU/ADAM state.

        These atoms are universal infrastructure, not asset payload. Asset recipes may
        reference them or higher-level compounds built from them, while conventional
        files remain temporary materializations only.
        """
        self._authorize(authorization_receipt)
        specs=[]
        for value in range(256):
            # Preserve the original BTDU primitive identity established by the
            # production universe: kind='byte', value=0..255, fixed metadata.
            # This reproduces the exact same content-addressed atom IDs in a
            # successor universe rather than creating a parallel primitive set.
            atom_value=value
            metadata={"btdu_primitive":True,"width":8}
            specs.append(("byte",atom_value,metadata))
        atom_ids=self._put_atoms(specs,reason="install_primitive_byte_atom_universe")
        rows=[]
        for value,atom_id in enumerate(atom_ids):
            atom_sha=sha256({"kind":"byte","value":value,"metadata":{"btdu_primitive":True,"width":8}})
            rows.append((value,atom_id,atom_sha,now_ms()))
        with self._db() as db:
            db.executemany("INSERT OR REPLACE INTO primitive_byte_atoms(byte_value,atom_id,atom_sha256,installed_at_ms) VALUES(?,?,?,?)",rows)
        root=sha256({"schema":"entity-btdu-primitive-byte-universe-root-v1",
                     "atoms":[[value,atom_id] for value,atom_id in enumerate(atom_ids)]})
        return {"schema":"entity-btdu-primitive-byte-universe-install-v1","pass":len(atom_ids)==256,
                "count":len(atom_ids),"root":root,"atom_ids":atom_ids,
                "conventional_payload_required":False}

    def primitive_byte_atom_summary(self)->dict[str,Any]:
        with self._db() as db:
            rows=[dict(r) for r in db.execute("SELECT byte_value,atom_id,atom_sha256 FROM primitive_byte_atoms ORDER BY byte_value")]
        return {"schema":"entity-btdu-primitive-byte-universe-summary-v1",
                "installed":len(rows)==256,"count":len(rows),
                "root":sha256({"schema":"entity-btdu-primitive-byte-universe-root-v1",
                               "atoms":[[int(r["byte_value"]),str(r["atom_id"])] for r in rows]}) if rows else None}

    def canonical_formula_basis(self)->dict[str,Any]:
        """Return canonical semantic compounds by BTDU atom identity, not external lists."""
        with self._db() as db:
            code=[dict(r) for r in db.execute("""SELECT atom_id,value_text FROM language_nodes
                WHERE node_kind='code_token' AND value_text IS NOT NULL ORDER BY atom_id""")]
            english=[dict(r) for r in db.execute("""SELECT atom_id,lower(lemma) lemma FROM english_lemmas
                WHERE lemma IS NOT NULL ORDER BY atom_id""")]
            math=[dict(r) for r in db.execute("""SELECT atom_id,name FROM math_terms
                WHERE name IS NOT NULL ORDER BY atom_id""")]
        def dedupe(rows,value_key,max_bytes):
            by_value={}
            for r in rows:
                raw=str(r[value_key]).encode("utf-8")
                if not raw or len(raw)>max_bytes: continue
                aid=str(r["atom_id"])
                prev=by_value.get(raw)
                if prev is None or aid<prev: by_value[raw]=aid
            ordered=sorted(((aid,raw) for raw,aid in by_value.items()),key=lambda x:x[0])
            root=sha256({"schema":"entity-btdu-canonical-compound-basis-v1",
                         "entries":[[aid,raw.hex()] for aid,raw in ordered]})
            return ordered,root
        code_rows,code_root=dedupe(code,"value_text",256)
        english_rows,english_root=dedupe(english,"lemma",128)
        math_rows,math_root=dedupe(math,"name",256)
        return {"schema":"entity-btdu-canonical-formula-basis-v1",
                "primitive_bytes":self.primitive_byte_atom_summary(),
                "code":{"count":len(code_rows),"root":code_root,"entries":code_rows},
                "english":{"count":len(english_rows),"root":english_root,"entries":english_rows},
                "math":{"count":len(math_rows),"root":math_root,"entries":math_rows},
                "basis_is_canonical_atom_identity":True,
                "external_payload_reference_required":False}

    def register_directory_asset(self,descriptor:Mapping[str,Any],authorization_receipt:Mapping[str,Any])->dict[str,Any]:
        """Register a BTDU directory formula under the current sovereign lineage."""
        self._authorize(authorization_receipt)
        doc=dict(descriptor)
        if str(doc.get("schema"))!="entity-btdu-directory-asset-v1":
            raise ValueError("unsupported directory asset descriptor")
        required=("asset_ref","owner_lineage","owner_entity_id","controller_entity_id",
                  "tree_sha256","metadata_sha256","formula_sha256","entropy_storage_root",
                  "source_bytes","file_count")
        missing=[k for k in required if doc.get(k) is None]
        if missing:
            raise ValueError("directory asset descriptor missing: "+",".join(missing))
        if str(doc["owner_entity_id"])!=self.sovereign_entity_id:
            raise PermissionError("directory asset owner does not match this sovereign ENTITY identity")
        value={
            "schema":"entity-btdu-directory-asset-registration-v1",
            "asset_ref":str(doc["asset_ref"]),
            "tree_sha256":str(doc["tree_sha256"]),
            "metadata_sha256":str(doc["metadata_sha256"]),
            "formula_sha256":str(doc["formula_sha256"]),
            "entropy_storage_root":str(doc["entropy_storage_root"]),
            "source_bytes":int(doc["source_bytes"]),
            "file_count":int(doc["file_count"]),
        }
        asset_atom=self._put_atom("btdu_directory_asset",value,{
            "formula_only":True,"conventional_payload_required":False,
            "temporary_materialization_only":True,
            "registration_does_not_create_ownership":True,
        })
        lineage_ref="btdu-lineage:"+sha256({"lineage":str(doc["owner_lineage"])})
        lineage_atom=self._put_atom("btdu_lineage_ref",{
            "lineage":str(doc["owner_lineage"]),
            "entity_id":str(doc["owner_entity_id"]),
        },{"asserted_by_entity":self.sovereign_entity_id})
        bond_id=self._bond(
            asset_atom,"registered_under_lineage",lineage_atom,
            source_ref=str(doc["asset_ref"]),target_ref=lineage_ref,
            context="BTDU_DIRECTORY_ASSET_LINEAGE",
            metadata={
                "owner_entity_id":str(doc["owner_entity_id"]),
                "controller_entity_id":str(doc["controller_entity_id"]),
                "does_not_create_ownership":True,
            })
        with self._db() as db:
            db.execute("""INSERT OR REPLACE INTO directory_assets(
                asset_ref,atom_id,owner_lineage,owner_entity_id,controller_entity_id,
                tree_sha256,metadata_sha256,formula_sha256,entropy_storage_root,
                source_bytes,file_count,descriptor_json,registered_at_ms)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
                str(doc["asset_ref"]),asset_atom,str(doc["owner_lineage"]),
                str(doc["owner_entity_id"]),str(doc["controller_entity_id"]),
                str(doc["tree_sha256"]),str(doc["metadata_sha256"]),
                str(doc["formula_sha256"]),str(doc["entropy_storage_root"]),
                int(doc["source_bytes"]),int(doc["file_count"]),
                json.dumps(doc,sort_keys=True,separators=(",",":"),ensure_ascii=False),
                now_ms()))
        return {
            "schema":"entity-btdu-directory-asset-registration-receipt-v1",
            "asset_ref":str(doc["asset_ref"]),"asset_atom_id":asset_atom,
            "lineage":str(doc["owner_lineage"]),"owner_entity_id":str(doc["owner_entity_id"]),
            "lineage_bond_id":bond_id,"tree_sha256":str(doc["tree_sha256"]),
            "formula_sha256":str(doc["formula_sha256"]),
            "entropy_storage_root":str(doc["entropy_storage_root"]),
            "source_bytes":int(doc["source_bytes"]),"file_count":int(doc["file_count"]),
            "conventional_payload_required":False,
            "temporary_materialization_only":True,
        }

    def directory_asset_binding(self,asset_ref:str)->dict[str,Any]:
        with self._db() as db:
            row=db.execute("SELECT * FROM directory_assets WHERE asset_ref=?",(str(asset_ref),)).fetchone()
        if row is None:
            raise KeyError(asset_ref)
        return {
            "schema":"entity-btdu-directory-asset-binding-v1",
            "asset_ref":str(row["asset_ref"]),"asset_atom_id":str(row["atom_id"]),
            "owner_lineage":str(row["owner_lineage"]),
            "owner_entity_id":str(row["owner_entity_id"]),
            "controller_entity_id":str(row["controller_entity_id"]),
            "tree_sha256":str(row["tree_sha256"]),
            "metadata_sha256":str(row["metadata_sha256"]),
            "formula_sha256":str(row["formula_sha256"]),
            "entropy_storage_root":str(row["entropy_storage_root"]),
            "source_bytes":int(row["source_bytes"]),"file_count":int(row["file_count"]),
            "conventional_payload_required":False,
        }

    def _bond(self,source_atom_id:str,predicate:str,target_atom_id:str,*,source_ref:str,target_ref:str,context:str,metadata:dict[str,Any])->str:
        with self._write_lock:
            bid,op=self.atomic.bond_op(source_atom_id,str(predicate),target_atom_id,context=str(context),metadata=dict(metadata))
            if op: self._commit([op],metadata={"btdu":"bond","predicate":str(predicate)})
            with self._db() as db: db.execute("INSERT OR REPLACE INTO edges VALUES(?,?,?,?,?,?,?)",(bid,source_atom_id,str(predicate),target_atom_id,str(source_ref),str(target_ref),json.dumps(metadata,sort_keys=True)))
            return bid

    def _ensure_root(self):
        root_ref=f"btdu:{self.sovereign_entity_id}"
        rows=[("btdu_root",{"schema":BTDU_SCHEMA,"version":BTDU_VERSION,"root_ref":root_ref,"sovereign_entity_id":self.sovereign_entity_id,"protocol_entity_id":self.protocol_entity_id,"steward_entity_id":self.steward_entity_id},{"authority_model":"ENTITY","state_engine":"ADAM","advisory_reasoner":"NIKI","primary_payload_model":"RECONSTRUCTIVE_FORMULA","conventional_bulk_storage_replacement":True}),
              ("entity_ref",{"entity_id":self.sovereign_entity_id},{"role":"sovereign_authority"}),
              ("entity_ref",{"entity_id":self.protocol_entity_id},{"role":"protocol_origin"}),
              ("entity_ref",{"entity_id":self.steward_entity_id},{"role":"steward"})]
        self.root_atom_id,self.sovereign_atom_id,self.protocol_atom_id,self.steward_atom_id=self._put_atoms(rows,reason="initialize_root")
        boundary={"protocol_origin_is_not_asset_provenance":True,"protocol_origin_does_not_transfer_user_asset_ownership":True,"economic_participation_requires_explicit_terms":True,"automatic_protocol_royalty_bps":0}
        self._bond(self.root_atom_id,"governed_by",self.sovereign_atom_id,source_ref=root_ref,target_ref=self.sovereign_entity_id,context="BTDU_AUTHORITY",metadata=boundary)
        self._bond(self.root_atom_id,"uses_protocol",self.protocol_atom_id,source_ref=root_ref,target_ref=self.protocol_entity_id,context="BTDU_PROTOCOL",metadata=boundary)
        self._bond(self.protocol_atom_id,"stewarded_by",self.steward_atom_id,source_ref=self.protocol_entity_id,target_ref=self.steward_entity_id,context="BTDU_PROTOCOL",metadata=boundary)
        self.install_genesis_contract()
        self.install_storage_contract()

    def install_genesis_contract(self)->dict[str,Any]:
        pids=self._put_atoms([("btdu_genesis_primitive",{"name":n},{"immutable_semantic":True}) for n in GENESIS_PRIMITIVES],reason="genesis_primitives")
        mids=self._put_atoms([("btdu_market_stage",{"name":n},{"genesis_market_semantic":True}) for n in GENESIS_MARKET_LIFECYCLE],reason="genesis_market_lifecycle")
        md={"btdu_is_additive":True,"genesis_semantics_preserved":True,"rights_not_created_by_topology":True,"economic_entitlement_not_created_by_topology":True}
        for aid,n in zip(pids,GENESIS_PRIMITIVES): self._bond(self.root_atom_id,"preserves_genesis_primitive",aid,source_ref=f"btdu:{self.sovereign_entity_id}",target_ref=n,context="BTDU_GENESIS_INVARIANT",metadata=md)
        for i in range(len(mids)-1): self._bond(mids[i],"precedes",mids[i+1],source_ref=GENESIS_MARKET_LIFECYCLE[i],target_ref=GENESIS_MARKET_LIFECYCLE[i+1],context="BTDU_GENESIS_MARKET_LIFECYCLE",metadata=md)
        return {"schema":"entity-btdu-genesis-contract-v1","primitives":list(GENESIS_PRIMITIVES),"market_lifecycle":list(GENESIS_MARKET_LIFECYCLE),"btdu_is_additive":True}

    def install_storage_contract(self)->dict[str,Any]:
        contract={"schema":"entity-btdu-storage-contract-v2",
                  "formula_schema":BTDU_FORMULA_SCHEMA,"formula_version":BTDU_FORMULA_VERSION,
                  "entropy_reservoir_schema":BTDU_STORAGE_SCHEMA,"entropy_reservoir_version":BTDU_STORAGE_VERSION,
                  "one_authoritative_payload":True,"unlimited_semantic_views":True,
                  "primary_payload_model":"RECONSTRUCTIVE_FORMULA",
                  "formula_is_authority":True,"latent_occurrence_bonds":True,
                  "temporary_materialization_only":True,
                  "conventional_bulk_storage_required":False,
                  "irreducible_entropy_reservoir_only":True,
                  "raw_payload_bytes_in_adam_journal":False,
                  "legacy_exact_representations":"read-only migration compatibility"}
        aid=self._put_atom("btdu_storage_contract",contract,
                           {"authoritative_payload_contract":True,"additive_to_genesis":True})
        self._bond(self.root_atom_id,"formulates_payloads_under",aid,
                   source_ref=f"btdu:{self.sovereign_entity_id}",target_ref="btdu-formula-kernel:v1",
                   context="BTDU_STORAGE_AUTHORITY",
                   metadata={"one_authoritative_payload":True,"semantic_views_unlimited":True,
                             "formula_is_authority":True,"rights_created":False,"ownership_created":False})
        return dict(contract,atom_id=aid)

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

    def _formula_atom(self,formula:Mapping[str,Any])->str:
        value={"schema":"entity-btdu-formula-reference-v1",
               "formula_object_id":str(formula["formula_object_id"]),
               "content_sha256":str(formula["content_sha256"]),
               "size_bytes":int(formula["size_bytes"]),
               "root_node_id":str(formula["root_node_id"]),
               "formula_sha256":str(formula["formula_sha256"]),
               "unit_count":int(formula["unit_count"])}
        return self._put_atom("btdu_formula",value,
            {"authoritative_payload":True,"formula_kernel":BTDU_FORMULA_VERSION,
             "raw_bytes_embedded_in_adam":False,"semantic_views_unlimited":True,
             "latent_occurrence_bonds":True})

    def _bind_object_formula(self,object_ref:str,object_atom:str,formula:Mapping[str,Any],*,migrated_from_legacy:bool=False)->str:
        formula_atom=self._formula_atom(formula)
        md={"authoritative_payload":True,"one_authoritative_payload":True,
            "formula_is_authority":True,"semantic_views_unlimited":True,
            "latent_occurrence_bonds":True,"migrated_from_legacy":bool(migrated_from_legacy),
            "raw_bytes_embedded_in_adam":False}
        self._bond(object_atom,"formulated_as",formula_atom,source_ref=str(object_ref),
                   target_ref=str(formula["formula_object_id"]),context="BTDU_RECONSTRUCTIVE_FORMULA",metadata=md)
        with self._db() as db:
            db.execute("""INSERT OR REPLACE INTO object_formulas(
                object_ref,formula_object_id,formula_sha256,root_node_id,
                authoritative,migrated_from_legacy,bound_at_ms) VALUES(?,?,?,?,?,?,?)""",
                (str(object_ref),str(formula["formula_object_id"]),str(formula["formula_sha256"]),
                 str(formula["root_node_id"]),1,1 if migrated_from_legacy else 0,now_ms()))
        return formula_atom

    def _register_formula(self,*,logical_path:str,formula:Mapping[str,Any],
            source_entity_id:str,controller_entity_id:str,rights_holder_entity_id:str|None,
            provenance_ref:str,media_type:str)->dict[str,Any]:
        content_sha=str(formula["content_sha256"])
        object_ref="btdu-object:"+sha256({"logical_path":str(logical_path).replace("\\","/"),
            "content_sha256":content_sha,"source_entity_id":str(source_entity_id)})
        value={"schema":"entity-btdu-object-v3","object_ref":object_ref,
               "logical_path":str(logical_path).replace("\\","/"),"content_sha256":content_sha,
               "size_bytes":int(formula["size_bytes"]),"evidence_object_id":str(formula["formula_object_id"]),
               "formula_object_id":str(formula["formula_object_id"]),
               "formula_sha256":str(formula["formula_sha256"]),
               "formula_root_node_id":str(formula["root_node_id"]),
               "formula_unit_count":int(formula["unit_count"]),"media_type":str(media_type)}
        object_atom=self._put_atom("btdu_object",value,
            {"exact_content_externalized":True,"authoritative_payload":"BTDU_RECONSTRUCTIVE_FORMULA",
             "raw_bytes_embedded_in_adam":False})
        formula_atom=self._bind_object_formula(object_ref,object_atom,formula,migrated_from_legacy=False)
        refs=[("source",source_entity_id,"data_origin"),("controller",controller_entity_id,"data_controller")]
        if rights_holder_entity_id: refs.append(("rights_holder",rights_holder_entity_id,"rights_holder"))
        ref_ids=self._put_atoms([("entity_ref",{"entity_id":str(eid)},{"role":role}) for _,eid,role in refs],reason="object_entity_refs")
        evidence_atom=self._put_atom("evidence_ref",
            {"formula_object_id":str(formula["formula_object_id"]),"sha256":content_sha},
            {"media_type":str(media_type),"payload_authority":"BTDU_RECONSTRUCTIVE_FORMULA"})
        provenance_atom=self._put_atom("provenance_ref",{"ref":str(provenance_ref)},{"source_entity_id":str(source_entity_id)})
        boundary={"protocol_origin_is_not_asset_provenance":True,"topology_does_not_create_ownership":True,
                  "topology_does_not_create_economic_entitlement":True,"one_authoritative_payload":True,
                  "formula_is_authority":True}
        self._bond(object_atom,"contained_in",self.root_atom_id,source_ref=object_ref,
                   target_ref=f"btdu:{self.sovereign_entity_id}",context="BTDU_MEMBERSHIP",metadata=boundary)
        self._bond(object_atom,"represented_by_evidence",evidence_atom,source_ref=object_ref,
                   target_ref=str(formula["formula_object_id"]),context="BTDU_EVIDENCE",
                   metadata={"sha256":content_sha,"authoritative_payload":True,"formula_is_authority":True})
        self._bond(object_atom,"provenance_recorded_as",provenance_atom,source_ref=object_ref,
                   target_ref=str(provenance_ref),context="BTDU_PROVENANCE",
                   metadata={"source_entity_id":str(source_entity_id)})
        for (label,eid,role),atom_id in zip(refs,ref_ids):
            predicate={"source":"sourced_from","controller":"controlled_by","rights_holder":"rights_asserted_by"}[label]
            md=dict(boundary,role=role,assertion_explicit=(label=="rights_holder"))
            self._bond(object_atom,predicate,atom_id,source_ref=object_ref,target_ref=str(eid),
                       context="BTDU_PROVENANCE_RIGHTS",metadata=md)
        with self._db() as db:
            db.execute("""INSERT OR REPLACE INTO objects(
                object_ref,atom_id,logical_path,content_sha256,size_bytes,media_type,evidence_object_id,
                source_entity_id,controller_entity_id,rights_holder_entity_id,provenance_ref,created_at_ms)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (object_ref,object_atom,value["logical_path"],content_sha,int(formula["size_bytes"]),
                 str(media_type),str(formula["formula_object_id"]),str(source_entity_id),
                 str(controller_entity_id),str(rights_holder_entity_id) if rights_holder_entity_id else None,
                 str(provenance_ref),now_ms()))
        return dict(value,atom_id=object_atom,formula_atom_id=formula_atom,
                    source_entity_id=str(source_entity_id),controller_entity_id=str(controller_entity_id),
                    rights_holder_entity_id=str(rights_holder_entity_id) if rights_holder_entity_id else None,
                    provenance_ref=str(provenance_ref))

    def ingest_bytes(self,*,logical_path:str,data:bytes,authorization_receipt:Mapping[str,Any],
            source_entity_id:str,controller_entity_id:str,rights_holder_entity_id:str|None=None,
            provenance_ref:str,media_type:str="application/octet-stream")->dict[str,Any]:
        self._authorize(authorization_receipt)
        formula=self.formulas.put_bytes(bytes(data))
        return self._register_formula(logical_path=logical_path,formula=formula,
            source_entity_id=source_entity_id,controller_entity_id=controller_entity_id,
            rights_holder_entity_id=rights_holder_entity_id,provenance_ref=provenance_ref,
            media_type=media_type)

    def ingest_file(self,path:str|Path,authorization_receipt:Mapping[str,Any],**kwargs:Any)->dict[str,Any]:
        self._authorize(authorization_receipt)
        p=Path(path)
        if not p.is_file(): raise FileNotFoundError(str(p))
        logical_path=kwargs.pop("logical_path",p.name)
        media=kwargs.pop("media_type",None) or mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        formula=self.formulas.put_path(p)
        return self._register_formula(logical_path=logical_path,formula=formula,media_type=media,**kwargs)

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
        with self._write_lock:
            return self._mirror_economic_lineage_locked(nodes=nodes,edges=edges,authorization_receipt=authorization_receipt,evidence_sha256=evidence_sha256)

    def _mirror_economic_lineage_locked(self,*,nodes:list[dict[str,Any]],edges:list[dict[str,Any]],authorization_receipt:Mapping[str,Any],evidence_sha256:str|None=None)->dict[str,Any]:
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

    def normalize_oriented_relation(self,left_ref:str,operator:str,right_ref:str,context:dict[str,Any]|None=None)->dict[str,Any]:
        n=self.orientation.topology_for(left_ref,operator,right_ref,context)
        return dict(n.__dict__)

    def register_oriented_relations(self,rows:list[dict[str,Any]],authorization_receipt:Mapping[str,Any],*,chunk_size:int=2000)->dict[str,int]:
        self._authorize(authorization_receipt)
        return self.orientation.register_bulk(rows,chunk_size=chunk_size)

    def language_summary(self)->dict[str,Any]:
        with self._db() as db:
            tables={r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            counts={name:(db.execute("SELECT count(*) AS n FROM "+name).fetchone()["n"] if name in tables else 0)
                    for name in ("language_nodes","language_relations","english_synsets","english_lemmas")}
        return {"schema":"entity-btdu-language-summary-v1","build_revision":BTDU_BUILD_REVISION,**counts}

    def lookup_english_lemma(self,lemma:str,*,pos:str|None=None,limit:int=50)->dict[str,Any]:
        with self._db() as db:
            tables={r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if not {"english_lemmas","english_synsets","language_relations"}.issubset(tables):
                return {"schema":"entity-btdu-english-lookup-v1","query":str(lemma),"matches":[]}
            sql="""SELECT l.lemma_ref,l.lemma,l.pos,l.synset_count,r.source_ref AS synset_ref,s.gloss
                   FROM english_lemmas l
                   LEFT JOIN language_relations r ON r.target_ref=l.lemma_ref AND r.predicate='contains_lemma'
                   LEFT JOIN english_synsets s ON s.synset_ref=r.source_ref
                   WHERE lower(l.lemma)=lower(?)"""
            args=[str(lemma)]
            if pos is not None:
                sql+=" AND l.pos=?"; args.append(str(pos))
            sql+=" ORDER BY l.pos,r.source_ref LIMIT ?"; args.append(max(1,min(int(limit),500)))
            rows=[dict(r) for r in db.execute(sql,args).fetchall()]
        return {"schema":"entity-btdu-english-lookup-v1","query":str(lemma),"pos":pos,"matches":rows}

    def code_token_usage(self,token:str,*,limit:int=100)->dict[str,Any]:
        ref="code-token:"+str(token)
        with self._db() as db:
            tables={r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if not {"language_nodes","language_relations"}.issubset(tables):
                return {"schema":"entity-btdu-code-token-usage-v1","token":str(token),"languages":[]}
            rows=db.execute("""SELECT source_ref,metadata_json FROM language_relations
                               WHERE target_ref=? AND predicate='uses_code_token'
                               ORDER BY source_ref LIMIT ?""",(ref,max(1,min(int(limit),500)))).fetchall()
        uses=[]
        for r in rows:
            md=json.loads(r["metadata_json"]) if r["metadata_json"] else {}
            uses.append({"language_ref":r["source_ref"],"token_class":md.get("token_class"),
                         "occurrence_count":md.get("occurrence_count"),"direction_preserved":md.get("direction_preserved",True)})
        return {"schema":"entity-btdu-code-token-usage-v1","token":str(token),"languages":uses}

    def install_cross_domain_semantic_bridge(self,authorization_receipt:Mapping[str,Any])->dict[str,Any]:
        self._authorize(authorization_receipt)
        with self._write_lock:
            with self._db() as db:
                return install_cross_domain_bridge_index(db,authorization_receipt)

    def resolve_cross_domain_concept(self,english_term:str)->dict[str,Any]:
        with self._db() as db:
            rows=db.execute("""SELECT l.lemma,l.pos,r.target_ref AS concept_ref,b.math_operator,b.code_token_ref
                               FROM english_lemmas l
                               JOIN language_relations r ON r.source_ref=l.lemma_ref AND r.predicate='maps_to_math_semantic'
                               JOIN semantic_bridges b ON b.concept_ref=r.target_ref
                               WHERE lower(l.lemma)=lower(?)
                               ORDER BY l.pos,r.target_ref""",(str(english_term),)).fetchall()
        return {"schema":"entity-btdu-cross-domain-resolution-v1","query":str(english_term),"matches":[dict(r) for r in rows]}

    def cross_domain_bridge_summary(self)->dict[str,Any]:
        with self._db() as db:
            tables={r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "semantic_bridges" not in tables:
                return {"schema":"entity-btdu-cross-domain-bridge-summary-v1","concepts":0,"relations":0}
            concepts=int(db.execute("SELECT count(*) FROM semantic_bridges").fetchone()[0])
            relations=int(db.execute("SELECT count(*) FROM language_relations WHERE predicate IN ('maps_to_math_semantic','realized_as_code_token')").fetchone()[0]) if "language_relations" in tables else 0
        return {"schema":"entity-btdu-cross-domain-bridge-summary-v1","concepts":concepts,"relations":relations}

    def canonical_replication_root(self)->str:
        """Authority-neutral deterministic root for exact BTDU semantic replication.

        ADAM's signed atomic root intentionally binds a local authority identity; two
        independent authorities can therefore have different signed atomic roots while
        carrying identical BTDU content. This root hashes deterministic BTDU content IDs
        and semantic/economic rows so replicas can prove exact payload convergence
        without pretending their authority envelopes are identical.
        """
        atom_ids=sorted(str(x) for x in self.atomic.atoms.keys())
        compound_ids=sorted(str(x) for x in self.atomic.compounds.keys())
        bond_ids=sorted(str(x) for x in self.atomic.bonds.keys())
        with self._db() as db:
            tables={r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            def rows(table,cols):
                if table not in tables: return []
                return [tuple(r) for r in db.execute("SELECT "+",".join(cols)+" FROM "+table+" ORDER BY "+",".join(cols))]
            payload={
              "schema":"entity-btdu-canonical-replication-root-v1",
              "atoms":atom_ids,"compounds":compound_ids,"bonds":bond_ids,
              "economic_nodes":rows("economic_nodes",("node_ref","atom_id","node_kind","metadata_json")),
              "economic_edges":rows("economic_edges",("edge_id","source_ref","predicate","target_ref","source_atom_id","target_atom_id","bond_id","evidence_sha256","metadata_json")),
              "semantic_bridges":rows("semantic_bridges",("concept_ref","math_operator","code_token_ref","english_refs_json","metadata_json","bridge_hash")),
              "object_formulas":rows("object_formulas",("object_ref","formula_object_id","formula_sha256","root_node_id","authoritative","migrated_from_legacy")),
              "formula_root":self.formulas.formula_root(),
            }
        return sha256(payload)

    def passport_binding(self,object_ref:str)->dict[str,Any]:
        with self._db() as db:
            row=db.execute("""SELECT o.object_ref,o.atom_id,o.content_sha256,o.controller_entity_id,
                              o.source_entity_id,o.rights_holder_entity_id,f.formula_object_id,
                              f.formula_sha256,f.root_node_id
                              FROM objects o LEFT JOIN object_formulas f ON f.object_ref=o.object_ref
                              WHERE o.object_ref=?""",(str(object_ref),)).fetchone()
        if not row: raise KeyError(object_ref)
        return {"schema":"entity-btdu-passport-binding-v1","btdu_version":BTDU_VERSION,
                "universe_root":self.atomic.root_hash,"object_ref":row["object_ref"],"object_atom_id":row["atom_id"],
                "content_sha256":row["content_sha256"],"formula_object_id":row["formula_object_id"],
                "formula_sha256":row["formula_sha256"],"formula_root_node_id":row["root_node_id"],
                "sovereign_entity_id":self.sovereign_entity_id,
                "controller_entity_id":row["controller_entity_id"],"source_entity_id":row["source_entity_id"],
                "rights_holder_entity_id":row["rights_holder_entity_id"],"protocol_origin_is_not_asset_provenance":True,
                "topology_does_not_create_ownership":True,"topology_does_not_create_economic_entitlement":True,
                "automatic_protocol_royalty_bps":0}

    def project_object_context(self,object_ref:str)->dict[str,Any]:
        with self._db() as db:
            obj=db.execute("SELECT * FROM objects WHERE object_ref=?",(str(object_ref),)).fetchone()
            if not obj: raise KeyError(object_ref)
            formula=db.execute("SELECT formula_object_id FROM object_formulas WHERE object_ref=?",(str(object_ref),)).fetchone()
            edges=db.execute("SELECT predicate,target_ref,metadata_json FROM edges WHERE source_ref=? ORDER BY predicate,target_ref",(str(object_ref),)).fetchall()
        lines=[f"{object_ref} {row['predicate']} {row['target_ref']}" for row in edges]
        return {"schema":"niki-btdu-context-v1","object_ref":str(object_ref),
                "content_sha256":obj["content_sha256"],"size_bytes":int(obj["size_bytes"]),
                "formula_object_id":formula["formula_object_id"] if formula else None,
                "context":"\n".join(lines),"raw_content_included":False,
                "authority_transferred_to_niki":False,"execution_authority":"ENTITY","state_engine":"ADAM"}

    def _object_formula_id(self,object_ref:str)->str|None:
        with self._db() as db:
            row=db.execute("SELECT formula_object_id FROM object_formulas WHERE object_ref=?",(str(object_ref),)).fetchone()
        return str(row["formula_object_id"]) if row else None

    def reconstruct_object(self,object_ref:str)->bytes:
        formula_id=self._object_formula_id(object_ref)
        if formula_id is not None:
            return self.formulas.read_all(formula_id)
        with self._db() as db:
            row=db.execute("SELECT evidence_object_id,content_sha256 FROM objects WHERE object_ref=?",(str(object_ref),)).fetchone()
        if not row: raise KeyError(object_ref)
        raw=self.evidence.exact.reconstruct(row["evidence_object_id"])
        if sha256(raw)!=row["content_sha256"]: raise RuntimeError("BTDU legacy exact evidence reconstruction hash mismatch")
        return raw

    def stream_object(self,object_ref:str):
        formula_id=self._object_formula_id(object_ref)
        if formula_id is None:
            yield self.reconstruct_object(object_ref); return
        yield from self.formulas.iter_object(formula_id)

    def read_object_range(self,object_ref:str,offset:int,length:int)->bytes:
        formula_id=self._object_formula_id(object_ref)
        if formula_id is None:
            raw=self.reconstruct_object(object_ref); return raw[int(offset):int(offset)+int(length)]
        return self.formulas.read_range(formula_id,offset,length)

    def materialize_object(self,object_ref:str,output_path:str|Path)->dict[str,Any]:
        formula_id=self._object_formula_id(object_ref)
        if formula_id is None:
            raw=self.reconstruct_object(object_ref); out=Path(output_path); out.parent.mkdir(parents=True,exist_ok=True)
            out.write_bytes(raw)
            return {"object_ref":str(object_ref),"path":str(out),"bytes":len(raw),"sha256":sha256(raw),"legacy":True}
        result=self.formulas.materialize(formula_id,output_path)
        return dict(result,object_ref=str(object_ref),legacy=False)

    def transient_object_bond_plan(self,object_ref:str)->dict[str,Any]:
        formula_id=self._object_formula_id(object_ref)
        if formula_id is None: raise RuntimeError("legacy object must be migrated before transient formula expansion")
        return self.formulas.transient_bond_plan(formula_id)

    def migrate_legacy_object(self,object_ref:str,authorization_receipt:Mapping[str,Any])->dict[str,Any]:
        self._authorize(authorization_receipt)
        existing=self._object_formula_id(object_ref)
        if existing is not None:
            return {"schema":"entity-btdu-formula-migration-v1","object_ref":str(object_ref),
                    "formula_object_id":existing,"already_migrated":True}
        with self._db() as db:
            row=db.execute("SELECT object_ref,atom_id,evidence_object_id,content_sha256,size_bytes FROM objects WHERE object_ref=?",(str(object_ref),)).fetchone()
        if not row: raise KeyError(object_ref)
        raw=self.evidence.exact.reconstruct(row["evidence_object_id"])
        if sha256(raw)!=row["content_sha256"] or len(raw)!=int(row["size_bytes"]):
            raise RuntimeError("legacy object failed exact reconstruction before formula migration")
        formula=self.formulas.put_bytes(raw)
        self._bind_object_formula(str(object_ref),str(row["atom_id"]),formula,migrated_from_legacy=True)
        return {"schema":"entity-btdu-formula-migration-v1","object_ref":str(object_ref),
                "formula_object_id":formula["formula_object_id"],"formula_sha256":formula["formula_sha256"],
                "bytes":len(raw),"already_migrated":False,"legacy_signed_history_preserved":True,
                "new_authoritative_payload":"BTDU_RECONSTRUCTIVE_FORMULA"}

    def migrate_legacy_objects(self,authorization_receipt:Mapping[str,Any],*,limit:int|None=None,batch_size:int=256)->dict[str,Any]:
        """Migrate legacy payloads to formula authority using durable signed batches.

        Formula creation remains independently journaled before each binding.  The
        ADAM formula-atom + formulated-as bond operations are then committed in a
        deterministic batch, followed by their rebuildable SQLite indexes.  If a
        process stops after the signed ADAM commit but before index insertion, a
        rerun is idempotent: existing atom/bond identities are reused and only the
        missing indexes are restored.
        """
        self._authorize(authorization_receipt)
        batch_size=max(1,min(1024,int(batch_size)))
        with self._db() as db:
            rows=db.execute("""SELECT o.object_ref,o.atom_id,o.evidence_object_id,o.content_sha256,o.size_bytes
                               FROM objects o LEFT JOIN object_formulas f ON f.object_ref=o.object_ref
                               WHERE f.object_ref IS NULL ORDER BY o.created_at_ms,o.object_ref""").fetchall()
        selected=rows if limit is None else rows[:max(0,int(limit))]
        pending_ops=[]; pending_atoms=set(); pending_edges=[]; pending_bindings=[]
        migrated=0

        formula_atom_metadata={"authoritative_payload":True,"formula_kernel":BTDU_FORMULA_VERSION,
            "raw_bytes_embedded_in_adam":False,"semantic_views_unlimited":True,
            "latent_occurrence_bonds":True}
        binding_metadata={"authoritative_payload":True,"one_authoritative_payload":True,
            "formula_is_authority":True,"semantic_views_unlimited":True,
            "latent_occurrence_bonds":True,"migrated_from_legacy":True,
            "raw_bytes_embedded_in_adam":False}

        def flush_batch():
            nonlocal pending_ops,pending_atoms,pending_edges,pending_bindings
            if not pending_bindings: return
            self._commit(pending_ops,metadata={"btdu":"formula_bulk_migration",
                "objects":len(pending_bindings),"deterministic_batch_size":batch_size})
            with self._db() as db:
                if pending_edges:
                    db.executemany("INSERT OR REPLACE INTO edges VALUES(?,?,?,?,?,?,?)",pending_edges)
                db.executemany("""INSERT OR REPLACE INTO object_formulas(
                    object_ref,formula_object_id,formula_sha256,root_node_id,
                    authoritative,migrated_from_legacy,bound_at_ms) VALUES(?,?,?,?,?,?,?)""",pending_bindings)
            pending_ops=[]; pending_atoms=set(); pending_edges=[]; pending_bindings=[]

        for row in selected:
            object_ref=str(row["object_ref"])
            raw=self.evidence.exact.reconstruct(row["evidence_object_id"])
            if sha256(raw)!=row["content_sha256"] or len(raw)!=int(row["size_bytes"]):
                raise RuntimeError("legacy object failed exact reconstruction before formula migration")
            formula=self.formulas.put_bytes(raw)
            formula_value={"schema":"entity-btdu-formula-reference-v1",
                "formula_object_id":str(formula["formula_object_id"]),
                "content_sha256":str(formula["content_sha256"]),
                "size_bytes":int(formula["size_bytes"]),
                "root_node_id":str(formula["root_node_id"]),
                "formula_sha256":str(formula["formula_sha256"]),
                "unit_count":int(formula["unit_count"])}
            formula_atom,atom_op=self.atomic.atom_op("btdu_formula",formula_value,dict(formula_atom_metadata))
            if atom_op is not None and formula_atom not in pending_atoms:
                pending_ops.append(atom_op); pending_atoms.add(formula_atom)
            bond_id,bond_op=self.atomic.bond_op(str(row["atom_id"]),"formulated_as",formula_atom,
                context="BTDU_RECONSTRUCTIVE_FORMULA",metadata=dict(binding_metadata))
            if bond_op is not None: pending_ops.append(bond_op)
            pending_edges.append((bond_id,str(row["atom_id"]),"formulated_as",formula_atom,
                object_ref,str(formula["formula_object_id"]),json.dumps(binding_metadata,sort_keys=True)))
            pending_bindings.append((object_ref,str(formula["formula_object_id"]),
                str(formula["formula_sha256"]),str(formula["root_node_id"]),1,1,now_ms()))
            migrated+=1
            if len(pending_bindings)>=batch_size: flush_batch()
            # Release per-object reconstruction/compiler temporaries promptly on
            # memory-constrained production devices. Durable formula/ADAM state is
            # already owned by the journals or pending canonical batch structures.
            raw=None; formula=None; formula_value=None; atom_op=None; bond_op=None
            if migrated%4==0: gc.collect()
        flush_batch()
        gc.collect()
        return {"schema":"entity-btdu-formula-bulk-migration-v2","migrated":migrated,
                "total_candidates":len(rows),"remaining":len(rows)-migrated,
                "batch_size":batch_size,"formula":self.formulas.stats()}

    def storage_status(self,*,deep:bool=False)->dict[str,Any]:
        formula=self.formulas.verify(deep=deep)
        entropy=self.storage.verify(deep=False)
        return {"schema":"entity-btdu-storage-status-v2",
                "pass":bool(formula.get("pass")) and bool(entropy.get("pass")),
                "formula":formula,
                "entropy_reservoir":entropy,
                "one_authoritative_payload":True,
                "formula_is_authority":True,
                "conventional_bulk_storage_required":False}

    def list_objects(self)->list[dict[str,Any]]:
        with self._db() as db: rows=db.execute("SELECT * FROM objects ORDER BY logical_path,object_ref").fetchall()
        return [dict(r) for r in rows]

    def repository_manifests(self)->list[dict[str,Any]]:
        with self._db() as db: rows=db.execute("SELECT manifest_json FROM repository_manifests ORDER BY created_at_ms,manifest_id").fetchall()
        return [json.loads(r["manifest_json"]) for r in rows]

    def verify(self,*,deep:bool=True)->dict[str,Any]:
        atomic=self.runtime.verify(); problems=[]; objects=self.list_objects()
        formula_check=self.formulas.verify(deep=False)
        reservoir_check=self.storage.verify(deep=False)
        if not formula_check.get("pass"): problems.append("formula_kernel")
        if not reservoir_check.get("pass"): problems.append("entropy_reservoir")
        if deep:
            with self._db() as db:
                formula_map={r["object_ref"]:r["formula_object_id"] for r in db.execute("SELECT object_ref,formula_object_id FROM object_formulas")}
            for row in objects:
                try:
                    formula_id=formula_map.get(row["object_ref"])
                    if formula_id:
                        fv=self.formulas.verify_object(formula_id,deep=True)
                        if not fv.get("pass"): problems.append("formula:"+row["object_ref"])
                        fobj=self.formulas.object_record(formula_id)
                        if fobj["content_sha256"]!=row["content_sha256"] or int(fobj["size_bytes"])!=int(row["size_bytes"]):
                            problems.append("formula_binding:"+row["object_ref"])
                    else:
                        raw=self.evidence.exact.reconstruct(row["evidence_object_id"])
                        if sha256(raw)!=row["content_sha256"]: problems.append("hash:"+row["object_ref"])
                        with self._db() as db:
                            atomized=db.execute("SELECT target_ref FROM edges WHERE source_ref=? AND predicate='atomized_as'",(row["object_ref"],)).fetchone()
                        if atomized and sha256(self.reconstruct_exact_bytes(atomized["target_ref"]))!=row["content_sha256"]:
                            problems.append("atomization:"+row["object_ref"])
                except Exception:
                    problems.append("reconstruct:"+row["object_ref"])
        primitive_targets=set(GENESIS_PRIMITIVES)
        with self._db() as db:
            present={r["target_ref"] for r in db.execute("SELECT target_ref FROM edges WHERE predicate='preserves_genesis_primitive'").fetchall()}
            econ_edges=[dict(r) for r in db.execute("SELECT * FROM economic_edges").fetchall()]
            formula_bindings=int(db.execute("SELECT count(*) FROM object_formulas").fetchone()[0])
        if not primitive_targets.issubset(present): problems.append("genesis_primitives")
        orientation=self.orientation.verify()
        if not orientation.get("pass"): problems.append("orientation")
        return {"schema":"entity-btdu-verification-v1","btdu_version":BTDU_VERSION,
                "build_revision":BTDU_BUILD_REVISION,"formula_version":BTDU_FORMULA_VERSION,
                "pass":bool(atomic.get("pass")) and not problems,"atomic":atomic,
                "formula":formula_check,"entropy_reservoir":reservoir_check,
                "orientation":orientation,"language_summary":self.language_summary(),
                "atomic_root":self.atomic.root_hash,"formula_root":self.formulas.formula_root(),
                "sovereign_entity_id":self.sovereign_entity_id,"protocol_entity_id":self.protocol_entity_id,
                "objects":len(objects),"formula_bindings":formula_bindings,
                "economic_lineage_edges":len(econ_edges),
                "genesis_primitives_preserved":primitive_targets.issubset(present),
                "one_authoritative_payload":True,"formula_is_authority":True,
                "latent_occurrence_bonds":True,"temporary_materialization_only":True,
                "conventional_bulk_storage_required":False,
                "raw_payload_bytes_in_adam_journal_for_new_objects":False,
                "protocol_origin_is_not_asset_provenance":True,"automatic_protocol_royalty_bps":0,
                "problems":problems}

    def close(self):
        self.formulas.close(); self.runtime.close()
    def __enter__(self): return self
    def __exit__(self,exc_type,exc,tb): self.close()
