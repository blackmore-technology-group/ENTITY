import hashlib, importlib.util, os, pathlib, tempfile, time, unittest

REPO=pathlib.Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

identity_mod=load('v342eco_identity',REPO/'src/01_Core_Runtime/identity/canonical_identity.py')
fabric_mod=load('v342eco_fabric',REPO/'src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py')
exchange_mod=load('v342eco_exchange',REPO/'src/32_V3_Hardening/exchange_protocol.py')
btdu_mod=load('v342eco_btdu',REPO/'src/40_BTDU/canonical_btdu.py')
eco_mod=load('v342eco_runtime',REPO/'src/41_Ecosystem_Runtime/canonical_ecosystem_runtime.py')
pb_mod=load('v342eco_pb',REPO/'sdk/principal_binding/canonical_principal_binding.py')

@unittest.skipUnless(os.environ.get('ENTITY_ADAM_V1_ROOT'),'verified ADAM source required')
class FederatedEcosystemTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='entity-v342-eco-'); root=pathlib.Path(self.tmp.name)
        self.a_root=root/'a'; self.b_root=root/'b'; self.a_identity=identity_mod.EntityIdentityVault(self.a_root); self.b_identity=identity_mod.EntityIdentityVault(self.b_root)
        self.owner_manifest=self.a_identity.create('Venue Owner','business'); self.owner=self.owner_manifest['entity_id']
        self.buyer_manifest=self.b_identity.create('Remote Buyer','business'); self.buyer=self.buyer_manifest['entity_id']
        self.a_identity.import_public_manifest(self.buyer_manifest); self.b_identity.import_public_manifest(self.owner_manifest)
        body={'schema':'entity-btdu-authorization-v1','actor_entity_id':self.owner,'scope':'BTDU_WRITE','nonce':'federated-test'}
        self.auth={'body':body,'signature':self.a_identity.sign(self.owner,body)}
        def verify_auth(record):
            try: return record['body'].get('scope')=='BTDU_WRITE' and self.a_identity.verify_signature(self.owner_manifest,record['body'],record['signature'])
            except Exception: return False
        self.btdu=btdu_mod.BlackmoreTechnologyDataUniverse(self.a_root/'btdu',authorization_verifier=verify_auth,sovereign_entity_id=self.owner)
        self.btdu_object=self.btdu.ingest_bytes(logical_path='market/sample.txt',data=b'governed BTDU market sample',authorization_receipt=self.auth,source_entity_id=self.owner,controller_entity_id=self.owner,rights_holder_entity_id=self.owner,provenance_ref='test://federated')
        self.fabric=fabric_mod.UniversalTransactionFabric(self.a_root,self.a_identity)
        dco=self.fabric.register_digital_commodity(self.owner,'Federated Data',hashlib.sha256(b'data').hexdigest())
        (self.a_root/'exchange').mkdir(parents=True,exist_ok=True); self.exchange=exchange_mod.ExchangeProtocol(self.a_root/'exchange',self.a_identity,self.fabric)
        self.venue=self.exchange.create_venue(self.owner,'Federated Venue','CA',['ORDER_BOOK','RFQ'],hashlib.sha256(b'policy').hexdigest())
        self.instrument=self.exchange.define_instrument(self.owner,dco['object_id'],'SPOT_LICENSE',{'actions':['READ'],'raw_redistribution':False},1000,'CAD',transferable=True)
        disclosure=self.exchange.publish_disclosure(self.venue['venue_id'],self.instrument['instrument_id'],self.owner,'LISTING',hashlib.sha256(b'disclosure').hexdigest())
        self.exchange.list_instrument(self.venue['venue_id'],self.instrument['instrument_id'],self.owner,1,1,disclosure['content_sha256'])
        gateway=eco_mod.EcosystemServiceGateway(btdu=self.btdu,exchange=self.exchange)
        self.node_a=eco_mod.FederatedEntityNode(self.a_root/'federation',self.a_identity,self.owner,node_id='node-a')
        self.node_b=eco_mod.FederatedEntityNode(self.b_root/'federation',self.b_identity,self.buyer,node_id='node-b')
        self.node_a.commission(name='venue.example.entity',services={'btdu-v342':gateway.btdu_handler,'market-v342':gateway.market_handler})
        self.node_b.commission(name='buyer.example.entity',services={'participant-v342':lambda req:{'buyer':self.buyer,'ready':True}})
        self.node_b.accept_snapshot('resolver-a',self.node_a.snapshot(),self.owner_manifest)
        self.node_a.accept_snapshot('resolver-b',self.node_b.snapshot(),self.buyer_manifest)
    def tearDown(self):
        try: self.node_a.stop(); self.node_b.stop(); self.btdu.close()
        finally: self.tmp.cleanup()

    def test_two_install_encrypted_btdu_and_signed_trade(self):
        pong=self.node_a.request('buyer.example.entity','participant-v342',{'operation':'STATUS'}); self.assertTrue(pong['result']['ready']); self.assertTrue(pong['direct_encrypted_session']); self.assertFalse(pong['dns_used'])
        ctx=self.node_b.request('venue.example.entity','btdu-v342',{'operation':'CONTEXT','object_ref':self.btdu_object['object_ref']})['result']
        self.assertFalse(ctx['raw_content_included']); self.assertFalse(ctx['authority_transferred_to_niki']); self.assertIn('atomized_as',ctx['context'])
        self.exchange.submit_order(self.venue['venue_id'],self.instrument['instrument_id'],self.owner,'SELL',10,50,nonce='seller-local')
        order={'schema':'entity-eep-order-v1','order_id':'remote-buy-1','venue_id':self.venue['venue_id'],'instrument_id':self.instrument['instrument_id'],'participant':self.buyer,'side':'BUY','quantity':10,'limit_price':50,'tif':'GTC','nonce':'buyer-remote','created_at_ms':int(time.time()*1000)}
        signature=self.b_identity.sign(self.buyer,order)
        accepted=self.node_b.request('venue.example.entity','market-v342',{'operation':'SUBMIT_SIGNED_ORDER','order':order,'signature':signature})['result']; self.assertEqual(accepted['participant'],self.buyer)
        trades=self.exchange.match_order_book(self.venue['venue_id'],self.instrument['instrument_id']); self.assertEqual(len(trades),1); self.assertEqual(trades[0]['buyer'],self.buyer)
        evidence=hashlib.sha256(b'federated-payment-evidence').hexdigest(); att=self.exchange.attest_payment(trades[0]['trade_id'],self.owner,'federated-payment',evidence)
        settled=self.exchange.settle_trade(trades[0]['trade_id'],payment_ref='federated-payment',external_verified=True,payment_attestation_id=att['attestation_id']); self.assertEqual(settled['status'],'SETTLED')
        remote_balance=self.node_b.request('venue.example.entity','market-v342',{'operation':'BALANCE','instrument_id':self.instrument['instrument_id'],'holder':self.buyer})['result']['balance_units']; self.assertEqual(remote_balance,10)
    def test_revoked_remote_node_fails_closed(self):
        self.node_a.domain.revoke_node(self.owner,self.node_a.node.node_id,'qualification-revoke')
        with self.assertRaises(PermissionError): self.node_b.accept_snapshot('resolver-a',self.node_a.snapshot(),self.owner_manifest)

class EcosystemBindingTests(unittest.TestCase):
    def test_required_subsystems_validate_and_missing_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix='entity-v342-bind-') as td:
            root=pathlib.Path(td); identity=identity_mod.EntityIdentityVault(root)
            principal=identity.create('Principal','organization')['entity_id']; device=identity.create('Device','system')['entity_id']
            bdir=root/'bindings'; bdir.mkdir()
            for name in eco_mod.REQUIRED_SUBSYSTEMS:
                app=identity.create(name+' Application','application')['entity_id']
                binding=pb_mod.provision_bound_installation(root,principal_entity_id=principal,application_entity_id=app,device_entity_id=device,display_name=name+' Local',alias='test.'+name.lower()+'.entity')
                (bdir/(name.lower()+'_local_principal_binding.json')).write_text(__import__('json').dumps(binding),encoding='utf-8')
                profile={'schema':'btg-subsystem-entity-profile-v1','subsystem':name,'application_entity_id':app,'device_entity_id':device,'installation_entity_id':binding['installation_entity_id'],'principal_entity_id':principal}
                (bdir/(name.lower()+'_entity_profile.json')).write_text(__import__('json').dumps(profile),encoding='utf-8')
            result=eco_mod.EcosystemBindingRegistry(root,bdir).verify_required(); self.assertTrue(result['pass']); self.assertTrue(all(v['valid'] for v in result['subsystems'].values()))
            (bdir/'bsie_entity_profile.json').unlink(); result2=eco_mod.EcosystemBindingRegistry(root,bdir).verify_required(); self.assertFalse(result2['pass']); self.assertFalse(result2['subsystems']['BSIE']['valid'])

if __name__=='__main__': unittest.main()
