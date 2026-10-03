from __future__ import annotations
from pathlib import Path
from typing import Iterable
import hashlib,json,shutil,sqlite3,time

def now_ms()->int: return int(time.time()*1000)
def canon(v)->bytes: return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def sha(v)->str: return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else canon(v)).hexdigest()

class PrelaunchEconomicWithdrawal:
    """Fail-closed application migration for unused prelaunch economic experiments.

    This does not add an EEP wire primitive or rewrite historical signed records.
    It is only valid when the targeted instruments have never entered real market
    activity and all non-issuer balances are proven internal treasury reserves.
    """

    def __init__(self,state_dir:str|Path,identity):
        self.state=Path(state_dir); self.identity=identity
        self.eep=self.state/"entity_v3_exchange.sqlite"
        self.eopp=self.state/"entity_v3_economic_participation.sqlite"
        self.factory=self.state/"dco_factory"/"entity_dco_factory.sqlite"
        self.audit_dir=self.state/"economic_migrations"; self.audit_dir.mkdir(parents=True,exist_ok=True)

    @staticmethod
    def _db(path:Path):
        db=sqlite3.connect(path); db.row_factory=sqlite3.Row; return db

    def audit(self,object_ids:Iterable[str],dco_ids:Iterable[str]=())->dict:
        object_ids=sorted({str(x) for x in object_ids}); dco_ids=sorted({str(x) for x in dco_ids})
        if not object_ids: raise ValueError("at least one underlying object_id required")
        if not self.eep.exists(): raise FileNotFoundError(self.eep)
        db=self._db(self.eep)
        try:
            marks=",".join("?" for _ in object_ids)
            instruments=[dict(r) for r in db.execute(
                f"SELECT * FROM instruments WHERE underlying_object_id IN ({marks}) ORDER BY instrument_id",object_ids)]
            if not instruments: raise ValueError("no economic instruments found for selected objects")
            ids=[r["instrument_id"] for r in instruments]; q=",".join("?" for _ in ids)
            activity={}
            for table in ("orders","trades","entitlements","usage"):
                activity[table]=int(db.execute(f"SELECT COUNT(*) FROM {table} WHERE instrument_id IN ({q})",ids).fetchone()[0])
            trade_ids=[r["trade_id"] for r in db.execute(f"SELECT trade_id FROM trades WHERE instrument_id IN ({q})",ids)]
            activity["clearing"]=0 if not trade_ids else int(db.execute(
                f"SELECT COUNT(*) FROM clearing WHERE trade_id IN ({','.join('?' for _ in trade_ids)})",trade_ids).fetchone()[0])
            balances=[dict(r) for r in db.execute(
                f"""SELECT b.instrument_id,b.holder,b.units,i.issuer
                    FROM balances b JOIN instruments i ON i.instrument_id=b.instrument_id
                    WHERE b.instrument_id IN ({q}) AND b.units>0 ORDER BY b.instrument_id,b.holder""",ids)]
            listings=int(db.execute(f"SELECT COUNT(*) FROM listings WHERE instrument_id IN ({q}) AND status='ACTIVE'",ids).fetchone()[0])
        finally: db.close()

        reserve_by_instrument={}; economic_events=0
        if self.eopp.exists():
            ep=self._db(self.eopp)
            try:
                iq=",".join("?" for _ in ids)
                economic_events=int(ep.execute(
                    f"SELECT COUNT(*) FROM economic_events WHERE instrument_id IN ({iq})",ids).fetchone()[0])
                rows=ep.execute(f"""SELECT r.instrument_id,r.units,r.treasury_entity_id,t.owner_entity_id
                                    FROM reserve_allocations r
                                    JOIN participation_policies p ON p.policy_id=r.policy_id
                                    JOIN treasuries t ON t.treasury_id=p.treasury_id
                                    WHERE r.instrument_id IN ({iq})""",ids).fetchall()
                reserve_by_instrument={r["instrument_id"]:dict(r) for r in rows}
            finally: ep.close()

        external=[]
        for b in balances:
            if b["holder"]==b["issuer"]: continue
            reserve=reserve_by_instrument.get(b["instrument_id"])
            if not reserve or reserve["owner_entity_id"]!=b["issuer"] or reserve["treasury_entity_id"]!=b["holder"] or int(reserve["units"])!=int(b["units"]):
                external.append(b)
        safe=not any(activity.values()) and economic_events==0 and not external
        return {
            "schema":"entity-prelaunch-economic-withdrawal-audit-v1",
            "object_ids":object_ids,"dco_ids":dco_ids,
            "instrument_ids":ids,"instrument_count":len(ids),"active_listing_count":listings,
            "activity_counts":activity,"economic_event_count":economic_events,
            "positive_balances":balances,"internal_reserves":reserve_by_instrument,
            "external_or_unexplained_balances":external,
            "safe_to_withdraw":safe,
            "requires_zero_market_history":True,
            "history_rewrite_prohibited":True,
        }

    def apply(self,object_ids:Iterable[str],dco_ids:Iterable[str],reason:str)->dict:
        reason=str(reason).strip()
        if not reason: raise ValueError("withdrawal reason required")
        audit=self.audit(object_ids,dco_ids)
        if not audit["safe_to_withdraw"]:
            raise RuntimeError("prelaunch withdrawal refused: economic activity or external holdings exist")
        ids=audit["instrument_ids"]; issuers=sorted({b["issuer"] for b in audit["positive_balances"]})
        if not issuers:
            db=self._db(self.eep)
            try:
                q=",".join("?" for _ in ids)
                issuers=sorted({r["issuer"] for r in db.execute(f"SELECT issuer FROM instruments WHERE instrument_id IN ({q})",ids)})
            finally: db.close()
        for issuer in issuers: self.identity.load_manifest(issuer)

        created=now_ms()
        body={"schema":"entity-prelaunch-economic-withdrawal-v1","reason":reason,
              "object_ids":audit["object_ids"],"dco_ids":audit["dco_ids"],"instrument_ids":ids,
              "audit_sha256":sha(audit),"created_at_ms":created,
              "no_orders":audit["activity_counts"]["orders"]==0,
              "no_trades":audit["activity_counts"]["trades"]==0,
              "no_entitlements":audit["activity_counts"]["entitlements"]==0,
              "no_usage":audit["activity_counts"]["usage"]==0,
              "no_economic_events":audit["economic_event_count"]==0,
              "no_external_holders":not audit["external_or_unexplained_balances"],
              "eep_wire_protocol_changed":False,"historical_records_deleted":False}
        evidence=sha(body)
        signatures=[self.identity.sign(issuer,body) for issuer in issuers]

        backups={}
        for p in (self.eep,self.eopp,self.factory):
            if p.exists():
                dst=self.audit_dir/f"{p.name}.{created}.bak"; shutil.copy2(p,dst); backups[str(p)]=str(dst)
        try:
            db=self._db(self.eep)
            db.execute("BEGIN IMMEDIATE")
            q=",".join("?" for _ in ids)
            db.execute(f"UPDATE instruments SET status='WITHDRAWN' WHERE instrument_id IN ({q}) AND status='ACTIVE'",ids)
            db.execute(f"UPDATE listings SET status='WITHDRAWN' WHERE instrument_id IN ({q}) AND status='ACTIVE'",ids)
            for iid,reserve in audit["internal_reserves"].items():
                issuer=next(r["issuer"] for r in audit["positive_balances"] if r["instrument_id"]==iid)
                holder=reserve["treasury_entity_id"]; units=int(reserve["units"])
                db.execute("UPDATE balances SET units=units-? WHERE instrument_id=? AND holder=?",(units,iid,holder))
                db.execute("""INSERT INTO balances(instrument_id,holder,units) VALUES(?,?,?)
                              ON CONFLICT(instrument_id,holder) DO UPDATE SET units=units+excluded.units""",(iid,issuer,units))
            db.commit(); db.close()

            if self.eopp.exists():
                ep=self._db(self.eopp); ep.execute("BEGIN IMMEDIATE")
                ep.execute("""CREATE TABLE IF NOT EXISTS participation_policy_withdrawals(
                              withdrawal_id TEXT PRIMARY KEY, policy_id TEXT NOT NULL UNIQUE,
                              instrument_id TEXT NOT NULL, originator_entity_id TEXT NOT NULL,
                              reason TEXT NOT NULL, evidence_sha256 TEXT, created_at_ms INTEGER NOT NULL,
                              signature_json TEXT NOT NULL)""")
                iq=",".join("?" for _ in ids)
                policies=ep.execute(f"""SELECT * FROM participation_policies
                                       WHERE instrument_id IN ({iq}) AND status='ACTIVE'
                                       ORDER BY instrument_id,version""",ids).fetchall()
                for policy in policies:
                    withdrawal_id="opw3-"+sha({"policy_id":policy["policy_id"],"evidence":evidence})[:24]
                    wbody={"schema":"entity-v3-participation-policy-withdrawal-v1",
                           "withdrawal_id":withdrawal_id,"policy_id":policy["policy_id"],
                           "instrument_id":policy["instrument_id"],
                           "originator_entity_id":policy["originator_entity_id"],
                           "reason":reason,"evidence_sha256":evidence,"created_at_ms":created,
                           "historical_obligations_and_reserves_preserved":True,
                           "no_retroactive_economic_change":True,"protocol_tax_bps":0}
                    wsig=self.identity.sign(policy["originator_entity_id"],wbody)
                    ep.execute("""INSERT OR IGNORE INTO participation_policy_withdrawals
                                  VALUES(?,?,?,?,?,?,?,?)""",(
                                  withdrawal_id,policy["policy_id"],policy["instrument_id"],
                                  policy["originator_entity_id"],reason,evidence,created,
                                  json.dumps(wsig,sort_keys=True)))
                    ep.execute("UPDATE participation_policies SET status='WITHDRAWN' WHERE policy_id=?",
                               (policy["policy_id"],))
                ep.commit(); ep.close()

            if self.factory.exists() and audit["dco_ids"]:
                fd=self._db(self.factory); fd.execute("BEGIN IMMEDIATE")
                for dco in audit["dco_ids"]:
                    runs=fd.execute("SELECT issuance_id FROM issuance_runs WHERE dco_id=?",(dco,)).fetchall()
                    for run in runs:
                        fd.execute("""INSERT OR IGNORE INTO issuance_withdrawals
                                      (issuance_id,dco_id,reason,evidence_sha256,created_at_ms)
                                      VALUES(?,?,?,?,?)""",(run["issuance_id"],dco,reason,evidence,created))
                    row=fd.execute("SELECT master_json FROM dco_masters WHERE dco_id=?",(dco,)).fetchone()
                    if row:
                        master=json.loads(row["master_json"]); master["lifecycle"]="ACTIVE"
                        meta=dict(master.get("metadata") or {}); meta["prelaunch_economic_issuance_withdrawn"]=True
                        meta["withdrawal_evidence_sha256"]=evidence; master["metadata"]=meta
                        fd.execute("UPDATE dco_masters SET lifecycle='ACTIVE',master_json=? WHERE dco_id=?",
                                   (json.dumps(master,sort_keys=True,separators=(",",":")),dco))
                fd.commit(); fd.close()
        except Exception:
            for original,backup in backups.items(): shutil.copy2(backup,original)
            raise

        receipt={**body,"evidence_sha256":evidence,"issuer_signatures":signatures,
                 "backup_files":backups,"status":"WITHDRAWN_UNUSED_PRELAUNCH_ECONOMICS"}
        path=self.audit_dir/f"prelaunch-economic-withdrawal-{created}.json"
        path.write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding="utf-8")
        return {**receipt,"receipt_path":str(path)}
