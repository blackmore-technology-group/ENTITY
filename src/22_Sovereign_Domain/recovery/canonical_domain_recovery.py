from __future__ import annotations
from pathlib import Path
import json

class DomainRecoveryManager:
    """Coordinates sovereign backup restore with independently verifiable domain restoration."""
    def __init__(self,identity_cls,domain_cls,portability_cls):
        self.identity_cls=identity_cls; self.domain_cls=domain_cls; self.portability_cls=portability_cls

    def recover(self,*,backup_manager,backup_path,key,target_state,domain_export_path):
        target=Path(target_state)
        backup_manager.restore_encrypted_backup(backup_path,key,target)
        ids=self.identity_cls(target); domain=self.domain_cls(target,ids); portability=self.portability_cls(ids,domain)
        check=portability.verify_export(domain_export_path)
        if not check.get('valid'): raise PermissionError('domain export invalid during recovery')
        package=json.loads(Path(domain_export_path).read_text(encoding='utf-8'))
        expected_root=package['export_manifest']['entity_root']; expected_domain=package['export_manifest']['domain_id']
        manifest=ids.load_manifest(expected_root)
        if manifest.get('entity_id')!=expected_root: raise RuntimeError('restored Entity root mismatch')
        restored=domain.get_domain(expected_domain)
        if restored.get('domain_id')!=expected_domain or restored.get('entity_root')!=expected_root:
            raise RuntimeError('restored sovereign domain mismatch')
        return {'status':'RECOVERED','entity_root':expected_root,'domain_id':expected_domain,
                'entity_root_unchanged':True,'domain_id_unchanged':True,'domain_export_valid':True,
                'btg_service_required':False,'dns_required':False,'identity_vault':ids,'domain_authority':domain}
