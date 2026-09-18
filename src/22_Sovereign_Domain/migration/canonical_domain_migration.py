from __future__ import annotations

class DomainMigrationManager:
    """Moves replaceable serving infrastructure without changing sovereign Entity/domain semantics."""
    def __init__(self,domain_authority):
        self.domain=domain_authority

    def migrate_service(self,entity_id,service_id,*,new_node_public_key_b64,new_endpoint,
                        new_provider=None,old_provider=None,new_node_id=None,revoke_old=True):
        old_service=self.domain.get_service(service_id)
        old_node=self.domain.get_node(old_service['node_id'])
        if old_service['entity_root']!=entity_id: raise PermissionError('service controller mismatch')
        before=self.domain.semantic_hash(old_service['domain_id'])
        node=self.domain.authorize_node(entity_id,old_service['domain_id'],new_node_public_key_b64,
            permitted_services=[old_service['service_type']],network_scopes=['*'],
            publication_scopes=[old_service['service_type']],data_scopes=[],node_id=new_node_id)
        updated=self.domain.publish_service(entity_id,old_service['domain_id'],node['node_id'],
            old_service['service_type'],dict(new_endpoint),protocol_version=old_service['protocol_version'],
            capabilities=list(old_service['capabilities']),access_class=old_service['access_class'],
            required_credentials=list(old_service['required_credentials']),policy_refs=list(old_service['policy_refs']),
            data_classifications=list(old_service['data_classifications']),economic_terms_ref=old_service.get('economic_terms_ref'),
            availability=dict(old_service.get('availability') or {}),expires_at_ms=old_service.get('expires_at_ms'),service_id=service_id)
        if revoke_old and old_node.get('effective_status')=='ACTIVE':
            self.domain.revoke_node(entity_id,old_node['node_id'],'device/provider migration')
        after=self.domain.semantic_hash(old_service['domain_id'])
        migration=self.domain.record_migration(entity_id,old_service['domain_id'],from_node=old_node['node_id'],
            to_node=node['node_id'],from_provider=old_provider,to_provider=new_provider,
            semantic_hash_before=before,semantic_hash_after=after)
        return {'status':'VERIFIED','entity_root':entity_id,'domain_id':old_service['domain_id'],
            'service_id':service_id,'old_node_id':old_node['node_id'],'new_node_id':node['node_id'],
            'service_manifest_version':updated['manifest_version'],'semantic_hash_before':before,
            'semantic_hash_after':after,'entity_root_unchanged':True,'domain_id_unchanged':True,
            'old_provider_retains_authority':False,'migration_record':migration}

    def status(self):
        return {'ready':True,'schema':'entity-domain-migration-manager-v1',
                'provider_replacement_changes_entity':False,'infrastructure_excluded_from_sovereign_semantic_hash':True}
