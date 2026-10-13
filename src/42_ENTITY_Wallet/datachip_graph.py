"""ENTITY DataChip Composer: bounded typed graph, not an execution engine.

A saved graph or a chip hash confers NO wallet right, trade, licence, device
capability, code execution privilege or deployment approval.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from hashlib import sha256
import json, math, os, re, tempfile, uuid
from pathlib import Path

SCHEMA="entity-datachip-composer-draft-v0.1"
MODULE_SCHEMA="entity-datachip-interface-v0.1"
ASSEMBLY_SCHEMA="entity-datachip-assembly-plan-v0.1"
MAX_NODES=128
MAX_EDGES=512
MAX_MODULES=256
MAX_DOCUMENT=512*1024
IDENT=re.compile(r"^[A-Za-z][A-Za-z0-9_.:/@-]{0,159}$")
PORTTYPE=re.compile(r"^[a-z][a-z0-9_.:/-]{0,95}$")
SEMVER=re.compile(r"^\d+\.\d+\.\d+$")
CHIPID=re.compile(r"^edc:formula:sha256:[0-9a-f]{64}$")

class ComposerError(ValueError): pass

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()

def _id(s):
    if not isinstance(s,str) or not IDENT.fullmatch(s):
        raise ComposerError("invalid DataChip identifier")
    return s

def _coord(x):
    if type(x) not in (int,float) or not math.isfinite(x) or abs(x)>10000:
        raise ComposerError("invalid graph coordinate")
    return float(x)

def _ports(value):
    if not isinstance(value,list) or len(value)>24:
        raise ComposerError("invalid port array")
    result=[];seen=set()
    for port in value:
        if not isinstance(port,dict) or set(port)!={"name","type","required"}:
            raise ComposerError("port requires name, type and required")
        name=_id(port["name"])
        kind=port["type"]
        if not isinstance(kind,str) or not PORTTYPE.fullmatch(kind):
            raise ComposerError("invalid port type")
        if name in seen or type(port["required"]) is not bool:
            raise ComposerError("duplicate port or invalid required field")
        result.append(dict(port));seen.add(name)
    return result

def module_spec(x):
    if not isinstance(x,dict) or set(x)!={"schema","module_id","version","name","kind","inputs","outputs"}:
        raise ComposerError("invalid or unrecognized module manifest")
    if x["schema"]!=MODULE_SCHEMA or not isinstance(x["version"],str) or not SEMVER.fullmatch(x["version"]):
        raise ComposerError("unsupported module schema/version")
    module_id=_id(x["module_id"])
    name=x["name"]
    if not isinstance(name,str) or not 1<=len(name)<=80:
        raise ComposerError("invalid module display name")
    if x["kind"] not in ("source","transform","sink","adapter"):
        raise ComposerError("unrecognized module behavior")
    inputs=_ports(x["inputs"]);outputs=_ports(x["outputs"])
    if x["kind"]=="source" and inputs or x["kind"]=="sink" and outputs:
        raise ComposerError("module interface contradicts kind")
    return dict(x,inputs=inputs,outputs=outputs)

def built_in_modules():
    """Declarations only; do not claim these functions are installed/runnable."""
    def port(name,typ,required=True): return {"name":name,"type":typ,"required":required}
    def mod(mid,label,kind,inputs=(),outputs=()):
        return module_spec({"schema":MODULE_SCHEMA,"module_id":mid,"version":"0.1.0",
                            "name":label,"kind":kind,
                            "inputs":[port(*p) for p in inputs],
                            "outputs":[port(*p,False) for p in outputs]})
    entries=[
      mod("entity.edcf.source","EDCF Input","source",outputs=[("archive","entity.archive.edcf")]),
      mod("entity.edcf.verify","Verify EDCF","transform",
          inputs=[("archive","entity.archive.edcf")],outputs=[("content","entity.content.verified")]),
      mod("entity.btdu.formula","BTDU Formula","transform",
          inputs=[("content","entity.content.verified")],outputs=[("formula","entity.btdu.formula")]),
      mod("entity.geo.decode","Geographic Layer","transform",
          inputs=[("content","entity.content.verified")],outputs=[("layer","entity.geo.layer")]),
      mod("entity.geo.terrain","Terrain Analysis","transform",
          inputs=[("layer","entity.geo.layer")],outputs=[("profile","entity.terrain.profile")]),
      mod("entity.host.visual","Host Visualization","sink",
          inputs=[("profile","entity.terrain.profile")]),
      mod("entity.host.export","Formula Export","sink",
          inputs=[("formula","entity.btdu.formula")]),
    ]
    return {x["module_id"]:x for x in entries}

@dataclass
class Graph:
    owner_id:str
    name:str="New DataChip Assembly"
    graph_id:str=field(default_factory=lambda:"graph-"+uuid.uuid4().hex)
    modules:dict=field(default_factory=built_in_modules)
    nodes:list=field(default_factory=list)
    edges:list=field(default_factory=list)

    def __post_init__(self):
        _id(self.owner_id);_id(self.graph_id)
        if not self.graph_id.startswith("graph-") or not isinstance(self.name,str) or not 1<=len(self.name)<=100:
            raise ComposerError("invalid graph identity")
        if len(self.modules)>MAX_MODULES:raise ComposerError("module limit")
        for mid,mod in self.modules.items():
            if mid!=module_spec(mod)["module_id"]:raise ComposerError("invalid registry")

    def register(self,spec:dict):
        rec=module_spec(spec)
        mid=rec["module_id"]
        if mid in self.modules and self.modules[mid]!=rec:
            raise ComposerError("conflicting module version/interface")
        if mid not in self.modules and len(self.modules)>=MAX_MODULES:
            raise ComposerError("module registry capacity")
        self.modules[mid]=rec
        return mid

    def node(self,nid):
        for row in self.nodes:
            if row["id"]==nid:return row
        raise ComposerError("unknown graph node")

    def add(self,mid,x=0,y=0,chip_id=None):
        if mid not in self.modules or len(self.nodes)>=MAX_NODES:
            raise ComposerError("unknown module or graph full")
        if chip_id is not None and (not isinstance(chip_id,str) or not CHIPID.fullmatch(chip_id)):
            raise ComposerError("invalid pinned chip identity")
        nid="node-"+uuid.uuid4().hex
        self.nodes.append({"id":nid,"module_id":mid,"x":_coord(x),"y":_coord(y),"chip_id":chip_id})
        return nid

    def move(self,nid,x,y):
        row=self.node(nid);row["x"]=_coord(x);row["y"]=_coord(y)

    def remove(self,nid):
        self.node(nid)
        self.nodes=[n for n in self.nodes if n["id"]!=nid]
        self.edges=[e for e in self.edges if nid not in (e["from"],e["to"])]

    def port(self,nid,direction,name):
        module=self.modules[self.node(nid)["module_id"]]
        for p in module[direction]:
            if p["name"]==name:return p
        raise ComposerError("unknown node port")

    def order(self):
        ids=[n["id"] for n in self.nodes]
        if len(set(ids))!=len(ids):raise ComposerError("duplicate graph node")
        incoming={n:0 for n in ids};following={n:set() for n in ids}
        for e in self.edges:
            if e["from"] not in incoming or e["to"] not in incoming:
                raise ComposerError("dangling graph connection")
            if e["to"] not in following[e["from"]]:
                following[e["from"]].add(e["to"]);incoming[e["to"]]+=1
        ready=sorted(n for n,d in incoming.items() if d==0);result=[]
        while ready:
            n=ready.pop(0);result.append(n)
            for nxt in sorted(following[n]):
                incoming[nxt]-=1
                if incoming[nxt]==0:ready.append(nxt);ready.sort()
        if len(result)!=len(ids):raise ComposerError("DataChip cycle prohibited")
        return result

    def connect(self,source,out,target,inp):
        if len(self.edges)>=MAX_EDGES or source==target:
            raise ComposerError("connection capacity or self-link")
        a=self.port(source,"outputs",out);b=self.port(target,"inputs",inp)
        if a["type"]!=b["type"]:
            raise ComposerError("incompatible typed ports: "+a["type"]+" / "+b["type"])
        row={"from":source,"out":out,"to":target,"in":inp}
        if row in self.edges or any(e["to"]==target and e["in"]==inp for e in self.edges):
            raise ComposerError("duplicate link or occupied input")
        self.edges.append(row)
        try:self.order()
        except Exception:
            self.edges.pop();raise
        return row

    def compile(self):
        if not self.nodes:raise ComposerError("cannot compile empty graph")
        ordered=self.order()
        for n in self.nodes:
            m=self.modules[n["module_id"]]
            for p in m["inputs"]:
                if p["required"] and not any(e["to"]==n["id"] and e["in"]==p["name"] for e in self.edges):
                    raise ComposerError("unconnected required input: "+m["name"]+" / "+p["name"])
        out={"schema":ASSEMBLY_SCHEMA,"owner_id":self.owner_id,"graph_id":self.graph_id,
             "name":self.name,"interfaces":[self.modules[k] for k in sorted({n["module_id"] for n in self.nodes})],
             "nodes":sorted(self.nodes,key=lambda n:n["id"]),
             "connections":sorted(self.edges,key=lambda e:(e["from"],e["to"],e["out"],e["in"])),
             "topological_order":ordered,"state":"COMPOSITION_ONLY",
             "security":{"execution_enabled":False,"rights_authorized":False,
                         "issuer_trusted":False,"licence_transferred":False,
                         "market_order_created":False,"deployment_approved":False,
                         "host_authentication_required":True}}
        if len(canonical(out))>MAX_DOCUMENT:raise ComposerError("oversized compilation")
        out["sha256"]=sha256(canonical(out)).hexdigest()
        return out

    def document(self):
        out={"schema":SCHEMA,"owner_id":self.owner_id,"graph_id":self.graph_id,"name":self.name,
             "modules":[self.modules[k] for k in sorted(self.modules)],
             "nodes":sorted(self.nodes,key=lambda n:n["id"]),
             "edges":sorted(self.edges,key=lambda e:(e["from"],e["to"],e["out"],e["in"])),
             "rights_authorized":False,"executable":False}
        if len(canonical(out))>MAX_DOCUMENT:raise ComposerError("draft exceeds size limit")
        out["sha256"]=sha256(canonical(out)).hexdigest()
        return out

    @classmethod
    def load(cls,obj,owner_id):
        required={"schema","owner_id","graph_id","name","modules","nodes","edges",
                  "rights_authorized","executable","sha256"}
        if not isinstance(obj,dict) or set(obj)!=required:
            raise ComposerError("unknown graph serialization")
        d=dict(obj);saved_hash=d.pop("sha256")
        if not isinstance(saved_hash,str) or sha256(canonical(d)).hexdigest()!=saved_hash:
            raise ComposerError("tampered graph document")
        if obj["owner_id"]!=owner_id or obj["schema"]!=SCHEMA:
            raise ComposerError("unrecognized wallet owner or graph format")
        if obj["rights_authorized"] is not False or obj["executable"] is not False:
            raise ComposerError("graph document attempts to grant authority")
        mods=obj["modules"];nodes=obj["nodes"];edges=obj["edges"]
        if not isinstance(mods,list) or len(mods)>MAX_MODULES or not isinstance(nodes,list) or len(nodes)>MAX_NODES or not isinstance(edges,list) or len(edges)>MAX_EDGES:
            raise ComposerError("graph limits exceeded")
        m={}
        for raw in mods:
            item=module_spec(raw)
            if item["module_id"] in m:raise ComposerError("repeated module")
            m[item["module_id"]]=item
        graph=cls(owner_id=owner_id,name=obj["name"],graph_id=obj["graph_id"],modules=m)
        for node in nodes:
            if not isinstance(node,dict) or set(node)!={"id","module_id","x","y","chip_id"}:
                raise ComposerError("invalid node")
            _id(node["id"])
            if not node["id"].startswith("node-") or node["module_id"] not in m:
                raise ComposerError("unrecognized node")
            chip_id=node["chip_id"]
            if chip_id is not None and (not isinstance(chip_id,str) or not CHIPID.fullmatch(chip_id)):
                raise ComposerError("invalid chip ID")
            graph.nodes.append({"id":node["id"],"module_id":node["module_id"],
                                "x":_coord(node["x"]),"y":_coord(node["y"]),"chip_id":chip_id})
        if len({n["id"] for n in graph.nodes})!=len(graph.nodes):
            raise ComposerError("duplicate node ID")
        if not all(isinstance(e,dict) and set(e)=={"from","out","to","in"} for e in edges):
            raise ComposerError("malformed connection")
        if len({tuple(e[k] for k in ("from","out","to","in")) for e in edges})!=len(edges):
            raise ComposerError("repeated connection")
        for e in edges:graph.connect(e["from"],e["out"],e["to"],e["in"])
        return graph

class GraphStore:
    """Local drafts in a separate wallet/composer directory. Never touches DCO DB."""
    def __init__(self,state,owner_id):
        self.owner_id=_id(owner_id)
        self.root=Path(state)/"wallet"/"composer"/"drafts"

    def path(self,graph_id):
        _id(graph_id)
        if not graph_id.startswith("graph-"):raise ComposerError("bad graph prefix")
        return self.root/(graph_id+".json")

    def save(self,graph):
        if graph.owner_id!=self.owner_id:raise ComposerError("wrong wallet owner")
        data=canonical(graph.document())+b"\n"
        if len(data)>MAX_DOCUMENT:raise ComposerError("oversized draft")
        self.root.mkdir(parents=True,exist_ok=True)
        path=self.path(graph.graph_id)
        if self.root.is_symlink() or path.is_symlink():
            raise ComposerError("unsafe draft destination")
        fd,tmp=tempfile.mkstemp(prefix=".assembly-",suffix=".tmp",dir=self.root)
        try:
            with os.fdopen(fd,"wb") as f:
                f.write(data);f.flush();os.fsync(f.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        return path

    def load(self,graph_id):
        p=self.path(graph_id)
        if not p.is_file() or p.is_symlink() or p.stat().st_size>MAX_DOCUMENT:
            raise ComposerError("missing or unsafe draft")
        try: doc=json.loads(p.read_text(encoding="utf-8"))
        except (ValueError,UnicodeError) as error:
            raise ComposerError("corrupt draft") from error
        graph=Graph.load(doc,self.owner_id)
        if graph.graph_id!=graph_id:raise ComposerError("inconsistent draft identity")
        return graph

    def list_drafts(self):
        if not self.root.is_dir() or self.root.is_symlink():return []
        result=[]
        for p in sorted(self.root.glob("graph-*.json")):
            try:
                g=self.load(p.stem)
                result.append({"id":g.graph_id,"name":g.name,"nodes":len(g.nodes)})
            except (ComposerError,OSError):
                continue
        return result
