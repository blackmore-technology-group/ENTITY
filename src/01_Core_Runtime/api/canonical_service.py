from __future__ import annotations
from pathlib import Path
import hashlib, hmac, importlib.util, json, os, secrets, time

CORE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = CORE_ROOT / "runtime_state"


def _load(name: str, relative: str):
    path = CORE_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise ImportError(str(path))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def _state_root() -> Path:
    root = Path(os.environ.get("ENTITY_CANONICAL_CORE_STATE", str(DEFAULT_STATE))).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _runtime():
    identity_mod = _load("entity_canonical_identity", "identity/canonical_identity.py")
    policy_mod = _load("entity_canonical_policy", "policy_engine/canonical_policy.py")
    permissions_mod = _load("entity_canonical_permissions", "permissions/canonical_permissions.py")
    identity = identity_mod.EntityIdentityVault(_state_root())
    return identity, policy_mod.PolicyConsentEngine(_state_root(), identity), permissions_mod.AuthorityCapabilityStore(_state_root(), identity)


def _bootstrap_secret_path() -> Path:
    p = _state_root() / "bootstrap"; p.mkdir(parents=True, exist_ok=True)
    return p / "bootstrap.secret"


def ensure_bootstrap_secret_v1() -> dict:
    path = _bootstrap_secret_path()
    if not path.exists():
        path.write_text(secrets.token_urlsafe(32), encoding="utf-8")
        try: os.chmod(path, 0o600)
        except OSError: pass
    return {"schema":"entity-bootstrap-secret-v1","path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}


def _require_bootstrap_secret(request: dict) -> None:
    path = _bootstrap_secret_path()
    if not path.exists(): ensure_bootstrap_secret_v1()
    supplied = str(request.get("bootstrap_token") or "")
    expected = path.read_text(encoding="utf-8").strip()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise PermissionError("invalid canonical bootstrap authorization")


def _bootstrap_receipt_path() -> Path:
    p = _state_root() / "bootstrap"; p.mkdir(parents=True, exist_ok=True)
    return p / "completed.json"


def entity_bootstrap_v1(*, request: dict) -> dict:
    request = dict(request or {})
    _require_bootstrap_secret(request)
    identity, policy, permissions = _runtime()
    receipt_path = _bootstrap_receipt_path()
    if receipt_path.exists() or identity.list_local():
        raise RuntimeError("canonical sovereign root is already bootstrapped")
    manifest = identity.create(
        str(request.get("display_name") or "Primary Entity"),
        str(request.get("entity_type") or "person"),
        aliases=list(request.get("aliases") or []),
        metadata=dict(request.get("metadata") or {}),
    )
    entity_id = str(manifest["entity_id"])
    default_policy = policy.create_policy(
        entity_id, "Sovereign Default Deny", rules={}, jurisdiction=request.get("jurisdiction")
    )
    owner_agent = str(request.get("owner_agent_id") or "owner-console")
    capability = permissions.grant(
        entity_id, owner_agent,
        operations=["ENTITY_ADMIN", "POLICY_ADMIN", "CAPABILITY_ADMIN"],
        approval_required=False, delegation_allowed=False,
    )
    receipt = {
        "schema":"entity-canonical-bootstrap-v1", "entity_id":entity_id,
        "manifest":manifest, "default_policy":default_policy, "owner_capability":capability,
        "created_at_ms":int(time.time()*1000), "state_root":str(_state_root()),
        "authority_owner":"01_Core_Runtime",
    }
    receipt["receipt_sha256"] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    return receipt


def canonical_core_status_v1() -> dict:
    identity, policy, permissions = _runtime()
    return {
        "schema":"entity-canonical-core-status-v1",
        "state_root":str(_state_root()),
        "identity":identity.status(),
        "policy":policy.status(),
        "permissions":permissions.status(),
        "bootstrapped":_bootstrap_receipt_path().exists(),
    }


def sers_acceptance_v1(*, request: dict, required_steps: list[str]) -> dict:
    """Never manufactures platform qualification. A dedicated signed evidence package must be supplied."""
    evidence_file = str((request or {}).get("qualification_evidence_file") or "").strip()
    if not evidence_file:
        raise RuntimeError("full SERS acceptance requires an explicit qualification evidence package")
    path = Path(evidence_file).resolve()
    allowed_root = Path(os.environ.get("ENTITY_QUALIFICATION_EVIDENCE_ROOT", str(CORE_ROOT.parents[1] / "qualification_evidence"))).resolve()
    try: path.relative_to(allowed_root)
    except ValueError as exc: raise PermissionError("qualification evidence must reside under canonical evidence root") from exc
    if not path.is_file(): raise FileNotFoundError(str(path))
    evidence = json.loads(path.read_text(encoding="utf-8")); steps = dict(evidence.get("steps") or {})
    missing = [step for step in required_steps if steps.get(step) != "PASS"]
    if missing: raise RuntimeError("qualification evidence has failing/missing steps: " + ",".join(missing))
    if not evidence.get("evidence_sha256"): raise RuntimeError("qualification evidence is not sealed")
    return {"schema":"entity-sers-acceptance-v1","steps":steps,"evidence":evidence,"source":str(path)}


class CanonicalServiceAPI:
    """Versioned façade over canonical ENTITY authorities. Every mutation requires an active scoped capability."""
    API_VERSION="entity-canonical-service-api-v1"
    def __init__(self,state_dir: str|Path|None=None):
        self.state=Path(state_dir or _state_root()).resolve(); self.state.mkdir(parents=True,exist_ok=True)
        network=CORE_ROOT.parent
        def ext(name,rel):
            path=network/rel; spec=importlib.util.spec_from_file_location(name,path)
            if spec is None or spec.loader is None: raise ImportError(str(path))
            mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
        im=_load("api_identity","identity/canonical_identity.py"); pm=_load("api_policy","policy_engine/canonical_policy.py"); capm=_load("api_permissions","permissions/canonical_permissions.py")
        self.identity=im.EntityIdentityVault(self.state); self.policy=pm.PolicyConsentEngine(self.state,self.identity); self.capabilities=capm.AuthorityCapabilityStore(self.state,self.identity)
        lm=ext("api_ledger",Path("04_Entity_Registry/event_ledger/canonical_event_ledger.py")); rm=ext("api_rights",Path("04_Entity_Registry/ownership_graphs/canonical_rights_claims.py")); provm=ext("api_prov",Path("04_Entity_Registry/provenance/canonical_provenance.py")); am=ext("api_assets",Path("04_Entity_Registry/asset_registry/canonical_asset_registry.py"))
        self.ledger=lm.CanonicalEventLedger(self.state,self.identity); self.rights=rm.RightsClaimsGraph(self.state,self.identity); self.provenance=provm.AssetProvenanceGraph(self.state,self.identity); self.assets=am.CanonicalAssetRegistry(self.state,self.identity,self.ledger,self.rights,self.provenance)
        sm=ext("api_sources",Path("08_Data_Vaults/canonical_data_source_gateway.py")); vm=ext("api_vault",Path("08_Data_Vaults/canonical_encrypted_vault.py"))
        self.sources=sm.DataSourceGateway(self.state); self.vault=vm.EncryptedDataVault(self.state)
        cm=_load("api_contracts","contracts/canonical_contracts.py"); um=_load("api_usage","usage_control/canonical_usage_control.py"); em=_load("api_econ","service_runtime/canonical_economics.py")
        self.contracts=cm.ContractLicensingEngine(self.state,self.identity,self.rights,self.ledger); self.usage=um.UsageControlEngine(self.state,self.identity,self.contracts,self.ledger); self.settlement=em.SettlementEngine(self.state,self.identity)
        bm=ext("api_portable",Path("15_Operations/backups/canonical_portable_state.py")); self.portability=bm.PortableStateManager(self.state,self.identity)
    def _auth(self,capability_id:str,agent_id:str,operation:str,**scope)->dict:
        result=self.capabilities.authorize(capability_id,agent_id,operation,asset_id=scope.get('asset_id'),counterparty_id=scope.get('counterparty_id'),amount=scope.get('amount'),object_ref=scope.get('object_ref'))
        if not result.get('allowed'): raise PermissionError('canonical service authorization denied: '+str(result.get('reason')))
        return result
    def identity_create(self,capability_id:str,agent_id:str,*,display_name:str,entity_type:str,aliases=None,metadata=None)->dict:
        self._auth(capability_id,agent_id,'IDENTITY_ADMIN')
        return self.identity.create(display_name,entity_type,aliases=aliases,metadata=metadata)
    def source_enroll(self,capability_id:str,agent_id:str,controller_entity_id:str,root_path,**kwargs)->dict:
        self._auth(capability_id,agent_id,'SOURCE_ADMIN',object_ref=str(root_path))
        return self.sources.enroll_source(controller_entity_id,root_path,**kwargs)
    def vault_put(self,capability_id:str,agent_id:str,controller_entity_id:str,data:bytes,**kwargs)->dict:
        self._auth(capability_id,agent_id,'VAULT_WRITE')
        return self.vault.put_bytes(controller_entity_id,data,**kwargs)
    def asset_register(self,capability_id:str,agent_id:str,controller_entity_id:str,**kwargs)->dict:
        self._auth(capability_id,agent_id,'ASSET_REGISTER')
        return self.assets.register(controller_entity_id,**kwargs)
    def claim_assert(self,capability_id:str,agent_id:str,claimant_entity_id:str,**kwargs)->dict:
        self._auth(capability_id,agent_id,'RIGHTS_ASSERT',asset_id=kwargs.get('asset_id'))
        return self.rights.assert_claim(claimant_entity_id,**kwargs)
    def dispute_claim(self,capability_id:str,agent_id:str,actor_entity_id:str,claim_id:str,reason:str='',evidence=None)->dict:
        self._auth(capability_id,agent_id,'RIGHTS_DISPUTE',object_ref=claim_id)
        return self.rights.set_state(actor_entity_id,claim_id,'DISPUTED',reason,evidence=evidence)
    def policy_create(self,capability_id:str,agent_id:str,controller_entity_id:str,name:str,rules=None,jurisdiction=None)->dict:
        self._auth(capability_id,agent_id,'POLICY_ADMIN')
        return self.policy.create_policy(controller_entity_id,name,rules=rules,jurisdiction=jurisdiction)
    def consent_grant(self,capability_id:str,agent_id:str,authorizing_entity_id:str,policy_id:str,**kwargs)->dict:
        self._auth(capability_id,agent_id,'CONSENT_GRANT',object_ref=policy_id,counterparty_id=kwargs.get('counterparty_entity_id'))
        return self.policy.grant_consent(authorizing_entity_id,policy_id,**kwargs)
    def licence_draft(self,capability_id:str,agent_id:str,grantor_entity_id:str,licensee_entity_id:str,terms:dict,**kwargs)->dict:
        self._auth(capability_id,agent_id,'LICENCE_CREATE',counterparty_id=licensee_entity_id)
        return self.contracts.create_draft(grantor_entity_id,licensee_entity_id,terms,**kwargs)
    def licence_offer(self,capability_id:str,agent_id:str,grantor_entity_id:str,licence_id:str)->dict:
        self._auth(capability_id,agent_id,'LICENCE_OFFER',object_ref=licence_id)
        return self.contracts.offer(grantor_entity_id,licence_id)
    def licence_accept(self,capability_id:str,agent_id:str,actor_entity_id:str,licence_id:str)->dict:
        self._auth(capability_id,agent_id,'LICENCE_ACCEPT',object_ref=licence_id)
        return self.contracts.accept(actor_entity_id,licence_id)
    def licence_activate(self,capability_id:str,agent_id:str,grantor_entity_id:str,licence_id:str)->dict:
        self._auth(capability_id,agent_id,'LICENCE_ACTIVATE',object_ref=licence_id)
        return self.contracts.activate(grantor_entity_id,licence_id)
    def licence_future_revoke(self,capability_id:str,agent_id:str,grantor_entity_id:str,licence_id:str,reason:str='')->dict:
        self._auth(capability_id,agent_id,'LICENCE_REVOKE',object_ref=licence_id)
        return self.contracts.future_revoke(grantor_entity_id,licence_id,reason)
    def usage_gateway_ticket(self,capability_id:str,agent_id:str,grantor_entity_id:str,**kwargs)->dict:
        self._auth(capability_id,agent_id,'USAGE_AUTHORIZE',asset_id=kwargs.get('asset_id'),object_ref=kwargs.get('licence_id'))
        return self.usage.issue_gateway_ticket(grantor_entity_id,**kwargs)
    def usage_consume(self,capability_id:str,agent_id:str,actor_entity_id:str,ticket_id:str,*,purpose:str,nonce:str)->dict:
        self._auth(capability_id,agent_id,'USAGE_RECORD',object_ref=ticket_id)
        return self.usage.consume_gateway_ticket(actor_entity_id,ticket_id,purpose=purpose,nonce=nonce)
    def usage_declared(self,capability_id:str,agent_id:str,actor_entity_id:str,licence_id:str,**kwargs)->dict:
        self._auth(capability_id,agent_id,'USAGE_RECORD',asset_id=kwargs.get('asset_id'),object_ref=licence_id)
        return self.usage.record_declared(actor_entity_id,licence_id,**kwargs)
    def ledger_append(self,capability_id:str,agent_id:str,actor_entity_id:str,event_type:str,**kwargs)->dict:
        self._auth(capability_id,agent_id,'LEDGER_APPEND',object_ref=event_type)
        return self.ledger.append(actor_entity_id,event_type,**kwargs)
    def ledger_checkpoint(self,capability_id:str,agent_id:str,signer_entity_id:str,**kwargs)->dict:
        self._auth(capability_id,agent_id,'LEDGER_CHECKPOINT')
        return self.ledger.create_checkpoint(signer_entity_id,**kwargs)
    def settlement_create(self,capability_id:str,agent_id:str,payer_entity_id:str,payee_entity_id:str,**kwargs)->dict:
        self._auth(capability_id,agent_id,'SETTLEMENT_CREATE',counterparty_id=payee_entity_id,amount=kwargs.get('amount_units'))
        return self.settlement.create(payer_entity_id,payee_entity_id,**kwargs)
    def settlement_authorize(self,capability_id:str,agent_id:str,payer_entity_id:str,settlement_id:str)->dict:
        self._auth(capability_id,agent_id,'SETTLEMENT_AUTHORIZE',object_ref=settlement_id)
        return self.settlement.authorize(payer_entity_id,settlement_id)
    def settlement_execute(self,capability_id:str,agent_id:str,payer_entity_id:str,settlement_id:str)->dict:
        self._auth(capability_id,agent_id,'SETTLEMENT_EXECUTE',object_ref=settlement_id)
        return self.settlement.begin_execution(payer_entity_id,settlement_id)
    def settlement_evidence(self,capability_id:str,agent_id:str,payer_entity_id:str,settlement_id:str,evidence_level:str,evidence:dict)->dict:
        self._auth(capability_id,agent_id,'SETTLEMENT_EVIDENCE',object_ref=settlement_id)
        return self.settlement.record_external_evidence(payer_entity_id,settlement_id,evidence_level,evidence)
    def settlement_confirm(self,capability_id:str,agent_id:str,payer_entity_id:str,settlement_id:str)->dict:
        self._auth(capability_id,agent_id,'SETTLEMENT_CONFIRM',object_ref=settlement_id)
        return self.settlement.confirm(payer_entity_id,settlement_id)
    def export_entity(self,capability_id:str,agent_id:str,entity_id:str,destination)->dict:
        self._auth(capability_id,agent_id,'EXPORT',object_ref=str(destination))
        return self.portability.export_entity(entity_id,destination)
    def backup_create(self,capability_id:str,agent_id:str,destination,key:bytes|None=None)->dict:
        self._auth(capability_id,agent_id,'BACKUP_CREATE',object_ref=str(destination))
        return self.portability.create_encrypted_backup(destination,key=key)
    def capability_grant(self,admin_capability_id:str,admin_agent_id:str,grantor_entity_id:str,target_agent_id:str,**kwargs)->dict:
        auth=self._auth(admin_capability_id,admin_agent_id,'CAPABILITY_ADMIN')
        if auth.get('grantor_entity_id')!=grantor_entity_id: raise PermissionError('capability administrator cannot grant for another Entity')
        return self.capabilities.grant(grantor_entity_id,target_agent_id,**kwargs)
    def capability_revoke(self,admin_capability_id:str,admin_agent_id:str,grantor_entity_id:str,capability_id:str)->dict:
        auth=self._auth(admin_capability_id,admin_agent_id,'CAPABILITY_ADMIN',object_ref=capability_id)
        if auth.get('grantor_entity_id')!=grantor_entity_id: raise PermissionError('capability administrator cannot revoke for another Entity')
        return self.capabilities.revoke(grantor_entity_id,capability_id)
    def _data_economy(self):
        if not hasattr(self,'_data_economy_cache'):
            network=CORE_ROOT.parent; path=network/'01_Core_Runtime'/'service_runtime'/'canonical_data_economy.py'
            spec=importlib.util.spec_from_file_location('api_data_economy',path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            self._data_economy_cache=(mod.DataPoolManager(self.state,self.identity),mod.DataSpaceGateway(self.state,self.identity))
        return self._data_economy_cache
    def data_pool_create(self,capability_id:str,agent_id:str,controller_entity_id:str,**kwargs)->dict:
        self._auth(capability_id,agent_id,'DATA_POOL_ADMIN')
        pools,_=self._data_economy(); return pools.create_pool(controller_entity_id,**kwargs)
    def data_pool_contribute(self,capability_id:str,agent_id:str,contributor_entity_id:str,pool_id:str,**kwargs)->dict:
        self._auth(capability_id,agent_id,'DATA_POOL_CONTRIBUTE',object_ref=pool_id,asset_id=kwargs.get('asset_id'))
        pools,_=self._data_economy(); return pools.contribute(pool_id,contributor_entity_id,**kwargs)
    def data_space_create(self,capability_id:str,agent_id:str,controller_entity_id:str,assets:list[str],operations:list[str])->dict:
        self._auth(capability_id,agent_id,'DATA_SPACE_ADMIN')
        _,spaces=self._data_economy(); return spaces.create_space(controller_entity_id,assets,operations)
    def data_space_issue(self,capability_id:str,agent_id:str,controller_entity_id:str,space_id:str,counterparty_entity_id:str,operation:str,**kwargs)->dict:
        self._auth(capability_id,agent_id,'DATA_SPACE_AUTHORIZE',counterparty_id=counterparty_entity_id,object_ref=space_id)
        _,spaces=self._data_economy(); return spaces.issue_session(controller_entity_id,space_id,counterparty_entity_id,operation,**kwargs)
    def data_space_consume(self,capability_id:str,agent_id:str,counterparty_entity_id:str,session_id:str)->dict:
        self._auth(capability_id,agent_id,'DATA_SPACE_USE',counterparty_id=counterparty_entity_id,object_ref=session_id)
        _,spaces=self._data_economy(); return spaces.consume(counterparty_entity_id,session_id)
    def status(self)->dict:
        pools,spaces=self._data_economy()
        return {'schema':self.API_VERSION,'ready':True,'domains':{
            'identity':self.identity.status(),'policy_consent':self.policy.status(),'capabilities':self.capabilities.status(),
            'assets':self.assets.status(),'rights':self.rights.status(),'provenance':self.provenance.status(),'ledger':self.ledger.status(),
            'sources':self.sources.status(),'vault':self.vault.status(),'contracts':self.contracts.status(),'usage':self.usage.status(),
            'settlement':self.settlement.status(),'portability':self.portability.status(),'data_pools':pools.status(),'data_spaces':spaces.status()},
            'authorization':'SCOPED_CAPABILITY_REQUIRED_FOR_MUTATION','duplicate_authoritative_state':False}

def canonical_service_api_v1(state_dir: str|Path|None=None)->CanonicalServiceAPI:
    return CanonicalServiceAPI(state_dir)
