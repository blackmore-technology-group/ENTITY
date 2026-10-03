from __future__ import annotations
from pathlib import Path
import hashlib, json, sqlite3

INGEST_SCHEMA="entity-wallet-canonical-asset-ingest-v2"

PACKAGE_KINDS={
    "robotics":["robot","controller","model","software","telemetry","action_record"],
    "ai":["training_dataset","corpus","model","weights","evaluation","agent","output"],
    "manufacturing":["machine","digital_twin","firmware","telemetry","maintenance_record"],
    "healthcare":["clinical_dataset","clinical_document","diagnostic_model","medical_device"],
    "finance":["instrument","trade_record","settlement_record","market_dataset"],
    "defence-public":["public_asset","public_dataset","software","device","model","custody_record"],
}

PACKAGE_POLICY_DEFAULTS={
    "robotics":{"safety_policy":"ENTITY_FAIL_CLOSED"},
    "ai":{"model_governance_policy":"ENTITY_PROVENANCE_BOUND"},
    "manufacturing":{"asset_namespace":"ENTITY_CONTROLLER"},
    "healthcare":{"privacy_policy":"ENTITY_RIGHTS_PASSPORT"},
    "finance":{"settlement_policy":"EXTERNAL_SETTLEMENT_EVIDENCE_REQUIRED"},
    "defence-public":{"release_policy":"PUBLIC_UNCLASSIFIED_ONLY","classification":"UNCLASSIFIED"},
}

class WalletAssetIngestor:
    """Wallet facade over the canonical v3.4.3 ingestion stack.

    The wallet does not maintain a parallel object-registration path. Every new DCO
    flows through the same protocol origin, BTDU, evidence, rights passport and
    Global Passport code used by the canonical ENTITY v3.4 deployment CLI.
    """
    def __init__(self,state_dir:str|Path,canonical_cli):
        self.state=Path(state_dir)
        self.cli=canonical_cli

    @staticmethod
    def asset_kinds(package:str)->list[str]:
        return list(PACKAGE_KINDS.get(str(package).lower(),[]))

    def _existing_dco(self,controller_entity_id:str,content_sha256:str)->str|None:
        dbp=self.state/"entity_v3"/"universal_fabric.sqlite"
        if not dbp.exists(): return None
        db=sqlite3.connect(dbp); db.row_factory=sqlite3.Row
        try:
            rows=db.execute("""SELECT object_id,descriptor_json FROM objects
                               WHERE controller_entity_id=? AND content_sha256=? AND status='ACTIVE'
                               ORDER BY created_at_ms DESC""",(controller_entity_id,content_sha256)).fetchall()
            for row in rows:
                try: descriptor=json.loads(row["descriptor_json"] or "{}")
                except Exception: descriptor={}
                if descriptor.get("digital_commodity") is True: return str(row["object_id"])
        finally: db.close()
        return None

    @staticmethod
    def _configuration(identity,controller_entity_id:str,package:str,jurisdiction:str,authority_basis:str,
                       overrides:dict|None=None)->dict:
        manifest=identity.load_manifest(controller_entity_id)
        package=str(package).lower()
        cfg={
            "organization":str(manifest.get("display_name") or controller_entity_id),
            "jurisdiction":str(jurisdiction or "").strip(),
            "authority_source":str(authority_basis or "").strip(),
            **dict(PACKAGE_POLICY_DEFAULTS.get(package) or {}),
            **dict(overrides or {}),
        }
        if cfg.get("asset_namespace")=="ENTITY_CONTROLLER": cfg["asset_namespace"]=controller_entity_id
        return cfg

    def ingest_file(self,controller_entity_id:str,file_path:str|Path,*,title:str|None=None,
                    package:str="general",asset_kind:str|None=None,jurisdiction:str="",
                    authority_basis:str="CONTROLLER_ENTITY",commodity_class:str="DATA",
                    measurement_unit:str="ASSET",version:str="1.0",
                    previous_object_id:str|None=None,metadata:dict|None=None,
                    configuration:dict|None=None,additional_profiles:list[str]|None=None,
                    additional_rights_actions:list[str]|None=None)->dict:
        src=Path(file_path).expanduser().resolve()
        if not src.is_file(): raise FileNotFoundError(str(src))
        digest=hashlib.sha256()
        with src.open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""): digest.update(chunk)
        source_sha=digest.hexdigest()
        existing=self._existing_dco(controller_entity_id,source_sha)
        if existing and str(previous_object_id or "")!=str(existing):
            raise ValueError(f"identical Digital Commodity Object already registered: {existing}")
        if existing and str(previous_object_id or "")==str(existing):
            # Explicit version/supersession path. Same bytes may be re-registered only
            # when the caller names the exact previous DCO being corrected/versioned.
            pass
        identity,fabric,profiles,origin,passports,packages,sdk,origin_status=self.cli.runtime(
            self.state,require_current_release=True)
        release=origin.passport_binding("entity-release:v3.4.3")
        if release.get("origin_lineage_id")!="entity-origin:shawn-btg-entity@1.0":
            raise RuntimeError("canonical Shawn -> BTG -> ENTITY origin lineage required")
        logical=src.name
        universe=self.cli._btdu_for_controller(self.state,identity,controller_entity_id)
        try:
            receipt=self.cli._btdu_receipt(identity,controller_entity_id,src,logical)
            btdu_obj=universe.ingest_file(
                src,receipt,logical_path=logical,source_entity_id=controller_entity_id,
                controller_entity_id=controller_entity_id,rights_holder_entity_id=controller_entity_id,
                provenance_ref="entity-v3.4.3-wallet-ingest:"+logical)
            binding=universe.passport_binding(btdu_obj["object_ref"])
        finally:
            universe.close()
        content_sha=str(binding["content_sha256"])
        if content_sha!=source_sha: raise RuntimeError("BTDU content hash differs from source asset")
        commodity_meta={
            "wallet_ingest_schema":INGEST_SCHEMA,
            "authority_basis":str(authority_basis),
            "controller_asserted_registration_authority":True,
            "canonical_protocol_lineage_required":True,
            "profile_domain":str(package).lower(),
            "explicit_previous_object_id":str(previous_object_id) if previous_object_id else None,
            "same_content_version_correction":bool(existing and previous_object_id and str(existing)==str(previous_object_id)),
            **dict(metadata or {}),
        }
        package=str(package or "general").lower()
        common={
            "logical_path":logical,"previous_object_id":previous_object_id,"version":str(version),
            "btdu_binding":binding,"title":str(title or src.name),"digital_commodity":True,
            "commodity_class":str(commodity_class).upper(),
            "measurement_unit":str(measurement_unit).upper(),
            "commodity_metadata":commodity_meta,
            "industry_context":{"wallet_ingest":True},
        }
        if package=="general":
            result=sdk.register_file(src,controller_entity_id,"global",**common)
            object_id=result["object_id"]; passport_id=result["global_passport_id"]
        else:
            if package not in PACKAGE_KINDS: raise ValueError("unsupported ENTITY domain package")
            if not asset_kind: raise ValueError("asset_kind required for domain package")
            if asset_kind not in PACKAGE_KINDS[package]: raise ValueError("unsupported package asset kind")
            if not str(jurisdiction or "").strip(): raise ValueError("jurisdiction required for domain package")
            cfg=self._configuration(identity,controller_entity_id,package,jurisdiction,authority_basis,configuration)
            profile_refs=[]
            for p in (additional_profiles or []):
                text=str(p).strip()
                if not text: continue
                profile_refs.append(text if text.startswith("entity-profile:") else sdk.profile_ref(text))
            result=sdk.ingest_package_file(src,controller_entity_id,package,cfg,asset_kind,
                additional_profile_refs=profile_refs,
                additional_rights_actions=[str(x).upper() for x in (additional_rights_actions or []) if str(x)],
                **common)
            object_id=result["object_id"]; passport_id=result["global_passport_id"]
        gp=passports.get(passport_id)
        check=passports.verify(gp)
        if not check.get("valid"): raise RuntimeError("new Global Passport failed verification")
        obj=fabric.get_object(object_id)
        return {
            "schema":INGEST_SCHEMA,
            "digital_asset":obj,
            "content_sha256":obj.get("content_sha256"),
            "global_passport":gp,
            "global_passport_verified":True,
            "rights_passport_id":gp["rights_passport_id"],
            "profile_refs":gp["profile_stack"]["profile_refs"],
            "protocol_origin":gp["protocol_origin"],
            "btdu_binding":gp.get("btdu_binding"),
            "canonical_origin_installation":origin_status,
            "market_instruments_created":False,
            "listing_created":False,
            "price_created":False,
            "economic_value_invented":False,
        }
