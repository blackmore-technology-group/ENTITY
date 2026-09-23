from __future__ import annotations
import hashlib, json

BTG_TREASURY_NAME='Blackmore Technology Group ENTITY Treasury'
BTG_JURISDICTION='CA'
BTG_VALUE_CHANNELS=(
    'RIGHTS_RESERVES','PRIMARY_ISSUANCE','SECONDARY_ROYALTIES',
    'DERIVATIVE_PARTICIPATION','MARKET_DATA','VENUE_SERVICES',
    'CERTIFICATION','MANAGED_INFRASTRUCTURE','API','INDEX_LICENSING'
)

def _policy_hash(policy_document):
    raw=json.dumps(policy_document,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()
    return hashlib.sha256(raw).hexdigest()

def provision_btg_treasury(profile,btg_legal_entity_id,btg_treasury_entity_id,policy_document):
    '''Bind the generic profile to verified BTG identities supplied by the operator.

    No BTG identifier is hard-coded, and no personal/test ENTITY is accepted implicitly.
    '''
    if not str(btg_legal_entity_id).startswith('ent') or not str(btg_treasury_entity_id).startswith('ent'):
        raise ValueError('verified ENTITY identifiers required for BTG deployment')
    if btg_legal_entity_id==btg_treasury_entity_id:
        raise ValueError('BTG Treasury ENTITY must be distinct from the BTG legal ENTITY')
    if not isinstance(policy_document,dict) or not policy_document:
        raise ValueError('non-empty BTG treasury governance policy required')
    record=profile.create_treasury(
        btg_legal_entity_id,btg_treasury_entity_id,BTG_TREASURY_NAME,
        BTG_JURISDICTION,_policy_hash(policy_document))
    return dict(record,btg_deployment=True,value_channels=list(BTG_VALUE_CHANNELS),
                hard_coded_protocol_privilege=False,protocol_tax_bps=0)

def provision_btg_originator_policy(profile,treasury_id,btg_legal_entity_id,instrument_id,
                                    total_units,reserve_units,currency,*,
                                    primary_treasury_bps=0,secondary_royalty_bps=0,
                                    derivative_participation_bps=0,version=1,terms=None):
    return profile.define_participation(
        btg_legal_entity_id,treasury_id,instrument_id,total_units,reserve_units,currency,
        primary_treasury_bps=primary_treasury_bps,
        secondary_royalty_bps=secondary_royalty_bps,
        derivative_participation_bps=derivative_participation_bps,
        version=version,terms=dict(terms or {}))
