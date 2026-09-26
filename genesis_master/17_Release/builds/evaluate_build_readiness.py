from pathlib import Path
import hashlib,json,time
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
EV=ROOT/'16_Test_Qualification'/'evidence'; REL=ROOT/'17_Release'/'manifests'; OUT=REL/'ENTITY_BUILD_READINESS_CURRENT.json'
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sealed(d):
    expected=str(d.get('evidence_sha256') or ''); body=dict(d); body.pop('evidence_sha256',None)
    return bool(expected and expected==hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest())
def ok(path,status='PASS'):
    d=load(path); return d.get('status')==status and sealed(d),d
release=load(REL/'ENTITY_10_10_RELEASE_GATE_CURRENT.json')
checks={
    'all_internal_release_gates_pass':bool(release.get('internal_gates_total')) and release.get('internal_gates_passed')==release.get('internal_gates_total'),
    'internal_chaos_qualified':release.get('internal_chaos_qualified') is True,
    'rtm_closed':bool((release.get('master_rtm') or {}).get('full_internal_requirements_closed',False)),
}
files={
    'ultimate_chaos':'ENTITY_ULTIMATE_CHAOS_QUALIFICATION_CURRENT.json','repository_regression':'ENTITY_REPOSITORY_REGRESSION_CURRENT.json',
    'full_e2e':'ENTITY_FULL_E2E_QUALIFICATION_CURRENT.json','production_scale':'ENTITY_PRODUCTION_SCALE_CURRENT.json',
    'million_asset_multi_million_event_scale':'ENTITY_MILLION_ASSET_SCALE_CURRENT.json','million_scale_live_revalidation':'ENTITY_MILLION_SCALE_REVALIDATION_CURRENT.json',
    'local_10000_storm':'ENTITY_10000_CLIENT_STORM_LOCAL_CURRENT.json','destructive_recovery':'ENTITY_DESTRUCTIVE_RECOVERY_CURRENT.json',
    'block_device_loss':'ENTITY_BLOCK_DEVICE_LOSS_CURRENT.json','independent_verifier':'ENTITY_INDEPENDENT_VERIFIER_CURRENT.json',
    'engineering_requirements_closure':'ENTITY_ENGINEERING_REQUIREMENTS_CLOSURE_CURRENT.json','genesis_proof':'ENTITY_GENESIS_PROOF_CURRENT.json',
    'btg_application_sdk':'ENTITY_BTG_APPLICATION_SDK_CURRENT.json',
    'open_entity_sdk':'ENTITY_OPEN_SDK_CURRENT.json',
}
for name,file in files.items():
    try:
        passed,data=ok(EV/file); checks[name]=passed and data.get('qualification_complete') is not False
    except Exception: checks[name]=False
build_ready=all(checks.values())
deferred=[
    {'item':'multi-host distributed storm across independent physical machines','reason':'additional devices/hosts unavailable','classification':'DEFERRED_DEVICE_REQUIRED'},
    {'item':'two physical user-controlled devices for sovereign-domain field qualification','reason':'additional independent device unavailable','classification':'DEFERRED_DEVICE_REQUIRED'},
    {'item':'independently developed non-BTG verifier/interoperable implementation','reason':'independent external organization required','classification':'DEFERRED_EXTERNAL_PARTY_REQUIRED'},
]
payload={'schema':'entity-build-readiness-v2','generated_at_ms':int(time.time()*1000),'status':'BUILD_READY' if build_ready else 'NOT_BUILD_READY','build_ready':build_ready,'checks':checks,'deferred_non_build_blockers':deferred,'full_external_release_qualification':release.get('status'),'internal_release_gates':{'passed':release.get('internal_gates_passed'),'total':release.get('internal_gates_total')},'claim':'Build readiness requires all current internal release gates, closed RTM, Genesis Proof, regression, scale, destructive recovery and independent verification. External/device milestones remain explicitly unclaimed.'}
raw=json.dumps(payload,sort_keys=True,separators=(',',':'),default=str).encode(); payload['evidence_sha256']=hashlib.sha256(raw).hexdigest()
OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8'); OUT.with_suffix('.json.sha256').write_text(hashlib.sha256(OUT.read_bytes()).hexdigest()+'  '+OUT.name+'\n',encoding='utf-8')
print(json.dumps({'status':payload['status'],'checks':checks,'deferred':deferred,'output':str(OUT)},indent=2)); raise SystemExit(0 if build_ready else 2)
