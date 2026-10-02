from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable
import hashlib, json

ORIENTATION_SCHEMA="entity-btdu-orientation-topology-v1"
SAFE_SYMMETRIC={"=":"equality","≠":"inequality","↔":"iff"}
SAFE_INVERSE={"<":("strict_order",False),">":("strict_order",True),
              "≤":("nonstrict_order",False),"≥":("nonstrict_order",True)}
CONTEXTUAL_COMMUTATIVE={"+":"addition","*":"multiplication"}

def _hash(value:Any)->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class NormalizedRelation:
    topology_id:str
    family:str
    mode:str
    left_ref:str
    right_ref:str
    handedness:str
    original_operator:str

class BTDUOrientationLayer:
    def __init__(self, universe):
        self.u=universe
        self._init_db()
    def _init_db(self):
        with self.u._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS orientation_topologies(
              topology_id TEXT PRIMARY KEY, atom_id TEXT NOT NULL UNIQUE,
              family TEXT NOT NULL, mode TEXT NOT NULL,
              left_ref TEXT NOT NULL, right_ref TEXT NOT NULL,
              metadata_json TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_orientation_family
              ON orientation_topologies(family,left_ref,right_ref);
            CREATE TABLE IF NOT EXISTS orientation_occurrences(
              occurrence_ref TEXT PRIMARY KEY, topology_id TEXT NOT NULL,
              source_ref TEXT NOT NULL, handedness TEXT NOT NULL,
              original_operator TEXT NOT NULL, metadata_json TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_orientation_occ_topology
              ON orientation_occurrences(topology_id);
            """)

    @staticmethod
    def normalize(left_ref:str,operator:str,right_ref:str,context:dict[str,Any]|None=None)->NormalizedRelation:
        left,right,op=str(left_ref),str(right_ref),str(operator)
        context=dict(context or {})
        profile=str(context.get("semantic_profile","generic")).lower()
        math_profile=profile in ("math","mathematics","formal_math")
        symmetry_allowed=math_profile or context.get("symmetric_proved") is True
        inverse_allowed=math_profile or context.get("inverse_pair_proved") is True
        mode="ORDERED"; family="ordered:"+op; hand="FWD"; a,b=left,right
        if op in SAFE_SYMMETRIC and symmetry_allowed:
            family=SAFE_SYMMETRIC[op]; mode="SYMMETRIC"
            if right < left: a,b=right,left; hand="REV"
            else: hand="FWD"
        elif op in SAFE_INVERSE and inverse_allowed:
            family,reverse=SAFE_INVERSE[op]; mode="INVERSE_PAIR"
            if reverse: a,b=right,left; hand="REV"
            else: hand="FWD"
        elif op in CONTEXTUAL_COMMUTATIVE and context.get("commutative_proved") is True:
            family="proved_commutative:"+CONTEXTUAL_COMMUTATIVE[op]; mode="CONTEXT_COMMUTATIVE"
            if right < left: a,b=right,left; hand="REV"
            else: hand="FWD"
        value={"schema":ORIENTATION_SCHEMA,"family":family,"mode":mode,"left_ref":a,"right_ref":b}
        return NormalizedRelation("btdu-topology:"+_hash(value),family,mode,a,b,hand,op)
    def topology_for(self,left_ref:str,operator:str,right_ref:str,context:dict[str,Any]|None=None)->NormalizedRelation:
        return self.normalize(left_ref,operator,right_ref,context)

    def register_bulk(self, rows:Iterable[dict[str,Any]], *, chunk_size:int=2000)->dict[str,int]:
        rows=list(rows); prepared=[]; unique={}
        for i,row in enumerate(rows):
            nr=self.normalize(row["left_ref"],row["operator"],row["right_ref"],row.get("context"))
            occurrence=str(row.get("occurrence_ref") or ("orientation-occ:"+_hash({"i":i,"source":row["source_ref"],"triple":[row["left_ref"],row["operator"],row["right_ref"]]})))
            md=dict(row.get("metadata") or {})
            md.update({"topology_does_not_create_rights":True,"topology_does_not_create_ownership":True,
                       "economic_entitlement_created":False,"exact_source_preserved_elsewhere":True})
            prepared.append((row,nr,occurrence,md))
            unique[nr.topology_id]=nr
        topology_atom={}
        unique_items=list(unique.items())
        for start in range(0,len(unique_items),chunk_size):
            part=unique_items[start:start+chunk_size]
            specs=[]
            for tid,nr in part:
                value={"schema":ORIENTATION_SCHEMA,"topology_id":tid,"family":nr.family,"mode":nr.mode,
                       "left_ref":nr.left_ref,"right_ref":nr.right_ref}
                meta={"btdu_orientation":True,"semantic_index":True,"rights_created":False}
                specs.append(("btdu_orientation_topology",value,meta))
            ids=self.u._put_atoms(specs,reason="orientation_topologies")
            for (tid,_),aid in zip(part,ids): topology_atom[tid]=aid
        edge_count=0
        with self.u._db() as db:
            db.executemany("INSERT OR REPLACE INTO orientation_topologies VALUES(?,?,?,?,?,?,?)",[
              (tid,topology_atom[tid],nr.family,nr.mode,nr.left_ref,nr.right_ref,
               json.dumps({"rights_created":False,"schema":ORIENTATION_SCHEMA},sort_keys=True))
              for tid,nr in unique_items])
            db.executemany("INSERT OR REPLACE INTO orientation_occurrences VALUES(?,?,?,?,?,?)",[
              (occ,nr.topology_id,str(row["source_ref"]),nr.handedness,nr.original_operator,json.dumps(md,sort_keys=True))
              for row,nr,occ,md in prepared])
        # Only source records that already have an ADAM atom receive an ADAM semantic edge.
        edge_rows=[]; ops=[]
        for row,nr,occ,md in prepared:
            source_atom=row.get("source_atom_id")
            if not source_atom: continue
            target=topology_atom[nr.topology_id]
            bmeta={"orientation_occurrence":occ,"handedness":nr.handedness,
                   "topology_does_not_create_rights":True}
            bid,op=self.u.atomic.bond_op(source_atom,"expresses_oriented_topology",target,
                    context="BTDU_ORIENTATION_TOPOLOGY",metadata=bmeta)
            if op: ops.append(op)
            edge_rows.append((bid,source_atom,"expresses_oriented_topology",target,
                              str(row["source_ref"]),nr.topology_id,json.dumps(bmeta,sort_keys=True)))
            if len(ops)>=chunk_size:
                self.u._commit(ops,metadata={"btdu":"orientation_edges","count":len(ops)})
                ops=[]
        if ops: self.u._commit(ops,metadata={"btdu":"orientation_edges","count":len(ops)})
        if edge_rows:
            with self.u._db() as db: db.executemany("INSERT OR REPLACE INTO edges VALUES(?,?,?,?,?,?,?)",edge_rows)
            edge_count=len(edge_rows)
        return {"input_occurrences":len(prepared),"unique_topologies":len(unique_items),"adam_edges":edge_count}

    def counts(self)->dict[str,int]:
        with self.u._db() as db:
            return {"topologies":db.execute("select count(*) from orientation_topologies").fetchone()[0],
                    "occurrences":db.execute("select count(*) from orientation_occurrences").fetchone()[0]}
    def verify(self)->dict[str,Any]:
        problems=[]
        with self.u._db() as db:
            rows=db.execute("select topology_id,atom_id,mode from orientation_topologies").fetchall()
            dangling=db.execute("""select count(*) from orientation_occurrences o
                                   left join orientation_topologies t on t.topology_id=o.topology_id
                                   where t.topology_id is null""").fetchone()[0]
        for row in rows:
            if row["atom_id"] not in self.u.atomic.atoms: problems.append("missing_atom:"+row["topology_id"])
            if row["mode"] not in ("SYMMETRIC","INVERSE_PAIR","CONTEXT_COMMUTATIVE","ORDERED"):
                problems.append("bad_mode:"+row["topology_id"])
        if dangling: problems.append("dangling_occurrences:"+str(dangling))
        return {"schema":"entity-btdu-orientation-verification-v1","pass":not problems,
                "counts":self.counts(),"problems":problems,
                "topology_does_not_create_rights":True}
