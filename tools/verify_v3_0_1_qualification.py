from __future__ import annotations
import json,pathlib,sys
R=pathlib.Path(__file__).resolve().parents[1]
def load(name): return json.loads((R/name).read_text(encoding='utf-8-sig'))
checks={}
q=load('docs/qualification/ENTITY_V3_0_1_RELEASE_QUALIFICATION_2026-09-23.json')
checks['qualification_status']=q.get('status')=='BTG_INTERNAL_QUALIFIED_MAINTENANCE_RELEASE'
checks['regression']=q.get('metrics',{}).get('regression')=={'passed':94,'total':94}
p=load('docs/qualification/ENTITY_V3_BTG_POLYGLOT_QUALIFICATION_2026-09-23.json')
checks['polyglot']=p.get('status')=='PASS' and len(p.get('implementations',{}))==5 and p.get('cross_language_state_agreement') and p.get('cross_language_recovery_agreement') and p.get('cross_language_result_agreement')
k=load('docs/qualification/ENTITY_V3_INTERNAL_KEY_LIFECYCLE_CRYPTO_ASSURANCE_2026-09-23.json')
c=load('docs/qualification/ENTITY_V3_INTERNAL_CRYPTO_ASSURANCE_2026-09-23.json')
pr=load('docs/qualification/ENTITY_V3_INTERNAL_PRIVACY_CRYPTO_ASSURANCE_2026-09-23.json')
checks['crypto']=k.get('pass') is True and c.get('pass') is True and pr.get('pass') is True
s=load('docs/qualification/ENTITY_V3_INTERNAL_PRODUCTION_SCALE_2026-09-23.json')
m=load('docs/qualification/ENTITY_V3_INTERNAL_MARKET_SCALE_QUALIFICATION_2026-09-23.json')
o=load('docs/qualification/ENTITY_V3_INTERNAL_OPERATIONAL_SOAK_2026-09-23.json')
checks['scale']=s.get('pass') is True and s.get('assets')==1000000 and s.get('events')==3000000 and s.get('destructive_restore_verified') is True
checks['market']=m.get('pass') is True and m.get('total_fully_settled_trades',0)>=4000
checks['soak']=o.get('pass') is True and o.get('target_total_wall_seconds',0)>=900
reg=load('docs/compliance/ENTITY_V3_REGULATORY_ENGINEERING_MATRIX_2026-09-23.json')
checks['regulatory_engineering']=reg.get('status')=='INTERNAL_ENGINEERING_MAPPING_COMPLETE'
print(json.dumps({'pass':all(checks.values()),'checks':checks},indent=2,sort_keys=True))
sys.exit(0 if all(checks.values()) else 2)
