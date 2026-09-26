from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]

p=ROOT/'src/38_Global_Passports/passport_conformance.py'
s=p.read_text(encoding='utf-8')
if 'def _btdu_ok' not in s:
    s=s.replace('def _passport_ok(r:dict)->bool:\n', '''def _btdu_ok(r:dict)->bool:\n    if not isinstance(r,dict): return False\n    return r.get("schema")=="entity-btdu-passport-binding-v1" and r.get("btdu_version")=="3.4.2" and bool(r.get("universe_root")) and bool(r.get("object_ref")) and _sha(r.get("content_sha256")) and bool(r.get("sovereign_entity_id")) and r.get("protocol_origin_is_not_asset_provenance") is True and r.get("topology_does_not_create_ownership") is True and r.get("topology_does_not_create_economic_entitlement") is True and int(r.get("automatic_protocol_royalty_bps",-1))==0\n\ndef _passport_ok(r:dict)->bool:\n''')
    old='return r.get("core_primitives")==CORE and bool(r.get("rights_passport_id"))'
    new='return (r.get("btdu_binding") is None or _btdu_ok(r.get("btdu_binding"))) and r.get("core_primitives")==CORE and bool(r.get("rights_passport_id"))'
    s=s.replace(old,new)
p.write_text(s,encoding='utf-8',newline='\n')
src=(ROOT/'tools/build_v3_4_cleanroom_kit.py').read_text(encoding='utf-8')
src=src.replace('"version":"3.4.1","base_release":"v3.4.0",','"version":"3.4.2","base_release":"v3.4.1",')
src=src.replace('"base_commit":"2db5bff64507b8d67642122a5ff2fc73dfef9152"','"base_commit":"9822b1b65f8269ebc17208a342809720729ae2f8"')
src=src.replace('out=ROOT/"protocol/v3/ENTITY_V3_4_GLOBAL_PASSPORT_CLEANROOM_KIT.min.json"','out=ROOT/"protocol/v3/ENTITY_V3_4_2_GLOBAL_PASSPORT_CLEANROOM_KIT.min.json"')
marker='add("valid_ingest","VALID",ingest())\n'
extra='''add("valid_ingest","VALID",ingest())\nbtdu={"schema":"entity-btdu-passport-binding-v1","btdu_version":"3.4.2","universe_root":Z,"object_ref":"btdu-object:example","object_atom_id":O,"content_sha256":T,"sovereign_entity_id":"ent2-example","protocol_origin_is_not_asset_provenance":True,"topology_does_not_create_ownership":True,"topology_does_not_create_economic_entitlement":True,"automatic_protocol_royalty_bps":0}\nx=passport(["entity-profile:global@1.0"]); x["btdu_binding"]=btdu; add("valid_passport_btdu_binding","VALID",x)\nx=passport(["entity-profile:global@1.0"]); x["btdu_binding"]=dict(btdu,topology_does_not_create_ownership=False); add("invalid_passport_btdu_claims_ownership","INVALID",x)\n'''
src=src.replace(marker,extra)
(ROOT/'tools/build_v3_4_2_cleanroom_kit.py').write_text(src,encoding='utf-8',newline='\n')
