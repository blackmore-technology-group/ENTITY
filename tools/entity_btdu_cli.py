from __future__ import annotations
from pathlib import Path
import argparse, importlib.util, json, os, time
REPO=Path(__file__).resolve().parents[1]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def main():
 ap=argparse.ArgumentParser(description='ENTITY v3.4.2 BTDU operator CLI'); ap.add_argument('--entity-state',required=True); ap.add_argument('--btdu-state',required=True); ap.add_argument('--adam-root',required=True); ap.add_argument('--owner-entity-id',default='ent2-6eoiiztjyhmyh2tbr5psmofcduwvjledubhoiqwo6mjfoqkn6ica'); ap.add_argument('--git-bin',default='git')
 sub=ap.add_subparsers(dest='cmd',required=True); sub.add_parser('init'); sub.add_parser('status'); p=sub.add_parser('ingest-repo'); p.add_argument('repo'); p.add_argument('--provenance',default='git://blackmore-technology-group/ENTITY'); p=sub.add_parser('context'); p.add_argument('object_ref'); p=sub.add_parser('reconstruct'); p.add_argument('object_ref'); p.add_argument('output'); sub.add_parser('mirror-genesis')
 a=ap.parse_args(); os.environ['ENTITY_ADAM_V1_ROOT']=str(Path(a.adam_root).resolve()); os.environ['ENTITY_GIT_BIN']=str(a.git_bin)
 ident=load('btdu_cli_identity',REPO/'src'/'01_Core_Runtime'/'identity'/'canonical_identity.py'); btdu=load('btdu_cli_runtime',REPO/'src'/'40_BTDU'/'canonical_btdu.py'); vault=ident.EntityIdentityVault(Path(a.entity_state)); vault.load_manifest(a.owner_entity_id)
 def receipt(purpose):
  body={'schema':'entity-btdu-authorization-v1','actor_entity_id':a.owner_entity_id,'scope':'BTDU_WRITE','purpose':purpose,'issued_at_ms':int(time.time()*1000)}; return {'body':body,'signature':vault.sign(a.owner_entity_id,body)}
 def verifier(record):
  try:
   body=dict(record['body']); return body.get('actor_entity_id')==a.owner_entity_id and body.get('scope')=='BTDU_WRITE' and vault.verify_signature(vault.load_manifest(a.owner_entity_id),body,dict(record['signature']))
  except Exception: return False
 u=btdu.BlackmoreTechnologyDataUniverse(Path(a.btdu_state),authorization_verifier=verifier,sovereign_entity_id=a.owner_entity_id)
 try:
  if a.cmd=='init': out={'primitive_bytes':u.materialize_primitive_bytes(receipt('initialize BTDU')),'verify':u.verify(deep=True)}
  elif a.cmd=='status': out=u.verify(deep=False)
  elif a.cmd=='ingest-repo': out=u.ingest_repository(Path(a.repo),receipt('ingest repository'),source_entity_id=btdu.ENTITY_PROTOCOL_ENTITY_ID,controller_entity_id=a.owner_entity_id,rights_holder_entity_id=a.owner_entity_id,provenance_ref=a.provenance)
  elif a.cmd=='context': out=u.project_object_context(a.object_ref)
  elif a.cmd=='reconstruct':
   raw=u.reconstruct_object(a.object_ref); Path(a.output).write_bytes(raw); out={'object_ref':a.object_ref,'output':str(Path(a.output).resolve()),'bytes':len(raw),'sha256':btdu.sha256(raw)}
  elif a.cmd=='mirror-genesis': out=u.mirror_genesis_market_chain(receipt('mirror Genesis market lineage'),prefix='entity-v3.4.2')
  print(json.dumps(out,indent=2,sort_keys=True))
 finally: u.close()
if __name__=='__main__': main()