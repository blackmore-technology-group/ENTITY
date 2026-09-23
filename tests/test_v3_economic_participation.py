import hashlib, importlib.util, json, pathlib, sqlite3, tempfile, unittest

REPO=pathlib.Path(__file__).resolve().parents[1]
IDENTITY=REPO/'src'/'01_Core_Runtime'/'identity'/'canonical_identity.py'
FABRIC=REPO/'src'/'30_Universal_Transaction_Fabric'/'canonical_universal_fabric.py'
EEP=REPO/'src'/'32_V3_Hardening'/'exchange_protocol.py'
ECON=REPO/'src'/'33_Economic_Participation'/'economic_participation.py'
BTG=REPO/'src'/'33_Economic_Participation'/'btg_deployment.py'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

identity_mod=load('econ_identity',IDENTITY)
fabric_mod=load('econ_fabric',FABRIC)
eep_mod=load('econ_eep',EEP)
econ_mod=load('econ_profile',ECON)
btg_mod=load('econ_btg',BTG)

class EconomicParticipationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.identity=identity_mod.EntityIdentityVault(self.tmp.name)
        self.originator=self.identity.create('Originator Company','business')['entity_id']
        self.treasury_entity=self.identity.create('Originator Treasury','business')['entity_id']
        self.buyer1=self.identity.create('Buyer One','business')['entity_id']
        self.buyer2=self.identity.create('Buyer Two','business')['entity_id']
        self.verifier=self.identity.create('Settlement Verifier','system')['entity_id']
        self.fabric=fabric_mod.UniversalTransactionFabric(self.tmp.name,self.identity)
        self.exchange=eep_mod.ExchangeProtocol(self.tmp.name,self.identity,self.fabric)
        self.profile=econ_mod.EconomicParticipationProfile(self.tmp.name,self.identity)
        self.asset=self.fabric.register_digital_commodity(self.originator,'Economic Corpus',hashlib.sha256(b'corpus').hexdigest())
        self.instrument=self.exchange.define_instrument(self.originator,self.asset['object_id'],'SPOT_LICENSE',{'actions':['TRAIN','INFER']},1000,'CAD',transferable=True)
        self.treasury=self.profile.create_treasury(self.originator,self.treasury_entity,'Originator Treasury','CA',hashlib.sha256(b'treasury policy').hexdigest())
        self.profile.authorize_settlement_verifier(self.treasury['treasury_id'],self.originator,self.verifier)
        self.policy=self.profile.define_participation(self.originator,self.treasury['treasury_id'],self.instrument['instrument_id'],1000,200,'CAD',primary_treasury_bps=2500,secondary_royalty_bps=150,derivative_participation_bps=100,terms={'raw_redistribution':'PROHIBITED'})
        self.profile.allocate_eep_reserve(self.exchange,self.policy['policy_id'])
        self.venue=self.exchange.create_venue(self.originator,'Rights Exchange','CA',['ORDER_BOOK'],hashlib.sha256(b'venue policy').hexdigest())
        disclosure=hashlib.sha256(b'disclosure').hexdigest()
        self.exchange.publish_disclosure(self.venue['venue_id'],self.instrument['instrument_id'],self.originator,'OFFERING',disclosure)
        self.exchange.list_instrument(self.venue['venue_id'],self.instrument['instrument_id'],self.originator,1,1,disclosure)
    def tearDown(self): self.tmp.cleanup()

    def _trade(self,seller,buyer,quantity,price,nonce):
        sell=self.exchange.submit_order(self.venue['venue_id'],self.instrument['instrument_id'],seller,'SELL',quantity,price,nonce=nonce+'-s')
        buy=self.exchange.submit_order(self.venue['venue_id'],self.instrument['instrument_id'],buyer,'BUY',quantity,price,nonce=nonce+'-b')
        trades=self.exchange.match_order_book(self.venue['venue_id'],self.instrument['instrument_id'])
        self.assertEqual(len(trades),1)
        settled=self.exchange.settle_trade(trades[0]['trade_id'],'payment:'+nonce,external_verified=False)
        self.assertEqual(settled['status'],'SETTLED')
        return trades[0]

    def test_btg_deployment_uses_verified_supplied_ids_not_hardcoded_privilege(self):
        profile=econ_mod.EconomicParticipationProfile(self.tmp.name+'-btg',self.identity)
        record=btg_mod.provision_btg_treasury(profile,self.originator,self.treasury_entity,{'policy':'BTG economic participation','version':1})
        self.assertTrue(record['btg_deployment'])
        self.assertFalse(record['hard_coded_protocol_privilege'])
        self.assertEqual(record['protocol_tax_bps'],0)
        self.assertEqual(record['owner_entity_id'],self.originator)
        self.assertEqual(record['treasury_entity_id'],self.treasury_entity)
        with self.assertRaises(ValueError):
            btg_mod.provision_btg_treasury(profile,self.originator,self.originator,{'policy':'bad'})
        with self.assertRaises(ValueError):
            btg_mod.provision_btg_treasury(profile,self.originator,self.treasury_entity,{})

    def test_no_token_no_protocol_tax_and_actual_reserve_balance(self):
        status=self.profile.status()
        self.assertEqual(status['protocol_tax_bps'],0)
        self.assertFalse(status['cryptocurrency_required'])
        self.assertTrue(status['issuer_neutral'])
        self.assertEqual(self.exchange.balance(self.instrument['instrument_id'],self.treasury_entity),200)
        self.assertEqual(self.exchange.balance(self.instrument['instrument_id'],self.originator),800)
        pos=self.profile.position(self.treasury['treasury_id'],self.exchange)
        self.assertIsNone(pos['token_balance'])
        self.assertEqual(pos['reserve_positions'][0]['current_eep_units'],200)

    def test_primary_sale_creates_treasury_allocation(self):
        trade=self._trade(self.originator,self.buyer1,10,100,'primary')
        captured=self.profile.capture_settled_eep_trade(self.exchange,trade['trade_id'])
        self.assertEqual(captured['trade_class'],'PRIMARY')
        self.assertEqual(captured['gross_amount_units'],1000)
        self.assertEqual(captured['obligation']['amount_units'],250)
        self.assertEqual(captured['obligation']['basis'],'PRIMARY_TREASURY_ALLOCATION')
        self.assertEqual(captured['protocol_tax_bps'],0)

    def test_secondary_sale_creates_originator_royalty(self):
        primary=self._trade(self.originator,self.buyer1,20,100,'seed-secondary')
        self.profile.capture_settled_eep_trade(self.exchange,primary['trade_id'])
        secondary=self._trade(self.buyer1,self.buyer2,5,120,'secondary')
        original_sign=self.identity.sign
        def guarded_sign(entity_id,payload):
            if entity_id==self.buyer1:
                raise AssertionError('secondary seller private key must not be used during royalty capture')
            return original_sign(entity_id,payload)
        self.identity.sign=guarded_sign
        try:
            captured=self.profile.capture_settled_eep_trade(self.exchange,secondary['trade_id'])
        finally:
            self.identity.sign=original_sign
        self.assertEqual(captured['trade_class'],'SECONDARY')
        self.assertEqual(captured['gross_amount_units'],600)
        self.assertEqual(captured['obligation']['amount_units'],9)
        self.assertEqual(captured['obligation']['basis'],'SECONDARY_ORIGINATOR_ROYALTY')
        self.assertEqual(captured['event']['actor_entity_id'],self.originator)
        self.assertTrue(captured['event']['details']['sell_order_signature_verified'])
        with self.assertRaises(ValueError):
            self.profile.capture_settled_eep_trade(self.exchange,secondary['trade_id'])

    def test_derivative_participation_and_service_revenue(self):
        derivative=self.profile.record_derivative_revenue(self.policy['policy_id'],self.buyer1,'derivative:model-x',100000,'CAD',hashlib.sha256(b'revenue evidence').hexdigest())
        self.assertEqual(derivative['obligation']['amount_units'],1000)
        service=self.profile.record_service_revenue(self.treasury['treasury_id'],self.buyer2,'MARKET_DATA',500,'CAD','invoice:md-001')
        self.assertEqual(service['obligation']['amount_units'],500)
        pos=self.profile.position(self.treasury['treasury_id'],self.exchange)
        self.assertEqual(pos['monetary_obligations']['CAD']['ACCRUED'],1500)

    def test_external_settlement_requires_evidence_and_remains_attestation(self):
        service=self.profile.record_service_revenue(self.treasury['treasury_id'],self.buyer1,'CERTIFICATION',750,'CAD','invoice:cert-1')
        oid=service['obligation']['obligation_id']
        with self.assertRaises(ValueError):
            self.profile.settle_obligation(oid,self.verifier,'bank:1',external_verified=True)
        proof=self.profile.settle_obligation(oid,self.verifier,'bank:1',external_verified=True,evidence_sha256=hashlib.sha256(b'bank evidence').hexdigest())
        self.assertTrue(proof['external_verified'])
        self.assertTrue(proof['verification_is_attestation_not_absolute_truth'])
        pos=self.profile.position(self.treasury['treasury_id'],self.exchange)
        self.assertEqual(pos['monetary_obligations']['CAD']['SETTLED'],750)

    def test_policy_version_cannot_be_rewritten(self):
        with self.assertRaises(ValueError):
            self.profile.define_participation(self.originator,self.treasury['treasury_id'],self.instrument['instrument_id'],1000,300,'CAD',version=1)
        v2=self.profile.define_participation(self.originator,self.treasury['treasury_id'],self.instrument['instrument_id'],1000,200,'CAD',version=2,secondary_royalty_bps=200)
        self.assertEqual(v2['version'],2)
        self.assertTrue(v2['no_retroactive_economic_rights'])

    def test_policy_history_is_trade_time_bound_and_reserve_not_duplicated(self):
        trade=self._trade(self.originator,self.buyer1,4,100,'historical-policy')
        v2=self.profile.define_participation(self.originator,self.treasury['treasury_id'],self.instrument['instrument_id'],1000,200,'CAD',primary_treasury_bps=5000,secondary_royalty_bps=300,derivative_participation_bps=100,version=2)
        captured=self.profile.capture_settled_eep_trade(self.exchange,trade['trade_id'])
        self.assertEqual(captured['obligation']['bps'],2500)
        self.assertEqual(captured['obligation']['amount_units'],100)
        with self.assertRaises(ValueError):
            self.profile.allocate_eep_reserve(self.exchange,v2['policy_id'])
        self.assertEqual(self.exchange.balance(self.instrument['instrument_id'],self.treasury_entity),200)
        pos=self.profile.position(self.treasury['treasury_id'],self.exchange)
        self.assertEqual(len(pos['reserve_positions']),1)
        self.assertEqual(pos['reserve_positions'][0]['current_eep_units'],200)

    def test_reconciliation_detects_missing_then_complete_trade_capture(self):
        trade=self._trade(self.originator,self.buyer1,3,110,'reconcile')
        before=self.profile.reconcile_eep_trades(self.exchange,self.instrument['instrument_id'])
        self.assertIn(trade['trade_id'],before['missing_trade_ids'])
        self.assertFalse(before['complete'])
        self.profile.capture_settled_eep_trade(self.exchange,trade['trade_id'])
        after=self.profile.reconcile_eep_trades(self.exchange,self.instrument['instrument_id'])
        self.assertNotIn(trade['trade_id'],after['missing_trade_ids'])
        self.assertIn(trade['trade_id'],after['captured_trade_ids'])
        self.assertTrue(after['complete'])

    def test_settlement_verifier_must_be_authorized(self):
        service=self.profile.record_service_revenue(self.treasury['treasury_id'],self.buyer1,'API',500,'CAD','invoice:api-auth')
        rogue=self.identity.create('Rogue Verifier','system')['entity_id']
        with self.assertRaises(PermissionError):
            self.profile.settle_obligation(service['obligation']['obligation_id'],rogue,'bank:rogue',external_verified=True,evidence_sha256=hashlib.sha256(b'rogue').hexdigest())
        proof=self.profile.settle_obligation(service['obligation']['obligation_id'],self.verifier,'bank:ok',external_verified=True,evidence_sha256=hashlib.sha256(b'ok').hexdigest())
        self.assertEqual(proof['verifier_authority_basis'],'AUTHORIZED_SETTLEMENT_VERIFIER')

    def test_policy_must_bind_to_owned_treasury_and_cannot_be_backdated(self):
        other_treasury_entity=self.identity.create('Other Treasury','business')['entity_id']
        other=self.profile.create_treasury(self.buyer1,other_treasury_entity,'Other Treasury','CA',hashlib.sha256(b'other').hexdigest())
        with self.assertRaises(PermissionError):
            self.profile.define_participation(self.originator,other['treasury_id'],'instrument:other',100,0,'CAD')
        with self.assertRaises(ValueError):
            self.profile.define_participation(self.originator,self.treasury['treasury_id'],self.instrument['instrument_id'],1000,200,'CAD',version=2,effective_at_ms=econ_mod.now_ms()-1)

    def test_event_and_obligation_are_atomic_on_obligation_insert_failure(self):
        trade=self._trade(self.originator,self.buyer1,2,100,'atomic-obligation')
        with self.profile._db() as db:
            db.execute("CREATE TRIGGER fail_obligation_insert BEFORE INSERT ON obligations BEGIN SELECT RAISE(ABORT,'forced obligation failure'); END")
        with self.assertRaises(ValueError):
            self.profile.capture_settled_eep_trade(self.exchange,trade['trade_id'])
        with self.profile._db() as db:
            event_count=db.execute('SELECT COUNT(*) FROM economic_events WHERE subject_ref=?',(trade['trade_id'],)).fetchone()[0]
            obligation_count=db.execute('SELECT COUNT(*) FROM obligations').fetchone()[0]
        self.assertEqual(event_count,0)
        self.assertEqual(obligation_count,0)

    def test_reserve_allocation_is_atomic_across_eep_and_eopp(self):
        asset=self.fabric.register_digital_commodity(self.originator,'Atomic Reserve Corpus',hashlib.sha256(b'atomic-reserve').hexdigest())
        inst=self.exchange.define_instrument(self.originator,asset['object_id'],'SPOT_LICENSE',{'actions':['TRAIN']},100,'CAD',transferable=True)
        policy=self.profile.define_participation(self.originator,self.treasury['treasury_id'],inst['instrument_id'],100,25,'CAD',version=1)
        before_originator=self.exchange.balance(inst['instrument_id'],self.originator)
        before_treasury=self.exchange.balance(inst['instrument_id'],self.treasury_entity)
        with self.profile._db() as db:
            db.execute("CREATE TRIGGER fail_reserve_insert BEFORE INSERT ON reserve_allocations WHEN NEW.instrument_id='"+inst['instrument_id']+"' BEGIN SELECT RAISE(ABORT,'forced reserve failure'); END")
        with self.assertRaises(sqlite3.DatabaseError):
            self.profile.allocate_eep_reserve(self.exchange,policy['policy_id'])
        self.assertEqual(self.exchange.balance(inst['instrument_id'],self.originator),before_originator)
        self.assertEqual(self.exchange.balance(inst['instrument_id'],self.treasury_entity),before_treasury)
        with self.profile._db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM reserve_allocations WHERE instrument_id=?',(inst['instrument_id'],)).fetchone()[0],0)

    def test_historical_derivative_revenue_uses_trade_time_policy(self):
        occurred=econ_mod.now_ms()
        future=occurred+2000
        self.profile.define_participation(self.originator,self.treasury['treasury_id'],self.instrument['instrument_id'],1000,200,'CAD',primary_treasury_bps=2500,secondary_royalty_bps=150,derivative_participation_bps=500,version=2,effective_at_ms=future)
        result=self.profile.record_derivative_revenue(self.policy['policy_id'],self.buyer1,'derivative:historical',100000,'CAD',hashlib.sha256(b'historical revenue').hexdigest(),occurred_at_ms=occurred)
        self.assertEqual(result['obligation']['bps'],100)
        self.assertEqual(result['obligation']['amount_units'],1000)
        self.assertEqual(result['event']['details']['occurred_at_ms'],occurred)

    def test_service_receivable_does_not_require_payer_private_key(self):
        original_sign=self.identity.sign
        def guarded_sign(entity_id,payload):
            if entity_id==self.buyer1:
                raise AssertionError('payer private key must not be required to record provider receivable')
            return original_sign(entity_id,payload)
        self.identity.sign=guarded_sign
        try:
            result=self.profile.record_service_revenue(self.treasury['treasury_id'],self.buyer1,'MARKET_DATA',400,'CAD','invoice:no-payer-key')
        finally:
            self.identity.sign=original_sign
        self.assertEqual(result['event']['actor_entity_id'],self.originator)
        self.assertEqual(result['obligation']['payer_entity_id'],self.buyer1)
        self.assertTrue(result['event']['details']['provider_asserted_receivable'])

    def test_reconciliation_detects_missing_obligation(self):
        trade=self._trade(self.originator,self.buyer1,2,150,'missing-obligation')
        captured=self.profile.capture_settled_eep_trade(self.exchange,trade['trade_id'])
        with self.profile._db() as db:
            db.execute('DELETE FROM obligations WHERE event_id=?',(captured['event']['event_id'],))
        result=self.profile.reconcile_eep_trades(self.exchange,self.instrument['instrument_id'])
        self.assertIn(trade['trade_id'],result['missing_obligation_trade_ids'])
        self.assertFalse(result['complete'])
        self.assertTrue(result['event_and_obligation_reconciled'])

    def test_revoked_settlement_verifier_cannot_settle(self):
        service=self.profile.record_service_revenue(self.treasury['treasury_id'],self.buyer1,'API',300,'CAD','invoice:revoked-verifier')
        self.profile.revoke_settlement_verifier(self.treasury['treasury_id'],self.originator,self.verifier)
        with self.assertRaises(PermissionError):
            self.profile.settle_obligation(service['obligation']['obligation_id'],self.verifier,'bank:revoked',external_verified=True,evidence_sha256=hashlib.sha256(b'revoked').hexdigest())

    def test_derivative_currency_must_match_policy(self):
        with self.assertRaises(ValueError):
            self.profile.record_derivative_revenue(self.policy['policy_id'],self.buyer1,'derivative:wrong-currency',1000,'USD',hashlib.sha256(b'currency').hexdigest())

    def test_eopp_schema_tracks_hardening_records(self):
        schema=json.loads((REPO/'protocol'/'v3'/'ENTITY_ORIGINATOR_PARTICIPATION.schema.json').read_text(encoding='utf-8'))
        required=set(schema['$defs']['policy']['required'])
        self.assertTrue({'effective_at_ms','created_at_ms','no_retroactive_economic_rights','treasury_entity_id'} <= required)
        refs={x['$ref'] for x in schema['oneOf']}
        self.assertIn('#/$defs/settlement_verifier_authorization',refs)
        self.assertIn('#/$defs/settlement_attestation',refs)
        self.assertIn('#/$defs/reconciliation',refs)
        self.assertEqual(schema['$defs']['settlement_attestation']['properties']['verification_is_attestation_not_absolute_truth']['const'],True)
        self.assertIn('#/$defs/reserve_allocation',refs)
        self.assertIn('#/$defs/economic_event',refs)
        self.assertIn('#/$defs/indicative_mark',refs)
        self.assertIn('#/$defs/treasury_snapshot',refs)
        recon=set(schema['$defs']['reconciliation']['required'])
        self.assertTrue({'missing_obligation_trade_ids','mismatched_obligation_trade_ids','event_and_obligation_reconciled'} <= recon)
        self.assertEqual(schema['$defs']['reserve_allocation']['properties']['cross_store_atomic']['const'],True)

    def test_indicative_mark_is_not_accounting_value(self):
        trade=self._trade(self.originator,self.buyer1,1,125,'mark')
        self.profile.capture_settled_eep_trade(self.exchange,trade['trade_id'])
        mark=self.profile.indicative_mark(self.treasury['treasury_id'],self.exchange,'LAST')
        self.assertTrue(mark['indicative_only'])
        self.assertTrue(mark['not_accounting_fair_value'])
        self.assertEqual(mark['marks'][0]['observed_unit_price'],125)
        self.assertEqual(mark['marks'][0]['indicative_amount_units'],25000)
        snapshot=self.profile.seal_snapshot(self.treasury['treasury_id'],self.originator,self.exchange)
        self.assertEqual(snapshot['protocol_tax_bps'],0)

if __name__=='__main__': unittest.main()
