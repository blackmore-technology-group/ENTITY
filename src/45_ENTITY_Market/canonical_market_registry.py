from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Any
import hashlib, json, re, sqlite3, textwrap, time

MARKET_SCHEMA="entity-economic-market-registry-v1"
MARKET_VERSION="1.0.0"

def now_ms()->int: return int(time.time()*1000)
def canon(v:Any)->bytes: return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def sha(v:Any)->str: return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else canon(v)).hexdigest()

def _token(v:str)->str:
    s=re.sub(r"[^A-Z0-9]+","-",str(v or "").upper()).strip("-")
    if not s: raise ValueError("non-empty canonical token required")
    return s

def _enum(v:str)->str:
    s=str(v or "").upper().strip()
    if not s or re.search(r"[^A-Z0-9_-]",s): raise ValueError("invalid canonical enum")
    return s

def _safe_symbol(v:str)->str:
    s=re.sub(r"[^A-Z0-9._-]+","-",str(v or "").upper()).strip("-._")
    if not s or len(s)>32: raise ValueError("display symbol must be 1-32 canonical characters")
    return s

def _namespace_candidate(manifest:dict)->str:
    explicit=str(manifest.get("market_namespace") or "").strip()
    if explicit: return _token(explicit)[:20]
    aliases=[str(x) for x in (manifest.get("aliases") or []) if str(x)]
    for alias in sorted(aliases,key=len):
        first=alias.split(".",1)[0]
        try:
            candidate=_token(first)
            if 2<=len(candidate)<=20: return candidate
        except ValueError: pass
    name=str(manifest.get("display_name") or "")
    words=[w for w in re.findall(r"[A-Za-z0-9]+",name)
           if w.upper() not in {"LIMITED","LTD","INC","INCORPORATED","CORP","CORPORATION","COMPANY","CO","LLC"}]
    if len(words)>=2:
        acr="".join(w[0] for w in words).upper()
        if 2<=len(acr)<=12: return acr
    compact="".join(words).upper()
    if compact: return compact[:20]
    return "ENTITY-"+str(manifest["entity_id"])[-8:].upper()

def canonical_instrument_id(issuer_entity_id:str,underlying_dco_id:str,rights_class:str,series:int)->str:
    s=int(series)
    if s<1: raise ValueError("series must be positive")
    return f"entity.instrument:v1:{issuer_entity_id}:{underlying_dco_id}:{_token(rights_class).lower()}:{s:06d}"

def canonical_listing_id(venue_id:str,instrument_id:str,series:int)->str:
    s=int(series)
    if s<1: raise ValueError("listing series must be positive")
    digest=sha({"venue_id":str(venue_id),"instrument_id":str(instrument_id)})[:24]
    return f"entity.listing:v1:{venue_id}:{digest}:{s:06d}"

def _simple_pdf(text:str,path:Path)->None:
    """Dependency-free human-readable PDF for portable instrument packages."""
    lines=[]
    for raw in text.splitlines():
        if not raw.strip(): lines.append(""); continue
        lines.extend(textwrap.wrap(raw,92,replace_whitespace=False,drop_whitespace=False) or [""])
    pages=[lines[i:i+52] for i in range(0,len(lines),52)] or [[]]
    objs=[]
    font_id=3+len(pages)*2
    kids=[]
    for idx,page in enumerate(pages):
        page_id=3+idx*2; content_id=page_id+1; kids.append(f"{page_id} 0 R")
        stream=["BT","/F1 9 Tf","48 760 Td","12 TL"]
        first=True
        for line in page:
            esc=line.replace("\\","\\\\").replace("(","\\(").replace(")","\\)")
            if first: stream.append(f"({esc}) Tj"); first=False
            else: stream.append(f"T* ({esc}) Tj")
        stream.append("ET")
        data="\n".join(stream).encode("latin-1","replace")
        objs.append((page_id,f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode()))
        objs.append((content_id,b"<< /Length "+str(len(data)).encode()+b" >>\nstream\n"+data+b"\nendstream"))
    objs.extend([
        (1,b"<< /Type /Catalog /Pages 2 0 R >>"),
        (2,f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>".encode()),
        (font_id,b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"),
    ])
    objs=sorted(objs,key=lambda x:x[0]); buf=bytearray(b"%PDF-1.4\n"); offsets={0:0}
    for oid,data in objs:
        offsets[oid]=len(buf); buf.extend(f"{oid} 0 obj\n".encode()); buf.extend(data); buf.extend(b"\nendobj\n")
    xref=len(buf); max_id=max(offsets)
    buf.extend(f"xref\n0 {max_id+1}\n".encode()); buf.extend(b"0000000000 65535 f \n")
    for i in range(1,max_id+1): buf.extend(f"{offsets.get(i,0):010d} 00000 n \n".encode())
    buf.extend(f"trailer\n<< /Size {max_id+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(buf)

class EntityEconomicMarketRegistry:
    """Universal multi-issuer market registry above the EEP execution engine.

    ENTITY owns protocol/registry rules, never listed assets. Any verified ENTITY
    controller may issue instruments over its own DCOs under the same rules.
    """

    def __init__(self,state_dir:str|Path,identity,fabric,exchange,rights_passports,global_passports):
        self.state=Path(state_dir); self.identity=identity; self.fabric=fabric; self.exchange=exchange
        self.rights=rights_passports; self.global_passports=global_passports
        self.path=self.state/"entity_market_registry.sqlite"
        self._init()

    @contextmanager
    def _db(self):
        db=sqlite3.connect(self.path); db.row_factory=sqlite3.Row
        try:
            yield db; db.commit()
        except Exception:
            db.rollback(); raise
        finally: db.close()

    def _init(self):
        with self._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS issuer_namespaces(
              namespace TEXT PRIMARY KEY, issuer_entity_id TEXT NOT NULL UNIQUE,
              display_name TEXT NOT NULL, created_at_ms INTEGER NOT NULL,
              signature_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS instrument_packages(
              instrument_id TEXT PRIMARY KEY, issuer_entity_id TEXT NOT NULL,
              issuer_namespace TEXT NOT NULL, underlying_dco_id TEXT NOT NULL,
              instrument_name TEXT NOT NULL, display_symbol TEXT NOT NULL,
              market_identifier TEXT NOT NULL UNIQUE, instrument_class TEXT NOT NULL,
              rights_class TEXT NOT NULL, series INTEGER NOT NULL,
              fungibility TEXT NOT NULL, divisibility INTEGER NOT NULL, supply INTEGER NOT NULL,
              rights_passport_id TEXT NOT NULL, global_passport_id TEXT NOT NULL,
              jurisdiction TEXT NOT NULL, transfer_rules_json TEXT NOT NULL,
              economic_terms_json TEXT NOT NULL, royalty_terms_json TEXT NOT NULL,
              buyer_receives_json TEXT NOT NULL, buyer_does_not_receive_json TEXT NOT NULL,
              evidence_refs_json TEXT NOT NULL, status TEXT NOT NULL,
              created_at_ms INTEGER NOT NULL, signature_json TEXT NOT NULL,
              UNIQUE(issuer_entity_id,underlying_dco_id,rights_class,series),
              UNIQUE(issuer_entity_id,display_symbol));
            CREATE TABLE IF NOT EXISTS listing_packages(
              listing_id TEXT PRIMARY KEY, instrument_id TEXT NOT NULL,
              venue_id TEXT NOT NULL, market_id TEXT NOT NULL,
              display_symbol TEXT NOT NULL, quote_unit TEXT NOT NULL,
              trade_mode TEXT NOT NULL, settlement_method TEXT NOT NULL,
              minimum_quantity INTEGER NOT NULL, quantity_precision INTEGER NOT NULL,
              price_precision INTEGER NOT NULL, pricing_method TEXT NOT NULL,
              listing_information_sha256 TEXT NOT NULL, machine_manifest_sha256 TEXT NOT NULL,
              status TEXT NOT NULL, listed_at_ms INTEGER NOT NULL,
              signature_json TEXT NOT NULL,
              UNIQUE(venue_id,instrument_id,listing_id));
            CREATE TABLE IF NOT EXISTS listing_information(
              listing_id TEXT PRIMARY KEY, information_json TEXT NOT NULL,
              information_markdown TEXT NOT NULL, created_at_ms INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_market_symbol ON instrument_packages(issuer_namespace,display_symbol);
            """)

    def suggest_namespace(self,issuer_entity_id:str)->dict:
        issuer=str(issuer_entity_id); manifest=self.identity.load_manifest(issuer)
        base=_namespace_candidate(manifest)
        if len(base)>20: base=base[:20]
        candidate=base
        with self._db() as db:
            existing=db.execute("SELECT namespace FROM issuer_namespaces WHERE issuer_entity_id=?",(issuer,)).fetchone()
            if existing:
                return {"namespace":existing["namespace"],"registered":True,"available":True}
            n=1
            while True:
                conflict=db.execute("SELECT issuer_entity_id FROM issuer_namespaces WHERE namespace=?",(candidate,)).fetchone()
                if not conflict:
                    return {"namespace":candidate,"registered":False,"available":True}
                n+=1; suffix="-"+str(n); candidate=base[:20-len(suffix)]+suffix

    def ensure_namespace(self,issuer_entity_id:str,preferred:str|None=None)->dict:
        issuer=str(issuer_entity_id); manifest=self.identity.load_manifest(issuer)
        with self._db() as db:
            prior=db.execute("SELECT * FROM issuer_namespaces WHERE issuer_entity_id=?",(issuer,)).fetchone()
            if prior: return dict(prior) | {"signature":json.loads(prior["signature_json"])}
        base=_token(preferred) if preferred else _namespace_candidate(manifest)
        if len(base)>20: base=base[:20]
        candidate=base
        with self._db() as db:
            n=1
            while True:
                conflict=db.execute("SELECT issuer_entity_id FROM issuer_namespaces WHERE namespace=?",(candidate,)).fetchone()
                if not conflict or conflict["issuer_entity_id"]==issuer: break
                n+=1; suffix="-"+str(n); candidate=base[:20-len(suffix)]+suffix
            body={"schema":"entity-market-issuer-namespace-v1","namespace":candidate,
                  "issuer_entity_id":issuer,"display_name":str(manifest.get("display_name") or issuer),
                  "created_at_ms":now_ms(),"namespace_is_alias_not_authority":True}
            sig=self.identity.sign(issuer,body)
            db.execute("INSERT INTO issuer_namespaces VALUES(?,?,?,?,?)",(
                candidate,issuer,body["display_name"],body["created_at_ms"],json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)

    def _verify_passports(self,issuer:str,dco_id:str,rights_passport_id:str,global_passport_id:str)->tuple[dict,dict]:
        rp=self.rights.get(str(rights_passport_id)); gp=self.global_passports.get(str(global_passport_id))
        if rp["object_id"]!=dco_id or rp["controller_entity_id"]!=issuer:
            raise PermissionError("Rights Passport must bind issuer-controlled underlying DCO")
        if gp["object_id"]!=dco_id or gp["controller_entity_id"]!=issuer:
            raise PermissionError("Global Passport must bind issuer-controlled underlying DCO")
        if gp["rights_passport_id"]!=rp["passport_id"]:
            raise ValueError("Global Passport does not bind supplied Rights Passport")
        if not self.rights.verify(rp).get("valid"): raise ValueError("Rights Passport verification failed")
        if not self.global_passports.verify(gp).get("valid"): raise ValueError("Global Passport verification failed")
        return rp,gp

    def create_instrument(self,issuer_entity_id:str,underlying_dco_id:str,*,instrument_name:str,
                          display_symbol:str,instrument_class:str,rights_class:str,rights:dict,
                          supply:int,rights_passport_id:str,global_passport_id:str,
                          settlement_currency:str,jurisdiction:str,series:int=1,
                          fungibility:str="FUNGIBLE",divisibility:int=0,transferable:bool=False,
                          duration_ms:int|None=None,delivery_mode:str="ENTITLEMENT",
                          transfer_rules:dict|None=None,economic_terms:dict|None=None,
                          royalty_terms:dict|None=None,buyer_receives:list[str]|None=None,
                          buyer_does_not_receive:list[str]|None=None,evidence_refs:list[str]|None=None,
                          namespace:str|None=None)->dict:
        issuer=str(issuer_entity_id); dco=str(underlying_dco_id)
        obj=self.fabric.get_object(dco)
        if obj["controller_entity_id"]!=issuer:
            raise PermissionError("only the controlled DCO issuer may create an instrument")
        if not (obj.get("descriptor") or {}).get("digital_commodity"):
            raise ValueError("underlying object must be a Digital Commodity Object")
        rp,gp=self._verify_passports(issuer,dco,rights_passport_id,global_passport_id)
        ns=self.ensure_namespace(issuer,namespace)
        symbol=_safe_symbol(display_symbol); rc=_token(rights_class); series=int(series)
        instrument_id=canonical_instrument_id(issuer,dco,rc,series)
        market_identifier=f"{ns['namespace']}:{symbol}"
        supply=int(supply); div=int(divisibility)
        if supply<1: raise ValueError("positive supply required")
        if div<0 or div>9: raise ValueError("divisibility must be between 0 and 9")
        fung=_token(fungibility)
        if fung not in {"FUNGIBLE","NON-FUNGIBLE","SERIES-FUNGIBLE"}: raise ValueError("unsupported fungibility")
        actions=sorted({_token(a) for a in (rights.get("actions") or [])})
        if not actions: raise ValueError("instrument rights actions required")
        allowed=set(); prohibited=set()
        for rule in rp.get("rights") or []:
            effect=str(rule.get("effect") or "").upper()
            rule_actions={_token(a) for a in (rule.get("actions") or [])}
            if effect=="ALLOW": allowed.update(rule_actions)
            elif effect=="PROHIBIT": prohibited.update(rule_actions)
        requested=set(actions)
        if requested & prohibited:
            raise PermissionError("instrument requests action prohibited by Rights Passport")
        if not requested.issubset(allowed):
            raise PermissionError("instrument actions exceed Rights Passport")
        rights_doc={**dict(rights),"actions":actions,
                    "rights_passport_id":rp["passport_id"],"global_passport_id":gp["passport_id"],
                    "rights_class":rc,"market_identifier":market_identifier}
        eep_body={"schema":"entity-eep-instrument-v1","instrument_id":instrument_id,"issuer":issuer,
                  "underlying_object_id":dco,"instrument_class":_enum(instrument_class),
                  "rights":rights_doc,"total_units":supply,"transferable":bool(transferable),
                  "duration_ms":int(duration_ms) if duration_ms is not None else None,
                  "settlement_currency":_enum(settlement_currency),"delivery_mode":_enum(delivery_mode),
                  "status":"ACTIVE","created_at_ms":now_ms(),"bytes_are_not_the_traded_scarcity":True}
        sig=self.identity.sign(issuer,eep_body)
        self.exchange.submit_signed_instrument(eep_body,sig)
        package={"schema":"entity-economic-instrument-package-v1","instrument_id":instrument_id,
                 "issuer_entity_id":issuer,"issuer_namespace":ns["namespace"],"underlying_dco_id":dco,
                 "instrument_name":str(instrument_name),"display_symbol":symbol,
                 "market_identifier":market_identifier,"instrument_class":eep_body["instrument_class"],
                 "rights_class":rc,"series":series,"fungibility":fung,"divisibility":div,"supply":supply,
                 "rights_passport_id":rp["passport_id"],"global_passport_id":gp["passport_id"],
                 "jurisdiction":str(jurisdiction).upper(),"transfer_rules":dict(transfer_rules or {}),
                 "economic_terms":dict(economic_terms or {}),"royalty_terms":dict(royalty_terms or {}),
                 "buyer_receives":[str(x) for x in (buyer_receives or [])],
                 "buyer_does_not_receive":[str(x) for x in (buyer_does_not_receive or [])],
                 "evidence_refs":sorted({str(x) for x in (evidence_refs or [])}),
                 "status":"ACTIVE","created_at_ms":eep_body["created_at_ms"],
                 "entity_owns_protocol_not_asset":True,"namespace_is_alias_not_authority":True,
                 "canonical_identity_is_instrument_id":True}
        psig=self.identity.sign(issuer,package)
        with self._db() as db:
            db.execute("""INSERT INTO instrument_packages VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(
                instrument_id,issuer,ns["namespace"],dco,package["instrument_name"],symbol,market_identifier,
                package["instrument_class"],rc,series,fung,div,supply,rp["passport_id"],gp["passport_id"],
                package["jurisdiction"],json.dumps(package["transfer_rules"],sort_keys=True),
                json.dumps(package["economic_terms"],sort_keys=True),json.dumps(package["royalty_terms"],sort_keys=True),
                json.dumps(package["buyer_receives"],sort_keys=True),json.dumps(package["buyer_does_not_receive"],sort_keys=True),
                json.dumps(package["evidence_refs"],sort_keys=True),"ACTIVE",package["created_at_ms"],json.dumps(psig,sort_keys=True)))
        return dict(package,signature=psig,eep_instrument=dict(eep_body,signature=sig))

    def instrument(self,instrument_id:str)->dict:
        with self._db() as db:
            r=db.execute("SELECT * FROM instrument_packages WHERE instrument_id=?",(str(instrument_id),)).fetchone()
        if not r: raise KeyError("instrument package not found")
        d=dict(r)
        for src,dst in [("transfer_rules_json","transfer_rules"),("economic_terms_json","economic_terms"),
                        ("royalty_terms_json","royalty_terms"),("buyer_receives_json","buyer_receives"),
                        ("buyer_does_not_receive_json","buyer_does_not_receive"),("evidence_refs_json","evidence_refs")]:
            d[dst]=json.loads(d.pop(src) or ("[]" if "buyer_" in dst or dst=="evidence_refs" else "{}"))
        d["signature"]=json.loads(d.pop("signature_json")); return d

    def resolve_symbol(self,issuer_namespace:str,display_symbol:str)->dict:
        ns=_token(issuer_namespace); sym=_safe_symbol(display_symbol)
        with self._db() as db:
            r=db.execute("""SELECT instrument_id FROM instrument_packages
                            WHERE issuer_namespace=? AND display_symbol=? AND status='ACTIVE'""",(ns,sym)).fetchone()
        if not r: raise KeyError("active market identifier not found")
        return self.instrument(r["instrument_id"])

    def _information(self,instrument:dict,listing:dict,asset:dict,issuer_manifest:dict)->tuple[dict,str]:
        info={
            "schema":"entity-listing-information-sheet-v1",
            "what_is_this":f"{instrument['market_identifier']} represents {instrument['instrument_name']}.",
            "instrument_name":instrument["instrument_name"],"display_symbol":instrument["display_symbol"],
            "market_identifier":instrument["market_identifier"],"instrument_id":instrument["instrument_id"],
            "issuer":str(issuer_manifest.get("display_name") or instrument["issuer_entity_id"]),
            "issuer_entity_id":instrument["issuer_entity_id"],"underlying_dco_id":instrument["underlying_dco_id"],
            "asset_name":asset["title"],"asset_type":asset["object_type"],
            "instrument_class":instrument["instrument_class"],"rights_class":instrument["rights_class"],
            "buyer_receives":instrument["buyer_receives"],
            "buyer_does_not_receive":instrument["buyer_does_not_receive"],
            "supply":instrument["supply"],"divisibility":instrument["divisibility"],
            "fungibility":instrument["fungibility"],"jurisdiction":instrument["jurisdiction"],
            "transfer_rules":instrument["transfer_rules"],"economic_terms":instrument["economic_terms"],
            "royalty_terms":instrument["royalty_terms"],"rights_passport_id":instrument["rights_passport_id"],
            "global_passport_id":instrument["global_passport_id"],"evidence_refs":instrument["evidence_refs"],
            "listing_id":listing["listing_id"],"venue_id":listing["venue_id"],"market_id":listing["market_id"],
            "quote_unit":listing["quote_unit"],"trade_mode":listing["trade_mode"],
            "settlement_method":listing["settlement_method"],"minimum_quantity":listing["minimum_quantity"],
            "quantity_precision":listing["quantity_precision"],"price_precision":listing["price_precision"],
            "pricing_method":listing["pricing_method"],"status":listing["status"],
            "instrument_created_at_ms":instrument["created_at_ms"],"listed_at_ms":listing["listed_at_ms"],
            "sheet_does_not_replace_rights_passport":True,
            "external_publication_does_not_create_new_instrument":True,
        }
        md=f"""# ENTITY Listing Information Sheet

## WHAT IS THIS?

**{info['market_identifier']} — {info['instrument_name']}**

Underlying asset: **{info['asset_name']}**  
Issuer: **{info['issuer']}**  
Canonical Instrument ID: `{info['instrument_id']}`  
Canonical Listing ID: `{info['listing_id']}`

### Purchasing this instrument grants

{chr(10).join('- '+x for x in info['buyer_receives']) or '- See Rights Passport.'}

### Purchasing this instrument does NOT grant

{chr(10).join('- '+x for x in info['buyer_does_not_receive']) or '- No rights beyond the Rights Passport.'}

## Rights and market terms

- Instrument class: {info['instrument_class']}
- Rights class: {info['rights_class']}
- Supply: {info['supply']}
- Divisibility: {info['divisibility']}
- Fungibility: {info['fungibility']}
- Jurisdiction: {info['jurisdiction']}
- Quote unit: {info['quote_unit']}
- Trade mode: {info['trade_mode']}
- Settlement: {info['settlement_method']}
- Minimum quantity: {info['minimum_quantity']}
- Pricing method: {info['pricing_method']}

## Canonical references

- Issuer ENTITY ID: `{info['issuer_entity_id']}`
- Underlying DCO: `{info['underlying_dco_id']}`
- Rights Passport: `{info['rights_passport_id']}`
- Global Passport: `{info['global_passport_id']}`
- Venue: `{info['venue_id']}`

This sheet is a buyer-facing disclosure layer. It does **not** replace the Rights Passport, Global Passport, canonical instrument, or canonical listing record.
"""
        info["verification_hash"]=sha(info)
        return info,md

    def create_listing(self,issuer_entity_id:str,instrument_id:str,venue_id:str,*,market_id:str,
                       quote_unit:str,trade_mode:str="ORDER_BOOK",settlement_method:str="PAYMENT_VERSUS_RIGHT",
                       minimum_quantity:int=1,quantity_precision:int=0,price_precision:int=0,
                       pricing_method:str="ORDER_BOOK",listing_series:int=1,tick_size:int=1)->dict:
        instrument=self.instrument(instrument_id); issuer=str(issuer_entity_id)
        if instrument["issuer_entity_id"]!=issuer: raise PermissionError("instrument issuer required")
        listing_id=canonical_listing_id(str(venue_id),instrument_id,int(listing_series))
        draft={"listing_id":listing_id,"venue_id":str(venue_id),"market_id":str(market_id),
               "quote_unit":_enum(quote_unit),"trade_mode":_enum(trade_mode),
               "settlement_method":_enum(settlement_method),"minimum_quantity":int(minimum_quantity),
               "quantity_precision":int(quantity_precision),"price_precision":int(price_precision),
               "pricing_method":_enum(pricing_method),"status":"ACTIVE","listed_at_ms":now_ms()}
        if draft["minimum_quantity"]<1: raise ValueError("minimum quantity must be positive")
        asset=self.fabric.get_object(instrument["underlying_dco_id"])
        manifest=self.identity.load_manifest(issuer)
        info,md=self._information(instrument,draft,asset,manifest)
        info_hash=sha(info)
        machine={"protocol":"ENTITY-INSTRUMENT-1","instrument_symbol":instrument["display_symbol"],
                 "market_identifier":instrument["market_identifier"],"instrument_name":instrument["instrument_name"],
                 "instrument_id":instrument_id,"issuer_entity_id":issuer,
                 "underlying_dco_id":instrument["underlying_dco_id"],"listing_id":listing_id,
                 "rights_passport":instrument["rights_passport_id"],"global_passport":instrument["global_passport_id"],
                 "listing_information_sha256":info_hash}
        machine["verification_hash"]=sha(machine); machine_hash=sha(machine)
        disclosure=self.exchange.publish_disclosure(str(venue_id),instrument_id,issuer,"LISTING_INFORMATION",machine_hash)
        listing_body={"schema":"entity-eep-listing-v1","listing_id":listing_id,"venue_id":str(venue_id),
                      "instrument_id":instrument_id,"lister":issuer,"min_lot":draft["minimum_quantity"],
                      "tick_size":int(tick_size),"disclosure_sha256":machine_hash,
                      "status":"ACTIVE","created_at_ms":draft["listed_at_ms"]}
        lsig=self.identity.sign(issuer,listing_body)
        self.exchange.submit_signed_listing(listing_body,lsig)
        package={**draft,"schema":"entity-market-listing-package-v1","instrument_id":instrument_id,
                 "display_symbol":instrument["display_symbol"],"listing_information_sha256":info_hash,
                 "machine_manifest_sha256":machine_hash}
        psig=self.identity.sign(issuer,package)
        with self._db() as db:
            db.execute("INSERT INTO listing_packages VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(
                listing_id,instrument_id,str(venue_id),draft["market_id"],instrument["display_symbol"],
                draft["quote_unit"],draft["trade_mode"],draft["settlement_method"],draft["minimum_quantity"],
                draft["quantity_precision"],draft["price_precision"],draft["pricing_method"],info_hash,machine_hash,
                "ACTIVE",draft["listed_at_ms"],json.dumps(psig,sort_keys=True)))
            db.execute("INSERT INTO listing_information VALUES(?,?,?,?)",(
                listing_id,json.dumps({"information":info,"machine_manifest":machine},sort_keys=True),
                md,draft["listed_at_ms"]))
        return dict(package,signature=psig,information=info,machine_manifest=machine,
                    eep_listing=dict(listing_body,signature=lsig),disclosure=disclosure)

    def listing(self,listing_id:str)->dict:
        with self._db() as db:
            r=db.execute("SELECT * FROM listing_packages WHERE listing_id=?",(str(listing_id),)).fetchone()
            i=db.execute("SELECT * FROM listing_information WHERE listing_id=?",(str(listing_id),)).fetchone()
        if not r or not i: raise KeyError("listing package not found")
        payload=json.loads(i["information_json"])
        return dict(r) | {"signature":json.loads(r["signature_json"]),
                          "information":payload["information"],"machine_manifest":payload["machine_manifest"],
                          "information_markdown":i["information_markdown"]}

    def export_portable_package(self,listing_id:str,destination:str|Path)->dict:
        listing=self.listing(listing_id); instrument=self.instrument(listing["instrument_id"])
        rp=self.rights.get(instrument["rights_passport_id"]); gp=self.global_passports.get(instrument["global_passport_id"])
        asset=self.fabric.get_object(instrument["underlying_dco_id"])
        out=Path(destination); out.mkdir(parents=True,exist_ok=True)
        files={
            "LISTING_INFORMATION.md":listing["information_markdown"].encode(),
            "instrument.json":json.dumps(instrument,indent=2,sort_keys=True).encode(),
            "entity-instrument.json":json.dumps(listing["machine_manifest"],indent=2,sort_keys=True).encode(),
            "listing.json":json.dumps({k:v for k,v in listing.items() if k not in {"information_markdown"}},indent=2,sort_keys=True,default=str).encode(),
            "rights-passport.json":json.dumps(rp,indent=2,sort_keys=True).encode(),
            "global-passport.json":json.dumps(gp,indent=2,sort_keys=True).encode(),
            "provenance.json":json.dumps({"underlying_dco":asset,"evidence_refs":instrument["evidence_refs"]},indent=2,sort_keys=True).encode(),
        }
        for name,data in files.items(): (out/name).write_bytes(data)
        _simple_pdf(listing["information_markdown"],out/"LISTING_INFORMATION.pdf")
        verification={"schema":"entity-portable-instrument-verification-v1","instrument_id":instrument["instrument_id"],
                      "listing_id":listing_id,"market_identifier":instrument["market_identifier"],
                      "canonical_identity_is_instrument_id":True,
                      "external_publication_does_not_create_new_instrument":True,
                      "manifest_sha256":listing["machine_manifest_sha256"]}
        (out/"verification.json").write_text(json.dumps(verification,indent=2,sort_keys=True),encoding="utf-8")
        names=sorted([p for p in out.iterdir() if p.is_file() and p.name!="SHA256SUMS"])
        sums="\n".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in names)+"\n"
        (out/"SHA256SUMS").write_text(sums,encoding="ascii")
        badge=f"[ENTITY VERIFIED | {instrument['market_identifier']}]"
        (out/"ENTITY_INSTRUMENT.md").write_text(
            f"# {instrument['instrument_name']}\n\n{badge}\n\nInstrument: `{instrument['instrument_id']}`\n\n"
            f"Underlying DCO: `{instrument['underlying_dco_id']}`\n\nIssuer: `{instrument['issuer_entity_id']}`\n\n"
            f"Listing: `{listing_id}`\n\nRights Passport: `{instrument['rights_passport_id']}`\n\n"
            f"Global Passport: `{instrument['global_passport_id']}`\n\nManifest SHA-256: `{listing['machine_manifest_sha256']}`\n",
            encoding="utf-8")
        return {"schema":"entity-portable-instrument-package-v1","destination":str(out),
                "instrument_id":instrument["instrument_id"],"listing_id":listing_id,
                "market_identifier":instrument["market_identifier"],
                "files":sorted(p.name for p in out.iterdir() if p.is_file())}

    def issuer_instruments(self,issuer_entity_id:str,*,include_withdrawn:bool=False)->list[dict]:
        sql="SELECT instrument_id FROM instrument_packages WHERE issuer_entity_id=?"
        args=[str(issuer_entity_id)]
        if not include_withdrawn: sql+=" AND status='ACTIVE'"
        sql+=" ORDER BY created_at_ms,instrument_id"
        with self._db() as db: ids=[r["instrument_id"] for r in db.execute(sql,args)]
        return [self.instrument(i) for i in ids]

    def instrument_listings(self,instrument_id:str,*,active_only:bool=True)->list[dict]:
        sql="SELECT listing_id FROM listing_packages WHERE instrument_id=?"
        args=[str(instrument_id)]
        if active_only: sql+=" AND status='ACTIVE'"
        sql+=" ORDER BY listed_at_ms,listing_id"
        with self._db() as db: ids=[r["listing_id"] for r in db.execute(sql,args)]
        return [self.listing(i) for i in ids]

    def active_market(self)->list[dict]:
        with self._db() as db:
            rows=db.execute("""SELECT l.*,i.instrument_name,i.market_identifier,i.issuer_entity_id,
                                      i.underlying_dco_id,i.rights_class,i.instrument_class
                               FROM listing_packages l JOIN instrument_packages i ON i.instrument_id=l.instrument_id
                               WHERE l.status='ACTIVE' AND i.status='ACTIVE'
                               ORDER BY i.market_identifier,l.listed_at_ms""").fetchall()
        return [dict(r) for r in rows]

    def status(self)->dict:
        with self._db() as db:
            counts={t:int(db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
                    for t in ("issuer_namespaces","instrument_packages","listing_packages","listing_information")}
        return {"schema":MARKET_SCHEMA,"version":MARKET_VERSION,"multi_issuer":True,
                "entity_owns_protocol_not_assets":True,"canonical_instrument_identity":True,
                "symbols_are_non_authoritative_aliases":True,"listing_information_required":True,
                "portable_publication_supported":True,"protocol_tax_bps":0,
                "cryptocurrency_required":False,"counts":counts}
