from __future__ import annotations
import copy, hashlib, importlib.util, json, pathlib, sqlite3, sys, tempfile, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(name,rel):
    spec=importlib.util.spec_from_file_location(name,ROOT/rel)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

identity_mod=load('origin_test_identity','src/01_Core_Runtime/identity/canonical_identity.py')
fabric_mod=load('origin_test_fabric','src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py')
rights_mod=load('origin_test_rights','src/36_Adoption_Layer/rights_passport.py')
load('reality_profile','src/37_Verifiable_Reality/reality_profile.py')
evidence_mod=load('origin_test_evidence','src/37_Verifiable_Reality/evidence_objects.py')
profile_mod=load('origin_test_profiles','src/38_Global_Passports/profile_registry.py')
industry_mod=load('origin_test_industry','src/38_Global_Passports/industry_profiles.py')
eep_mod=load('origin_test_eep','src/32_V3_Hardening/exchange_protocol.py')
econ_mod=load('origin_test_econ','src/33_Economic_Participation/economic_participation.py')
origin_mod=load('origin_test_origin','src/38_Global_Passports/protocol_origin.py')
global_mod=load('origin_test_global','src/38_Global_Passports/global_passport.py')
ingest_mod=load('origin_test_ingest','src/38_Global_Passports/continuous_ingestion.py')
BUNDLE_PATH=ROOT/'protocol/origin/ENTITY_PROTOCOL_ORIGIN_BUNDLE.json'
class ProtocolOriginLineageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.state=pathlib.Path(self.tmp.name)/'state'
        self.identity=identity_mod.EntityIdentityVault(self.state)
        self.fabric=fabric_mod.UniversalTransactionFabric(self.state,self.identity)
        self.evidence=evidence_mod.EvidenceRegistry(self.state,self.identity)
        self.rights=rights_mod.RightsPassportRegistry(self.state,self.identity,self.fabric)
        self.profiles=profile_mod.GlobalProfileRegistry(self.state,self.identity)
        self.origin=origin_mod.ProtocolOriginRegistry(self.state,self.identity)
        self.bundle=json.loads(BUNDLE_PATH.read_text(encoding='utf-8'))
        self.install=self.origin.install_bundle(self.bundle,self.profiles)
        self.passports=global_mod.GlobalPassportRegistry(self.state,self.identity,self.fabric,self.rights,self.profiles,self.origin)
        self.ingest=ingest_mod.ContinuousProvenanceEngine(self.state,self.identity,self.fabric,self.evidence,self.rights,self.passports,self.origin.default_release_ref)

    def tearDown(self):
        self.tmp.cleanup()

    def test_01_canonical_bundle_imports_public_lineage_and_profiles(self):
        self.assertEqual(self.install['release_origins'],9)
        self.assertEqual(self.install['canonical_profiles_imported'],7)
        self.assertEqual(self.install['automatic_protocol_royalty_bps'],0)
        self.assertTrue(self.install['user_asset_provenance_remains_independent'])
        self.assertEqual(self.origin.default_release_ref,'entity-release:v3.4.0')
    def test_02_all_published_release_targets_are_anchored(self):
        expected={
            'v1.0.0-rc2':'4efb686da7081378e3d8d908abf04aeadf91da60',
            'v1.0.0-rc2.1':'964d2756972c8b14d57dc6a9c10de048962237fa',
            'v1.0.0-rc2.2':'dca93ae228ed39e4441138822ec0d0972b970f2c',
            'v3.0.0':'63acd0962965eda1f80bc8afc6259029daaec7aa',
            'v3.0.1':'a977b013cb29504f04953c4fce33d2372e91097b',
            'v3.1.0':'b985b7cf875bdeeadb228d4d1885395cbcaf19f1',
            'v3.2.0':'512665096cef3771a3a8307d6dc955015ee0efbc',
            'v3.3.0':'9c79f987207592cb6791e1a8956f23351cdfb2d3',
            'v3.4.0':'2db5bff64507b8d67642122a5ff2fc73dfef9152'}
        for tag,commit in expected.items():
            r=self.origin.get_release('entity-release:'+tag)
            self.assertEqual(r['body']['release_commit_sha1'],commit)
            self.assertTrue(self.origin.verify_release(r)['valid'])

    def test_03_new_user_controls_asset_while_protocol_origin_traces_to_shawn(self):
        user=self.identity.create('Independent User','person',aliases=['independent.user.entity'])
        f=pathlib.Path(self.tmp.name)/'user-data.txt'; f.write_text('user-owned source data',encoding='utf-8')
        out=self.ingest.ingest_file(f,user['entity_id'],['entity-profile:global@1.0'],logical_path='user/data.txt')
        gp=out['global_passport']; origin=gp['protocol_origin']
        self.assertEqual(gp['controller_entity_id'],user['entity_id'])
        self.assertNotEqual(user['entity_id'],origin['root_originator_entity_id'])
        self.assertEqual(origin['root_originator_entity_id'],'ent2-6eoiiztjyhmyh2tbr5psmofcduwvjledubhoiqwo6mjfoqkn6ica')
        self.assertEqual(origin['steward_entity_id'],'ent2-kkov66eoh23h3zgr4pe4njsbkayn2kxad6vfyirqvuqrty52clpa')
        self.assertEqual(origin['protocol_entity_id'],'ent2-m3nofxtv3zwldhwuonw3h67hqjh2zambrhj4kaaulncpt4amkcua')
        self.assertTrue(gp['protocol_origin_is_not_asset_provenance'])
        self.assertTrue(origin['protocol_origin_does_not_transfer_user_asset_ownership'])
        self.assertEqual(origin['automatic_protocol_royalty_bps'],0)
        self.assertEqual(gp['economic_state']['amount_units'],0)
        self.assertTrue(self.passports.verify(gp)['valid'])

    def test_04_canonical_profiles_are_issued_by_entity_identity(self):
        for ref in ['entity-profile:global@1.0','entity-profile:healthcare@1.0','entity-profile:finance@1.0','entity-profile:manufacturing@1.0','entity-profile:ai@1.0','entity-profile:robotics@1.0','entity-profile:defence-public@1.0']:
            p=self.profiles.get(ref)
            self.assertEqual(p['issuer_entity_id'],'ent2-m3nofxtv3zwldhwuonw3h67hqjh2zambrhj4kaaulncpt4amkcua')
            self.assertTrue(self.profiles.verify(p)['valid'])

    def test_05_tampered_origin_bundle_is_rejected(self):
        bad=copy.deepcopy(self.bundle)
        bad['origin_chain']['body']['automatic_protocol_royalty_bps']=100
        other=pathlib.Path(self.tmp.name)/'other'; identity=identity_mod.EntityIdentityVault(other)
        profiles=profile_mod.GlobalProfileRegistry(other,identity); origin=origin_mod.ProtocolOriginRegistry(other,identity)
        with self.assertRaises(ValueError): origin.install_bundle(bad,profiles)

    def test_06_v340_state_migrates_to_canonical_profiles_without_breaking_old_passport(self):
        state=pathlib.Path(self.tmp.name)/'legacy-v340'; identity=identity_mod.EntityIdentityVault(state)
        fabric=fabric_mod.UniversalTransactionFabric(state,identity); evidence=evidence_mod.EvidenceRegistry(state,identity)
        rights=rights_mod.RightsPassportRegistry(state,identity,fabric); profiles=profile_mod.GlobalProfileRegistry(state,identity)
        user=identity.create('Legacy User','person',aliases=['legacy.user.entity']); industry_mod.install_builtin_profiles(profiles,user['entity_id'])
        old_profiles={ref:profiles.get(ref) for ref in industry_mod.BUILTIN_PROFILES}
        passports=global_mod.GlobalPassportRegistry(state,identity,fabric,rights,profiles)
        ingest=ingest_mod.ContinuousProvenanceEngine(state,identity,fabric,evidence,rights,passports)
        f=pathlib.Path(self.tmp.name)/'legacy-data.txt'; f.write_text('pre-v3.4.1 user data',encoding='utf-8')
        old=ingest.ingest_file(f,user['entity_id'],['entity-profile:global@1.0'],logical_path='legacy/data.txt')
        old_record=old['global_passport']; old_body={k:v for k,v in old_record.items() if k not in {'body_sha256','signature'}}
        old_body.pop('protocol_origin',None); old_body.pop('protocol_origin_is_not_asset_provenance',None)
        old_sha=global_mod.digest(old_body); old_sig=identity.sign(user['entity_id'],old_body)
        with sqlite3.connect(passports.path) as db:
            db.execute('UPDATE global_passports SET body_sha256=?,body_json=?,signature_json=? WHERE passport_id=?',(old_sha,json.dumps(old_body,sort_keys=True),json.dumps(old_sig,sort_keys=True),old_body['passport_id']))
        legacy_passport=dict(old_body,body_sha256=old_sha,signature=old_sig)
        user_before=identity.load_manifest(user['entity_id']); object_before=fabric.get_object(old['object']['object_id']); right_before=rights.get(old['rights_passport']['passport_id'])
        origin=origin_mod.ProtocolOriginRegistry(state,identity); status=origin.install_bundle(self.bundle,profiles)
        self.assertEqual(status['legacy_profiles_rebound_to_canonical_entity_issuer'],7)
        self.assertEqual(profiles.get('entity-profile:global@1.0')['issuer_entity_id'],'ent2-m3nofxtv3zwldhwuonw3h67hqjh2zambrhj4kaaulncpt4amkcua')
        self.assertEqual(len(profiles.list_variants('entity-profile:global@1.0')),2)
        migrated=global_mod.GlobalPassportRegistry(state,identity,fabric,rights,profiles,origin)
        self.assertTrue(migrated.verify(legacy_passport)['valid'])
        self.assertEqual(identity.load_manifest(user['entity_id']),user_before); self.assertEqual(fabric.get_object(object_before['object_id']),object_before); self.assertEqual(rights.get(right_before['passport_id']),right_before)
        new=migrated.issue(user['entity_id'],object_before['object_id'],right_before['passport_id'],['entity-profile:global@1.0'],version='2.0')
        self.assertEqual(new['controller_entity_id'],user['entity_id']); self.assertEqual(new['protocol_origin']['root_originator_entity_id'],'ent2-6eoiiztjyhmyh2tbr5psmofcduwvjledubhoiqwo6mjfoqkn6ica'); self.assertTrue(migrated.verify(new)['valid'])
        self.assertNotEqual(old_profiles['entity-profile:global@1.0']['body_sha256'],profiles.get('entity-profile:global@1.0')['body_sha256'])

    def test_07_protocol_lineage_does_not_hijack_data_trading_economics(self):
        user=self.identity.create('Data Originator','business')['entity_id']; treasury_entity=self.identity.create('Data Originator Treasury','business')['entity_id']; buyer=self.identity.create('Rights Buyer','business')['entity_id']
        asset=self.fabric.register_digital_commodity(user,'Lineage Corpus',hashlib.sha256(b'lineage-corpus').hexdigest())
        exchange=eep_mod.ExchangeProtocol(self.state,self.identity,self.fabric); econ=econ_mod.EconomicParticipationProfile(self.state,self.identity)
        instrument=exchange.define_instrument(user,asset['object_id'],'SPOT_LICENSE',{'actions':['TRAIN']},1000,'CAD',transferable=True)
        treasury=econ.create_treasury(user,treasury_entity,'Originator Treasury','CA',hashlib.sha256(b'treasury-policy').hexdigest())
        policy=econ.define_participation(user,treasury['treasury_id'],instrument['instrument_id'],1000,0,'CAD',primary_treasury_bps=1000,secondary_royalty_bps=200,derivative_participation_bps=100,terms={'explicit':True})
        venue=exchange.create_venue(user,'Lineage Rights Exchange','CA',['ORDER_BOOK'],hashlib.sha256(b'venue-policy').hexdigest())
        disclosure=hashlib.sha256(b'lineage-disclosure').hexdigest(); exchange.publish_disclosure(venue['venue_id'],instrument['instrument_id'],user,'OFFERING',disclosure); exchange.list_instrument(venue['venue_id'],instrument['instrument_id'],user,1,1,disclosure)
        exchange.submit_order(venue['venue_id'],instrument['instrument_id'],user,'SELL',10,100,nonce='lineage-sell'); exchange.submit_order(venue['venue_id'],instrument['instrument_id'],buyer,'BUY',10,100,nonce='lineage-buy')
        trade=exchange.match_order_book(venue['venue_id'],instrument['instrument_id'])[0]; exchange.settle_trade(trade['trade_id'],'payment:lineage',external_verified=False)
        captured=econ.capture_settled_eep_trade(exchange,trade['trade_id']); protocol_ids={self.origin.passport_binding(self.origin.default_release_ref)[k] for k in ('root_originator_entity_id','steward_entity_id','protocol_entity_id')}
        self.assertEqual(policy['originator_entity_id'],user); self.assertEqual(captured['event']['actor_entity_id'],user); self.assertEqual(captured['obligation']['recipient_entity_id'],treasury_entity)
        self.assertNotIn(treasury_entity,protocol_ids); self.assertEqual(captured['obligation']['amount_units'],100); self.assertEqual(captured['protocol_tax_bps'],0); self.assertEqual(econ.reconcile_eep_trades(exchange,instrument['instrument_id'])['complete'],True)

    def test_08_v341_new_issuance_fails_closed_without_current_release_attestation(self):
        user=self.identity.create('Fail Closed User','person')['entity_id']; f=pathlib.Path(self.tmp.name)/'fail-closed.txt'; f.write_text('release origin required',encoding='utf-8')
        baseline=self.ingest.ingest_file(f,user,['entity-profile:global@1.0'],logical_path='fail/closed.txt')
        gated=global_mod.GlobalPassportRegistry(self.state,self.identity,self.fabric,self.rights,self.profiles,self.origin,required_release_ref='entity-release:v3.4.1')
        with self.assertRaisesRegex(ValueError,'current release origin attestation required'):
            gated.issue(user,baseline['object']['object_id'],baseline['rights_passport']['passport_id'],['entity-profile:global@1.0'],version='2.0')

if __name__=='__main__': unittest.main()
