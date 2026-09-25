from __future__ import annotations
import argparse, hashlib, importlib.util, json, pathlib, subprocess, sys, time

ROOT=pathlib.Path(__file__).resolve().parents[1]
BUNDLE=ROOT/'protocol'/'origin'/'ENTITY_PROTOCOL_ORIGIN_BUNDLE.json'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def canon(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(value): return hashlib.sha256(canon(value)).hexdigest()
def git(git_exe,*args): return subprocess.check_output([git_exe,'-C',str(ROOT),*args],text=True).strip()

def main(argv=None):
    p=argparse.ArgumentParser(description='Build signed post-tag ENTITY release-origin attestation')
    p.add_argument('--tag',required=True)
    p.add_argument('--signing-state',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--git',default='git')
    a=p.parse_args(argv)
    bundle=json.loads(BUNDLE.read_text(encoding='utf-8-sig'))
    origin=bundle['origin_chain']; origin_body=origin['body']; protocol_id=origin_body['protocol_entity_id']
    identity=load('release_origin_identity',ROOT/'src/01_Core_Runtime/identity/canonical_identity.py')
    vault=identity.EntityIdentityVault(a.signing_state)
    if identity.canonical_json(vault.load_manifest(protocol_id))!=identity.canonical_json(bundle['public_manifests']['protocol']):
        raise RuntimeError('signing-state ENTITY manifest does not match canonical public protocol manifest')
    commit=git(a.git,'rev-list','-n','1',a.tag); tree=git(a.git,'rev-parse',f'{a.tag}^{{tree}}')
    body={'schema':'entity-protocol-release-origin-v1','release_ref':'entity-release:'+a.tag,
          'release_tag':a.tag,'release_commit_sha1':commit,'release_tree_sha1':tree,
          'protocol_entity_id':protocol_id,'origin_lineage_id':origin_body['lineage_id'],
          'origin_lineage_sha256':origin['body_sha256'],'root_originator_entity_id':origin_body['root_originator_entity_id'],
          'steward_entity_id':origin_body['steward_entity_id'],'historical_release_is_immutable_target':True,
          'asset_provenance_is_separate_from_protocol_origin':True,
          'economic_participation_requires_explicit_terms':True,'automatic_protocol_royalty_bps':0,
          'created_at_ms':int(time.time()*1000)}
    record={'body':body,'body_sha256':digest(body),'signature':vault.sign(protocol_id,body)}
    out=pathlib.Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'output':str(out),'tag':a.tag,'commit':commit,'tree':tree,'body_sha256':record['body_sha256'],
                      'private_keys_included':False},indent=2,sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
