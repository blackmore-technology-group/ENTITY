import hashlib, importlib.util, pathlib, tempfile, unittest, time
REPO=pathlib.Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
identity_mod=load('v3h_identity',REPO/'src'/'01_Core_Runtime'/'identity'/'canonical_identity.py')
fabric_mod=load('v3h_fabric',REPO/'src'/'30_Universal_Transaction_Fabric'/'canonical_universal_fabric.py')
hard=load('v3h_hard',REPO/'src'/'32_V3_Hardening'/'hardening_profiles.py')
eep_mod=load('v3h_eep',REPO/'src'/'32_V3_Hardening'/'exchange_protocol.py')

class V3HardeningExchangeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.identity=identity_mod.EntityIdentityVault(self.tmp.name); self.fabric=fabric_mod.UniversalTransactionFabric(self.tmp.name,self.identity)
        self.owner=self.identity.create('Owner','business')['entity_id']; self.buyer=self.identity.create('Buyer','business')['entity_id']; self.agent=self.identity.create('Agent','system')['entity_id']; self.subagent=self.identity.create('Sub Agent','system')['entity_id']; self.resolver1=self.identity.create('Resolver 1','system')['entity_id']; self.resolver2=self.identity.create('Resolver 2','system')['entity_id']
    def tearDown(self): self.tmp.cleanup()
    def test_profile_and_schema_immutability(self):
        r=hard.ProfileRegistry(self.tmp.name); schema={'type':'object','properties':{'x':{'type':'string'}}}; s=r.register_schema('core.object','1',schema); p=r.register_profile('core','3.0.0',s['document_sha256']); self.assertEqual(p['status'],'ACTIVE')
        with self.assertRaises(ValueError): r.register_schema('core.object','1',{'changed':True})
        self.assertTrue(r.negotiate({'core':['3.0.0']},{'core':['3.0.0']})['core_interop_preserved'])
    def test_privacy_selective_disclosure(self):
        package=hard.SelectiveDisclosure.commit({'age_over_18':True,'name':'hidden','region':'CA'}); proof=hard.SelectiveDisclosure.disclose(package,['age_over_18','region']); result=hard.SelectiveDisclosure.verify(proof)
        self.assertTrue(result['valid']); self.assertNotIn('name',result['revealed_keys']); self.assertNotIn('name',proof['revealed'])
    def test_dispute_history_not_rewritten(self):
        d=hard.DisputeLedger(self.tmp.name,self.identity); claim=d.record('CLAIM',self.owner,'asset:X',{'owner':self.owner}); d.record('CHALLENGE',self.buyer,'asset:X',{'reason':'prior title'},target_ref=claim['record_id']); ruling=d.record('RULING',self.owner,'asset:X',{'outcome':'CLAIM_LIMITED'},target_ref=claim['record_id'],authority_basis='court-order-hash'); d.record('SUPERSESSION',self.owner,'asset:X',{'new_state':'limited-right'},target_ref=ruling['record_id'])
        state=d.state('asset:X'); self.assertEqual(state['state'],'SUPERSEDED'); self.assertEqual(state['record_count'],4); self.assertTrue(state['history_preserved'])
    def test_status_revocation_and_stale_policy(self):
        s=hard.StatusTimeProfile(self.tmp.name,self.identity); now=int(time.time()*1000); s.publish(self.owner,'right:X','ACTIVE',1,10,stale_policy='READ_ONLY_GRACE',effective_at_ms=now); self.assertEqual(s.evaluate('right:X',at_ms=now+20)['decision'],'READ_ONLY'); s.publish(self.owner,'right:X','REVOKED',2,1000,effective_at_ms=now+21); self.assertEqual(s.evaluate('right:X',at_ms=now+22)['decision'],'DENY')
    def test_recovery_quorum(self):
        q=hard.RecoveryQuorum(self.tmp.name,self.identity); q.set_policy(self.owner,[self.buyer,self.agent],2); req=q.request(self.owner,{'reason':'compromise'}); q.approve(req['request_id'],self.buyer); self.assertFalse(q.ready(req['request_id'])['ready']); q.approve(req['request_id'],self.agent); self.assertTrue(q.ready(req['request_id'])['ready'])
    def test_federated_resolution_and_equivocation(self):
        obj=self.fabric.register_object(self.owner,'DOCUMENT','Object'); record={'version':1,'object_id':obj['object_id'],'endpoints':[{'uri':'ent3://x'}]}; f=hard.FederatedResolution(self.tmp.name,self.identity); f.observe(self.resolver1,obj['object_id'],record,1,60000); f.observe(self.resolver2,obj['object_id'],record,1,60000); self.assertTrue(f.quorum(obj['object_id'],2)['resolved'])
        with self.assertRaises(ValueError): f.observe(self.resolver1,obj['object_id'],{'version':1,'object_id':obj['object_id'],'endpoints':[{'uri':'ent3://evil'}]},1,60000)
    def test_agent_attenuation_and_kill(self):
        a=hard.AgentDelegation(self.tmp.name,self.identity); policy=hashlib.sha256(b'policy').hexdigest(); expiry=int(time.time()*1000)+60000; root=a.grant(self.owner,self.owner,self.agent,['READ','TRAIN'],1,100,expiry,policy); child=a.grant(self.owner,self.agent,self.subagent,['READ'],0,25,expiry-1000,policy,parent_grant_id=root['grant_id']); self.assertEqual(a.consume(child['grant_id'],'READ',5)['remaining_units'],20)
        with self.assertRaises(PermissionError): a.grant(self.owner,self.agent,self.subagent,['TRANSFER'],0,1,expiry-1000,policy,parent_grant_id=root['grant_id'])
        killed=a.kill(root['grant_id']); self.assertIn(child['grant_id'],killed['revoked_grants'])
    def test_merkle_degradation_admission_and_bridge(self):
        values=[{'i':i} for i in range(5)]; proof=hard.MerkleBatcher.proof(values,3); self.assertTrue(hard.MerkleBatcher.verify(proof)); sm=hard.DegradationStateMachine(); sm.transition('OFFLINE_VERIFY'); self.assertTrue(sm.permits('VERIFY')); self.assertFalse(sm.permits('TRADE')); ac=hard.AdmissionController(2,1000); self.assertTrue(ac.admit('x')['allowed']); self.assertTrue(ac.admit('x')['allowed']); self.assertFalse(ac.admit('x')['allowed']); bridge=hard.LegacyBridge.map('OIDC','sub-1',self.owner,hashlib.sha256(b'evidence').hexdigest()); self.assertTrue(bridge['legacy_identifier_is_not_entity_authority'])
    def test_eep_full_rights_trade(self):
        dco=self.fabric.register_digital_commodity(self.owner,'Wildfire Corpus',hashlib.sha256(b'data').hexdigest(),commodity_class='ENVIRONMENTAL_TELEMETRY'); eep=eep_mod.ExchangeProtocol(self.tmp.name,self.identity,self.fabric); venue=eep.create_venue(self.owner,'Independent Data Venue','CA',['ORDER_BOOK','RFQ'],hashlib.sha256(b'venue-policy').hexdigest()); inst=eep.define_instrument(self.owner,dco['object_id'],'SPOT_LICENSE',{'actions':['TRAIN','DERIVE'],'raw_redistribution':False},1000,'CAD',transferable=True,duration_ms=86400000); disc=eep.publish_disclosure(venue['venue_id'],inst['instrument_id'],self.owner,'LISTING',hashlib.sha256(b'disclosure').hexdigest()); eep.list_instrument(venue['venue_id'],inst['instrument_id'],self.owner,1,1,disc['content_sha256']); eep.set_revenue_rules(inst['instrument_id'],self.owner,{self.owner:800,self.agent:200}); sell=eep.submit_order(venue['venue_id'],inst['instrument_id'],self.owner,'SELL',100,8430,'sell-1'); buy=eep.submit_order(venue['venue_id'],inst['instrument_id'],self.buyer,'BUY',100,8430,'buy-1'); trades=eep.match_order_book(venue['venue_id'],inst['instrument_id']); self.assertEqual(len(trades),1); att=eep.attest_payment(trades[0]['trade_id'],self.owner,'bank-receipt-hash',hashlib.sha256(b'bank evidence').hexdigest()); settled=eep.settle_trade(trades[0]['trade_id'],'bank-receipt-hash',external_verified=True,payment_attestation_id=att['attestation_id']); self.assertEqual(eep.balance(inst['instrument_id'],self.buyer),100); self.assertFalse(settled['entitlement']['ownership_of_underlying_transferred']); self.assertTrue(settled['external_money_movement_verified']); usage=eep.meter_usage(inst['instrument_id'],self.buyer,'TRAIN',3,'usage-1'); self.assertEqual(usage['units'],3); market=eep.market_data(venue['venue_id'],inst['instrument_id']); self.assertEqual(market['last_price'],8430); self.assertEqual(market['volume_units'],100); self.assertTrue(eep.status()['rights_are_traded_not_bytes'])

    def test_eep_accepts_external_signed_order_without_trader_key_custody(self):
        dco=self.fabric.register_digital_commodity(self.owner,'External Order Corpus',hashlib.sha256(b'external-order').hexdigest())
        eep=eep_mod.ExchangeProtocol(self.tmp.name,self.identity,self.fabric)
        venue=eep.create_venue(self.owner,'External Order Venue','CA',['ORDER_BOOK'],hashlib.sha256(b'policy').hexdigest())
        inst=eep.define_instrument(self.owner,dco['object_id'],'SPOT_LICENSE',{'actions':['TRAIN']},100,'CAD',transferable=True)
        disclosure=hashlib.sha256(b'disclosure').hexdigest(); eep.publish_disclosure(venue['venue_id'],inst['instrument_id'],self.owner,'LISTING',disclosure); eep.list_instrument(venue['venue_id'],inst['instrument_id'],self.owner,1,1,disclosure)
        order={'schema':'entity-eep-order-v1','order_id':'external-buy-1','venue_id':venue['venue_id'],'instrument_id':inst['instrument_id'],'participant':self.buyer,'side':'BUY','quantity':2,'limit_price':100,'tif':'GTC','nonce':'external-buy-nonce','created_at_ms':int(time.time()*1000)}
        signature=self.identity.sign(self.buyer,order)
        tampered=dict(order); tampered['quantity']=3
        with self.assertRaises(PermissionError): eep.submit_signed_order(tampered,signature)
        original_sign=self.identity.sign
        def guarded_sign(entity_id,payload):
            if entity_id==self.buyer: raise AssertionError('venue must not require trader private key')
            return original_sign(entity_id,payload)
        self.identity.sign=guarded_sign
        try: recorded=eep.submit_signed_order(order,signature)
        finally: self.identity.sign=original_sign
        self.assertEqual(recorded['participant'],self.buyer); self.assertEqual(recorded['status'],'OPEN'); self.assertIn('received_at_ms',recorded)
        self.assertTrue(eep.status()['externally_signed_orders'])

    def test_eep_price_time_priority_uses_venue_receipt_not_client_clock(self):
        buyer2=self.identity.create('Buyer 2','business')['entity_id']
        dco=self.fabric.register_digital_commodity(self.owner,'Priority Corpus',hashlib.sha256(b'priority').hexdigest())
        eep=eep_mod.ExchangeProtocol(self.tmp.name,self.identity,self.fabric); venue=eep.create_venue(self.owner,'Priority Venue','CA',['ORDER_BOOK'],hashlib.sha256(b'priority-policy').hexdigest())
        inst=eep.define_instrument(self.owner,dco['object_id'],'SPOT_LICENSE',{'actions':['TRAIN']},10,'CAD',transferable=True); disclosure=hashlib.sha256(b'priority-disclosure').hexdigest(); eep.publish_disclosure(venue['venue_id'],inst['instrument_id'],self.owner,'LISTING',disclosure); eep.list_instrument(venue['venue_id'],inst['instrument_id'],self.owner,1,1,disclosure)
        base={'schema':'entity-eep-order-v1','venue_id':venue['venue_id'],'instrument_id':inst['instrument_id'],'side':'BUY','quantity':1,'limit_price':100,'tif':'GTC'}
        first=dict(base,order_id='priority-first',participant=self.buyer,nonce='priority-1',created_at_ms=int(time.time()*1000)+100000); sig1=self.identity.sign(self.buyer,first); eep.submit_signed_order(first,sig1)
        time.sleep(0.01)
        second=dict(base,order_id='priority-second',participant=buyer2,nonce='priority-2',created_at_ms=0); sig2=self.identity.sign(buyer2,second); eep.submit_signed_order(second,sig2)
        eep.submit_order(venue['venue_id'],inst['instrument_id'],self.owner,'SELL',1,100,'priority-sell')
        trades=eep.match_order_book(venue['venue_id'],inst['instrument_id'])
        self.assertEqual(len(trades),1); self.assertEqual(trades[0]['buyer'],self.buyer)

    def test_eep_settlement_does_not_require_instrument_issuer_private_key(self):
        venue_operator=self.identity.create('Venue Operator','business')['entity_id']
        dco=self.fabric.register_digital_commodity(self.owner,'Settlement Corpus',hashlib.sha256(b'settlement').hexdigest())
        eep=eep_mod.ExchangeProtocol(self.tmp.name,self.identity,self.fabric); venue=eep.create_venue(venue_operator,'Independent Venue','CA',['ORDER_BOOK'],hashlib.sha256(b'independent-venue').hexdigest())
        inst=eep.define_instrument(self.owner,dco['object_id'],'SPOT_LICENSE',{'actions':['TRAIN']},10,'CAD',transferable=True); disclosure=hashlib.sha256(b'settlement-disclosure').hexdigest(); eep.publish_disclosure(venue['venue_id'],inst['instrument_id'],self.owner,'LISTING',disclosure); eep.list_instrument(venue['venue_id'],inst['instrument_id'],self.owner,1,1,disclosure)
        eep.submit_order(venue['venue_id'],inst['instrument_id'],self.owner,'SELL',1,100,'settle-sell'); eep.submit_order(venue['venue_id'],inst['instrument_id'],self.buyer,'BUY',1,100,'settle-buy'); trade=eep.match_order_book(venue['venue_id'],inst['instrument_id'])[0]
        original_sign=self.identity.sign
        def guarded_sign(entity_id,payload):
            if entity_id==self.owner: raise AssertionError('settlement must not require issuer private key')
            return original_sign(entity_id,payload)
        self.identity.sign=guarded_sign
        try: settled=eep.settle_trade(trade['trade_id'],'payment:settlement',external_verified=False)
        finally: self.identity.sign=original_sign
        self.assertEqual(settled['entitlement']['signature']['entity_id'],venue_operator); self.assertEqual(settled['entitlement_attested_by'],'VENUE_OPERATOR')

    def test_encrypted_privacy_succession_and_governance(self):
        key=hashlib.sha256(b'privacy-key').digest(); env=hard.PrivacyEnvelope.encrypt(key,{'secret':'value','classification':'restricted'},{'purpose':'verify'}); self.assertEqual(hard.PrivacyEnvelope.decrypt(key,env,{'purpose':'verify'})['secret'],'value'); p1=hard.PrivacyEnvelope.pseudonym(key,'hospital-A'); p2=hard.PrivacyEnvelope.pseudonym(key,'hospital-B'); self.assertNotEqual(p1,p2)
        succ=hard.SuccessionRegistry(self.tmp.name,self.identity); designation=succ.designate(self.owner,self.buyer,'EMERGENCY_CONTINUITY',hashlib.sha256(b'succession').hexdigest()); self.assertTrue(designation['designation_is_not_trigger_proof'])
        gov=hard.StandardsGovernance(self.tmp.name,self.identity); rfc=gov.propose(self.owner,{'change':'new profile'},threshold=2); self.assertEqual(gov.vote(rfc['rfc_id'],self.buyer,'APPROVE')['rfc_status'],'OPEN'); self.assertEqual(gov.vote(rfc['rfc_id'],self.agent,'APPROVE')['rfc_status'],'ACCEPTED')
    def test_attribution_physical_custody_and_archival_snapshot(self):
        receipt=hard.AttributionMethodology.receipt('obj',self.owner,'declared-contribution','1',{'sourceA':6000,'sourceB':3000},8500,['e1']); self.assertTrue(receipt['methodology_is_not_universal_truth'])
        custody=hard.PhysicalCustody(self.tmp.name,self.identity); evt=custody.record(self.owner,'machine-1',self.owner,self.buyer,'CUSTODY_TRANSFER',hashlib.sha256(b'custody').hexdigest()); self.assertTrue(evt['custody_is_not_ownership'])
        snap=hard.ArchivalSnapshot.create([{'e':1},{'e':2}],1,2); self.assertEqual(snap['event_count'],2); self.assertTrue(snap['pruning_preserves_proof'])
if __name__=='__main__': unittest.main()