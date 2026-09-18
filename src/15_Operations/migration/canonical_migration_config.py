from __future__ import annotations
from pathlib import Path
import hashlib, json, time

def _now(): return int(time.time()*1000)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

DEFAULT_STATE_DOMAINS={
    "identity":"identity","credentials":"credentials","policy_consent":"policy_consent","permissions":"authority",
    "data_sources":"data_source_gateway","data_vault":"vault","asset_registry":"asset_registry","rights_claims":"rights_claims",
    "provenance":"asset_provenance","contracts":"contracts","usage_control":"usage_control","event_ledger":"event_ledger","settlement":"settlement"
}

class MigrationConfiguration:
    """Signed owner-controlled migration interpretation configuration stored inside sovereign state."""
    def __init__(self,state_dir: str|Path,identity):
        self.state=Path(state_dir).resolve(); self.identity=identity; self.root=self.state/"migration"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"migration_config.json"
    def create(self,controller_entity_id: str,*,external_dependencies: list[dict]|None=None,domains: dict|None=None) -> dict:
        body={"schema":"entity-migration-config-v1","controller_entity_id":controller_entity_id,"created_at_ms":_now(),
              "state_format":"ENTITY_STATE_TREE_V1","portable_export_schema":"entity-portable-export-v1","encrypted_backup_schema":"entity-encrypted-backup-v1",
              "domains":dict(domains or DEFAULT_STATE_DOMAINS),"required_interpreters":["JSON","SQLite3","SHA-256","Ed25519","AES-256-GCM"],
              "verification_tool":"independent_verifier.py","external_dependencies":list(external_dependencies or [])}
        signature=self.identity.sign(controller_entity_id,body); record={**body,"signature":signature}
        self.path.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return record
    def load(self) -> dict:
        if not self.path.is_file(): raise FileNotFoundError(str(self.path))
        return json.loads(self.path.read_text(encoding="utf-8"))
    def verify(self) -> dict:
        record=self.load(); signature=dict(record.get("signature") or {}); body={k:v for k,v in record.items() if k!="signature"}
        schema_ok=body.get("schema")=="entity-migration-config-v1" and body.get("state_format")=="ENTITY_STATE_TREE_V1"
        domains_ok=all(str(v).strip() and not Path(str(v)).is_absolute() for v in (body.get("domains") or {}).values())
        try:
            manifest=self.identity.load_manifest(body["controller_entity_id"]); sig_ok=self.identity.verify_signature(manifest,body,signature)
        except Exception: sig_ok=False
        digest=hashlib.sha256(_canon(body)).hexdigest()
        return {"pass":bool(schema_ok and domains_ok and sig_ok),"schema_valid":bool(schema_ok),"relative_domain_paths":bool(domains_ok),"signature_valid":bool(sig_ok),"configuration_sha256":digest,"external_dependencies":list(body.get("external_dependencies") or [])}
    def status(self) -> dict:
        exists=self.path.is_file(); verified=self.verify() if exists else {"pass":False}
        return {"ready":bool(exists and verified.get("pass")),"schema":"entity-migration-config-v1","portable_relative_paths":True,"documented_interpreters":True,"path":str(self.path)}
