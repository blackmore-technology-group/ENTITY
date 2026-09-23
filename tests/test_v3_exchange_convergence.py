import hashlib, importlib.util, pathlib, sqlite3, sys, tempfile, threading, time, unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

identity_mod = load("v3c_identity", REPO / "src/01_Core_Runtime/identity/canonical_identity.py")
fabric_mod = load("v3c_fabric", REPO / "src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
ref_mod = load("v3c_ref_eep", REPO / "src/31_Profiles/exchange_protocol.py")
mirror_mod = load("v3c_mirror_eep", REPO / "src/32_V3_Hardening/exchange_protocol.py")
ref_core = load("v3c_ref_core", REPO / "src/31_Profiles/profile_core.py")
mirror_hard = load("v3c_mirror_hard", REPO / "src/32_V3_Hardening/hardening_profiles.py")

class V3ExchangeConvergenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.identity = identity_mod.EntityIdentityVault(self.root)
        self.fabric = fabric_mod.UniversalTransactionFabric(self.root, self.identity)
        self.owner = self.identity.create("Owner", "business")["entity_id"]
        self.buyer = self.identity.create("Buyer", "business")["entity_id"]
        self.buyer2 = self.identity.create("Buyer 2", "business")["entity_id"]
        self.agent = self.identity.create("Agent", "system")["entity_id"]
        self.dco = self.fabric.register_digital_commodity(
            self.owner, "Reference Data", hashlib.sha256(b"data").hexdigest()
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _verified_settle(self,eep,trade_id,payment_ref):
        evidence=hashlib.sha256((payment_ref+":evidence").encode()).hexdigest()
        att=eep.attest_payment(trade_id,self.owner,payment_ref,evidence)
        return eep.settle_trade(trade_id,payment_ref=payment_ref,external_verified=True,
                                payment_attestation_id=att["attestation_id"])

    def make_ref_exchange(self):
        root = self.root / "reference"
        root.mkdir(exist_ok=True)
        eep = ref_mod.ExchangeProtocol(root, self.identity, self.fabric)
        venue = eep.create_venue(
            self.owner, "Reference Venue", "CA",
            ["ORDER_BOOK", "CALL_AUCTION", "RFQ"],
            hashlib.sha256(b"reference-policy").hexdigest(),
        )
        inst = eep.define_instrument(
            self.owner, self.dco["object_id"], "SPOT_LICENSE",
            {"actions": ["TRAIN", "DERIVE"], "raw_redistribution": False},
            1000, "CAD", transferable=True,
        )
        disc = eep.publish_disclosure(
            venue["venue_id"], inst["instrument_id"], self.owner,
            "LISTING", hashlib.sha256(b"reference-disclosure").hexdigest(),
        )
        eep.list_instrument(
            venue["venue_id"], inst["instrument_id"], self.owner,
            min_lot=1, tick_size=1, disclosure_sha256=disc["content_sha256"],
        )
        return eep, venue, inst

    def make_mirror_exchange(self):
        root = self.root / "mirror"
        root.mkdir(exist_ok=True)
        eep = mirror_mod.ExchangeProtocol(root, self.identity, self.fabric)
        venue = eep.create_venue(
            self.owner, "Mirror Venue", "CA", ["ORDER_BOOK", "RFQ"],
            hashlib.sha256(b"mirror-policy").hexdigest(),
        )
        inst = eep.define_instrument(
            self.owner, self.dco["object_id"], "SPOT_LICENSE",
            {"actions": ["TRAIN", "DERIVE"], "raw_redistribution": False},
            1000, "CAD", transferable=True,
        )
        disc = eep.publish_disclosure(
            venue["venue_id"], inst["instrument_id"], self.owner,
            "LISTING", hashlib.sha256(b"mirror-disclosure").hexdigest(),
        )
        eep.list_instrument(
            venue["venue_id"], inst["instrument_id"], self.owner, 1, 1,
            disc["content_sha256"],
        )
        return eep, venue, inst

    def test_rights_ontology_semantics_converge(self):
        cases = [
            ([{"effect": "ALLOW", "actions": ["TRAIN"]}, {"effect": "PROHIBIT", "actions": ["READ"]}], "TRAIN", "DENY"),
            ([{"effect": "ALLOW", "actions": ["READ"]}, {"effect": "PROHIBIT", "actions": ["TRAIN"]}], "READ", "ALLOW"),
            ([{"effect": "ALLOW", "actions": ["REDISTRIBUTE"]}], "READ", "ALLOW"),
            ([], "READ", "DENY"),
        ]
        for rules, action, expected in cases:
            ref = ref_core.RightsOntology.evaluate(rules, action)["decision"]
            mirror = mirror_hard.RightsOntology.evaluate(rules, action)["decision"]
            self.assertEqual(ref, expected)
            self.assertEqual(mirror, expected)

    def test_order_book_semantics_converge(self):
        ref, rv, ri = self.make_ref_exchange()
        mirror, mv, mi = self.make_mirror_exchange()
        for eep, venue, inst, prefix in (
            (ref, rv, ri, "r"), (mirror, mv, mi, "m"),
        ):
            eep.submit_order(
                venue["venue_id"], inst["instrument_id"], self.owner,
                "SELL", 10, 50, nonce=f"{prefix}-sell",
            )
            eep.submit_order(
                venue["venue_id"], inst["instrument_id"], self.buyer,
                "BUY", 10, 50, nonce=f"{prefix}-buy",
            )
        rt = ref.match_order_book(rv["venue_id"], ri["instrument_id"])
        mt = mirror.match_order_book(mv["venue_id"], mi["instrument_id"])
        self.assertEqual(len(rt), 1)
        self.assertEqual(len(mt), 1)
        self._verified_settle(ref,rt[0]["trade_id"],"ref-pay")
        self._verified_settle(mirror,mt[0]["trade_id"],"mirror-pay")
        self.assertEqual(ref.balance(ri["instrument_id"], self.buyer), 10)
        self.assertEqual(mirror.balance(mi["instrument_id"], self.buyer), 10)
        rmd = ref.market_data(rv["venue_id"], ri["instrument_id"])
        mmd = mirror.market_data(mv["venue_id"], mi["instrument_id"])
        self.assertEqual(rmd["last"], 50)
        self.assertEqual(mmd["last_price"], 50)
        self.assertEqual(rmd["volume_units"], 10)
        self.assertEqual(mmd["volume_units"], 10)

    def test_reference_call_auction_and_rfq_acceptance(self):
        eep, venue, inst = self.make_ref_exchange()
        iid, vid = inst["instrument_id"], venue["venue_id"]
        eep.submit_order(vid, iid, self.owner, "SELL", 100, 80, nonce="auction-sell")
        eep.submit_order(vid, iid, self.buyer, "BUY", 60, 100, nonce="auction-buy-1")
        eep.submit_order(vid, iid, self.buyer2, "BUY", 40, 90, nonce="auction-buy-2")
        auction = eep.run_call_auction(vid, iid)
        self.assertTrue(auction["executed"])
        self.assertEqual(auction["clearing_price"], 80)
        self.assertEqual(auction["executed_volume"], 100)
        for index, trade_id in enumerate(auction["trade_ids"]):
            self._verified_settle(eep,trade_id,f"auction-payment-{index}")
        self.assertEqual(eep.balance(iid, self.buyer), 60)
        self.assertEqual(eep.balance(iid, self.buyer2), 40)
        expiry = int(time.time() * 1000) + 60_000
        rfq = eep.create_rfq(vid, iid, self.buyer, "BUY", 10, expires_at_ms=expiry)
        quote = eep.quote_rfq(rfq["rfq_id"], self.owner, 77, expires_at_ms=expiry)
        execution = eep.accept_quote(rfq["rfq_id"], quote["quote_id"], self.buyer)
        self.assertEqual(execution["execution_model"], "RFQ")
        settled = self._verified_settle(eep,execution["trade_id"],"rfq-payment")
        self.assertEqual(settled["status"], "SETTLED")
        self.assertEqual(eep.balance(iid, self.buyer), 70)

    def test_external_signed_order_and_receipt_priority_converge(self):
        for eep, venue, inst, prefix in (
            (*self.make_ref_exchange(), "r"),
            (*self.make_mirror_exchange(), "m"),
        ):
            iid,vid=inst["instrument_id"],venue["venue_id"]
            base={"schema":"entity-eep-order-v1","venue_id":vid,"instrument_id":iid,"side":"BUY","quantity":1,"limit_price":42,"tif":"GTC"}
            first=dict(base,order_id=f"{prefix}-external-first",participant=self.buyer,nonce=f"{prefix}-external-1",created_at_ms=int(time.time()*1000)+100000)
            sig1=self.identity.sign(self.buyer,first)
            original_sign=self.identity.sign
            def guarded_sign(entity_id,payload):
                if entity_id==self.buyer: raise AssertionError("signed-order ingestion must not use trader private key")
                return original_sign(entity_id,payload)
            self.identity.sign=guarded_sign
            try: recorded=eep.submit_signed_order(first,sig1)
            finally: self.identity.sign=original_sign
            self.assertEqual(recorded["participant"],self.buyer); self.assertIn("received_at_ms",recorded)
            time.sleep(0.01)
            second=dict(base,order_id=f"{prefix}-external-second",participant=self.buyer2,nonce=f"{prefix}-external-2",created_at_ms=0)
            sig2=self.identity.sign(self.buyer2,second); eep.submit_signed_order(second,sig2)
            eep.submit_order(vid,iid,self.owner,"SELL",1,42,nonce=f"{prefix}-priority-sell")
            trades=eep.match_order_book(vid,iid)
            self.assertEqual(len(trades),1); self.assertEqual(trades[0]["buyer"],self.buyer)

    def test_signed_participant_control_paths_converge(self):
        for eep, venue, inst, prefix in (
            (*self.make_ref_exchange(), "r"),
            (*self.make_mirror_exchange(), "m"),
        ):
            iid,vid=inst["instrument_id"],venue["venue_id"]
            order=eep.submit_order(vid,iid,self.buyer,"BUY",1,10,nonce=f"{prefix}-cancel-order")
            cancel={"schema":"entity-eep-order-cancel-v1","cancellation_id":f"{prefix}-cancel-id","order_id":order["order_id"],
                    "participant":self.buyer,"nonce":f"{prefix}-cancel-nonce","created_at_ms":int(time.time()*1000)}
            cancel_sig=self.identity.sign(self.buyer,cancel); original_sign=self.identity.sign
            def guard_buyer(entity_id,payload):
                if entity_id==self.buyer: raise AssertionError("venue must not use participant private key")
                return original_sign(entity_id,payload)
            self.identity.sign=guard_buyer
            try: cancelled=eep.submit_signed_cancellation(cancel,cancel_sig)
            finally: self.identity.sign=original_sign
            self.assertEqual(cancelled["status"],"CANCELLED")
            with self.assertRaises(PermissionError):
                eep.submit_signed_cancellation(dict(cancel,cancellation_id=f"{prefix}-tampered"),cancel_sig)

            eep.submit_order(vid,iid,self.owner,"SELL",2,20,nonce=f"{prefix}-pay-sell")
            eep.submit_order(vid,iid,self.buyer,"BUY",2,20,nonce=f"{prefix}-pay-buy")
            trade=eep.match_order_book(vid,iid)[0]
            eep.authorize_settlement_verifier(vid,self.owner,self.agent)
            pay={"schema":"entity-eep-payment-attestation-v1","attestation_id":f"{prefix}-payatt","trade_id":trade["trade_id"],
                 "verifier_entity_id":self.agent,"settlement_ref":f"{prefix}-payment","evidence_sha256":hashlib.sha256((prefix+"-bank-proof").encode()).hexdigest(),
                 "nonce":f"{prefix}-pay-nonce","created_at_ms":int(time.time()*1000),"verification_is_attestation_not_absolute_truth":True}
            pay_sig=self.identity.sign(self.agent,pay)
            def guard_agent(entity_id,payload):
                if entity_id==self.agent: raise AssertionError("venue must not use verifier private key")
                return original_sign(entity_id,payload)
            self.identity.sign=guard_agent
            try: att=eep.submit_signed_payment_attestation(pay,pay_sig)
            finally: self.identity.sign=original_sign
            self.assertEqual(att["verifier_authority_basis"],"AUTHORIZED_SETTLEMENT_VERIFIER")
            with self.assertRaises(ValueError):
                eep.settle_trade(trade["trade_id"],payment_ref=f"{prefix}-payment",external_verified=True)
            settled=eep.settle_trade(trade["trade_id"],payment_ref=f"{prefix}-payment",external_verified=True,payment_attestation_id=att["attestation_id"])
            self.assertTrue(settled["external_money_movement_verified"])

            usage={"schema":"entity-eep-usage-v1","usage_id":f"{prefix}-usage","instrument_id":iid,"holder":self.buyer,
                   "action":"TRAIN","units":1,"nonce":f"{prefix}-usage-nonce","created_at_ms":int(time.time()*1000)}
            usage_sig=self.identity.sign(self.buyer,usage); self.identity.sign=guard_buyer
            try: recorded=eep.submit_signed_usage(usage,usage_sig)
            finally: self.identity.sign=original_sign
            self.assertEqual(recorded["holder"],self.buyer)
            with self.assertRaises(PermissionError): eep.submit_signed_usage(dict(usage,units=2,usage_id=f"{prefix}-usage-tamper"),usage_sig)

            expiry=int(time.time()*1000)+60000
            rfq={"schema":"entity-eep-rfq-v1","rfq_id":f"{prefix}-rfq","venue_id":vid,"instrument_id":iid,"requester":self.buyer,
                 "side":"BUY","quantity":1,"expires_at_ms":expiry,"nonce":f"{prefix}-rfq-nonce","created_at_ms":int(time.time()*1000)}
            rfq_sig=self.identity.sign(self.buyer,rfq); self.identity.sign=guard_buyer
            try: eep.submit_signed_rfq(rfq,rfq_sig)
            finally: self.identity.sign=original_sign
            quote={"schema":"entity-eep-rfq-quote-v1","quote_id":f"{prefix}-quote","rfq_id":rfq["rfq_id"],"provider":self.owner,
                   "price":30,"expires_at_ms":expiry,"nonce":f"{prefix}-quote-nonce","created_at_ms":int(time.time()*1000)}
            quote_sig=self.identity.sign(self.owner,quote)
            def guard_owner(entity_id,payload):
                if entity_id==self.owner: raise AssertionError("venue must not use provider private key")
                return original_sign(entity_id,payload)
            self.identity.sign=guard_owner
            try: eep.submit_signed_quote(quote,quote_sig)
            finally: self.identity.sign=original_sign
            acceptance={"schema":"entity-eep-rfq-acceptance-v1","acceptance_id":f"{prefix}-accept","rfq_id":rfq["rfq_id"],
                        "quote_id":quote["quote_id"],"requester":self.buyer,"nonce":f"{prefix}-accept-nonce","created_at_ms":int(time.time()*1000)}
            accept_sig=self.identity.sign(self.buyer,acceptance); self.identity.sign=guard_buyer
            try: execution=eep.submit_signed_quote_acceptance(acceptance,accept_sig)
            finally: self.identity.sign=original_sign
            self.assertEqual(execution["execution_model"],"RFQ")

    def test_signed_revenue_rules_require_instrument_issuer_in_both(self):
        for eep,venue,inst,prefix in (
            (*self.make_ref_exchange(),"r"),
            (*self.make_mirror_exchange(),"m"),
        ):
            body={"schema":"entity-eep-revenue-rule-set-v1","rule_set_id":f"{prefix}-rules","instrument_id":inst["instrument_id"],
                  "issuer":self.owner,"allocations_bps":{self.owner:700,self.agent:300},"nonce":f"{prefix}-rules-nonce",
                  "created_at_ms":int(time.time()*1000)}
            sig=self.identity.sign(self.owner,body); original=self.identity.sign
            def guard(entity_id,payload):
                if entity_id==self.owner: raise AssertionError("venue must not use issuer private key")
                return original(entity_id,payload)
            self.identity.sign=guard
            try: result=eep.submit_signed_revenue_rules(body,sig)
            finally: self.identity.sign=original
            self.assertEqual(result["total_bps"],1000)
            with self.assertRaises(PermissionError):
                eep.submit_signed_revenue_rules(dict(body,rule_set_id=f"{prefix}-tamper",allocations_bps={self.owner:900,self.agent:100}),sig)
            rogue=dict(body,rule_set_id=f"{prefix}-rogue",issuer=self.buyer,nonce=f"{prefix}-rogue-nonce")
            rogue_sig=self.identity.sign(self.buyer,rogue)
            with self.assertRaises(PermissionError): eep.submit_signed_revenue_rules(rogue,rogue_sig)

    def test_unsettled_trade_units_remain_reserved_in_both(self):
        for eep,venue,inst,prefix in (
            (*self.make_ref_exchange(),"r-reserve"),
            (*self.make_mirror_exchange(),"m-reserve"),
        ):
            eep.submit_order(venue["venue_id"],inst["instrument_id"],self.owner,"SELL",900,10,nonce=prefix+"-sell")
            eep.submit_order(venue["venue_id"],inst["instrument_id"],self.buyer,"BUY",900,10,nonce=prefix+"-buy")
            trades=eep.match_order_book(venue["venue_id"],inst["instrument_id"])
            self.assertEqual(len(trades),1)
            self.assertEqual(eep.balance(inst["instrument_id"],self.owner),1000)
            self.assertEqual(eep._reserved_sell(inst["instrument_id"],self.owner),900)
            with self.assertRaises(PermissionError):
                eep.submit_order(venue["venue_id"],inst["instrument_id"],self.owner,"SELL",101,11,nonce=prefix+"-oversell")
            self._verified_settle(eep,trades[0]["trade_id"],prefix+"-pay")
            self.assertEqual(eep.balance(inst["instrument_id"],self.owner),100)
            self.assertEqual(eep._reserved_sell(inst["instrument_id"],self.owner),0)

    def test_rfq_acceptance_rechecks_unsettled_sell_commitments(self):
        for eep,venue,inst,prefix in (
            (*self.make_ref_exchange(),"r-rfq-reserve"),
            (*self.make_mirror_exchange(),"m-rfq-reserve"),
        ):
            expiry=int(time.time()*1000)+60000
            rfq=eep.create_rfq(venue["venue_id"],inst["instrument_id"],self.buyer2,"BUY",500,expires_at_ms=expiry)
            quote=eep.quote_rfq(rfq["rfq_id"],self.owner,100,expires_at_ms=expiry)
            eep.submit_order(venue["venue_id"],inst["instrument_id"],self.owner,"SELL",600,10,nonce=prefix+"-sell")
            eep.submit_order(venue["venue_id"],inst["instrument_id"],self.buyer,"BUY",600,10,nonce=prefix+"-buy")
            trades=eep.match_order_book(venue["venue_id"],inst["instrument_id"])
            self.assertEqual(len(trades),1)
            self.assertEqual(eep._reserved_sell(inst["instrument_id"],self.owner),600)
            with self.assertRaises(PermissionError):
                eep.accept_quote(rfq["rfq_id"],quote["quote_id"],self.buyer2,nonce=prefix+"-accept")

    def test_trade_revenue_binding_is_execution_time_immutable(self):
        for eep,venue,inst,prefix,is_mirror in (
            (*self.make_ref_exchange(),"r-revenue-bind",False),
            (*self.make_mirror_exchange(),"m-revenue-bind",True),
        ):
            first={"schema":"entity-eep-revenue-rule-set-v1","rule_set_id":prefix+"-rules-v1","instrument_id":inst["instrument_id"],
                   "issuer":self.owner,"allocations_bps":{self.buyer2:1000},"nonce":prefix+"-rules-v1-nonce","created_at_ms":int(time.time()*1000)}
            eep.submit_signed_revenue_rules(first,self.identity.sign(self.owner,first))
            eep.submit_order(venue["venue_id"],inst["instrument_id"],self.owner,"SELL",10,100,nonce=prefix+"-sell")
            eep.submit_order(venue["venue_id"],inst["instrument_id"],self.buyer,"BUY",10,100,nonce=prefix+"-buy")
            trades=eep.match_order_book(venue["venue_id"],inst["instrument_id"])
            self.assertEqual(len(trades),1); trade_id=trades[0]["trade_id"]
            bound=eep.trade_revenue_binding(trade_id)
            self.assertEqual(bound["rule_set_id"],first["rule_set_id"]); self.assertEqual(bound["allocations_bps"],{self.buyer2:1000})
            second={"schema":"entity-eep-revenue-rule-set-v1","rule_set_id":prefix+"-rules-v2","instrument_id":inst["instrument_id"],
                    "issuer":self.owner,"allocations_bps":{self.agent:2000},"nonce":prefix+"-rules-v2-nonce","created_at_ms":int(time.time()*1000)+1}
            eep.submit_signed_revenue_rules(second,self.identity.sign(self.owner,second))
            self.assertEqual(eep.trade_revenue_binding(trade_id)["allocations_bps"],{self.buyer2:1000})
            settled=self._verified_settle(eep,trade_id,prefix+"-pay")
            if is_mirror:
                revenue=settled["revenue_distribution"]
                self.assertEqual(len(revenue),1); self.assertEqual(revenue[0]["recipient"],self.buyer2); self.assertEqual(revenue[0]["amount_units"],100)
            self.assertEqual(eep.trade_revenue_binding(trade_id)["rule_set_id"],first["rule_set_id"])

    def test_concurrent_sell_admission_is_atomic_in_both(self):
        for eep,venue,inst,prefix in (
            (*self.make_ref_exchange(),"r-concurrent-sell"),
            (*self.make_mirror_exchange(),"m-concurrent-sell"),
        ):
            bodies=[]
            for i in range(2):
                body={"schema":"entity-eep-order-v1","order_id":f"{prefix}-order-{i}","venue_id":venue["venue_id"],
                      "instrument_id":inst["instrument_id"],"participant":self.owner,"side":"SELL","quantity":600,
                      "limit_price":10,"tif":"GTC","nonce":f"{prefix}-nonce-{i}","created_at_ms":int(time.time()*1000)+i}
                bodies.append((body,self.identity.sign(self.owner,body)))
            gate=threading.Barrier(2); original_reserved=eep._reserved_sell
            def gated_reserved(instrument_id,participant):
                value=original_reserved(instrument_id,participant); gate.wait(timeout=5); return value
            eep._reserved_sell=gated_reserved; results=[]; lock=threading.Lock()
            def worker(item):
                body,sig=item
                try: eep.submit_signed_order(body,sig); outcome='ok'
                except Exception as exc: outcome=type(exc).__name__
                with lock: results.append(outcome)
            threads=[threading.Thread(target=worker,args=(item,)) for item in bodies]
            for t in threads: t.start()
            for t in threads: t.join(10)
            eep._reserved_sell=original_reserved
            self.assertTrue(all(not t.is_alive() for t in threads))
            self.assertEqual(results.count('ok'),1,results); self.assertEqual(results.count('PermissionError'),1,results)
            self.assertEqual(eep._reserved_sell(inst["instrument_id"],self.owner),600)

    def test_concurrent_matching_creates_exactly_one_trade_in_both(self):
        for eep,venue,inst,prefix in (
            (*self.make_ref_exchange(),"r-concurrent-match"),
            (*self.make_mirror_exchange(),"m-concurrent-match"),
        ):
            eep.submit_order(venue["venue_id"],inst["instrument_id"],self.owner,"SELL",10,100,nonce=prefix+"-sell")
            eep.submit_order(venue["venue_id"],inst["instrument_id"],self.buyer,"BUY",10,100,nonce=prefix+"-buy")
            start=threading.Barrier(2); results=[]; lock=threading.Lock()
            def worker():
                start.wait(timeout=5)
                try: outcome=len(eep.match_order_book(venue["venue_id"],inst["instrument_id"]))
                except Exception as exc: outcome=type(exc).__name__
                with lock: results.append(outcome)
            threads=[threading.Thread(target=worker) for _ in range(2)]
            for t in threads: t.start()
            for t in threads: t.join(10)
            self.assertTrue(all(not t.is_alive() for t in threads)); self.assertEqual(sum(x for x in results if isinstance(x,int)),1,results)
            with eep._db() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM trades WHERE instrument_id=?',(inst["instrument_id"],)).fetchone()[0],1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM orders WHERE instrument_id=? AND status='FILLED'",(inst["instrument_id"],)).fetchone()[0],2)

    def test_concurrent_double_settlement_is_atomic_in_both(self):
        for eep,venue,inst,prefix in (
            (*self.make_ref_exchange(),"r-double-settle"),
            (*self.make_mirror_exchange(),"m-double-settle"),
        ):
            eep.submit_order(venue["venue_id"],inst["instrument_id"],self.owner,"SELL",10,100,nonce=prefix+"-sell")
            eep.submit_order(venue["venue_id"],inst["instrument_id"],self.buyer,"BUY",10,100,nonce=prefix+"-buy")
            trade=eep.match_order_book(venue["venue_id"],inst["instrument_id"])[0]
            payment=prefix+"-pay"; evidence=hashlib.sha256((payment+":evidence").encode()).hexdigest()
            att=eep.attest_payment(trade["trade_id"],self.owner,payment,evidence)
            start=threading.Barrier(2); old_balance=eep.balance; legacy_gate=threading.Barrier(2)
            def gated_balance(instrument_id,holder):
                value=old_balance(instrument_id,holder); legacy_gate.wait(timeout=5); return value
            eep.balance=gated_balance; results=[]; lock=threading.Lock()
            def settle_worker():
                start.wait(timeout=5)
                try:
                    eep.settle_trade(trade["trade_id"],payment_ref=payment,external_verified=True,payment_attestation_id=att["attestation_id"]); outcome='ok'
                except Exception as exc: outcome=type(exc).__name__
                with lock: results.append(outcome)
            threads=[threading.Thread(target=settle_worker) for _ in range(2)]
            for t in threads: t.start()
            for t in threads: t.join(10)
            eep.balance=old_balance
            self.assertTrue(all(not t.is_alive() for t in threads))
            self.assertEqual(results.count('ok'),1,results); self.assertEqual(results.count('KeyError'),1,results)
            self.assertEqual(eep.balance(inst["instrument_id"],self.owner),990); self.assertEqual(eep.balance(inst["instrument_id"],self.buyer),10)
            with eep._db() as db: self.assertEqual(db.execute('SELECT COUNT(*) FROM entitlements WHERE trade_id=?',(trade["trade_id"],)).fetchone()[0],1)

    def test_revenue_event_failure_rolls_back_hardening_settlement(self):
        eep,venue,inst=self.make_mirror_exchange()
        eep.set_revenue_rules(inst["instrument_id"],self.owner,{self.buyer2:1000},nonce='atomic-revenue-rule')
        eep.submit_order(venue["venue_id"],inst["instrument_id"],self.owner,"SELL",10,100,nonce='atomic-revenue-sell')
        eep.submit_order(venue["venue_id"],inst["instrument_id"],self.buyer,"BUY",10,100,nonce='atomic-revenue-buy')
        trade=eep.match_order_book(venue["venue_id"],inst["instrument_id"])[0]
        with eep._db() as db:
            db.execute("CREATE TRIGGER fail_revenue_event BEFORE INSERT ON revenue_events BEGIN SELECT RAISE(ABORT,'forced revenue failure'); END")
        with self.assertRaises(sqlite3.DatabaseError): self._verified_settle(eep,trade["trade_id"],'atomic-revenue-pay')
        self.assertEqual(eep.balance(inst["instrument_id"],self.owner),1000); self.assertEqual(eep.balance(inst["instrument_id"],self.buyer),0)
        with eep._db() as db:
            self.assertEqual(db.execute('SELECT status FROM trades WHERE trade_id=?',(trade["trade_id"],)).fetchone()[0],'EXECUTED')
            self.assertEqual(db.execute('SELECT status FROM clearing WHERE trade_id=?',(trade["trade_id"],)).fetchone()[0],'PENDING')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM entitlements WHERE trade_id=?',(trade["trade_id"],)).fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM revenue_events WHERE trade_id=?',(trade["trade_id"],)).fetchone()[0],0)

    def test_external_signed_issuer_instrument_disclosure_listing_converge(self):
        for eep,venue,_existing,prefix in (
            (*self.make_ref_exchange(),"r"),
            (*self.make_mirror_exchange(),"m"),
        ):
            dco=self.fabric.register_digital_commodity(self.owner,f"{prefix}-External Corpus",hashlib.sha256((prefix+"-external-data").encode()).hexdigest())
            instrument={"schema":"entity-eep-instrument-v1","instrument_id":f"{prefix}-external-inst","issuer":self.owner,
                        "underlying_object_id":dco["object_id"],"instrument_class":"SPOT_LICENSE","rights":{"actions":["DERIVE","TRAIN"],"raw_redistribution":False},
                        "total_units":100,"transferable":True,"duration_ms":None,"settlement_currency":"CAD","delivery_mode":"ENTITLEMENT",
                        "status":"ACTIVE","created_at_ms":int(time.time()*1000),"bytes_are_not_the_traded_scarcity":True}
            inst_sig=self.identity.sign(self.owner,instrument); original=self.identity.sign
            def guard_owner(entity_id,payload):
                if entity_id==self.owner: raise AssertionError("venue must not use issuer/lister private key")
                return original(entity_id,payload)
            self.identity.sign=guard_owner
            try: recorded=eep.submit_signed_instrument(instrument,inst_sig)
            finally: self.identity.sign=original
            self.assertEqual(recorded["instrument_id"],instrument["instrument_id"])
            with self.assertRaises(PermissionError):
                eep.submit_signed_instrument(dict(instrument,instrument_id=f"{prefix}-inst-tamper"),inst_sig)

            content=hashlib.sha256((prefix+"-offering").encode()).hexdigest()
            disclosure={"schema":"entity-eep-disclosure-v1","disclosure_id":f"{prefix}-disc","venue_id":venue["venue_id"],
                        "instrument_id":instrument["instrument_id"],"publisher":self.owner,"disclosure_type":"OFFERING","content_sha256":content,
                        "created_at_ms":int(time.time()*1000),"protected_data_included":False}
            disc_sig=self.identity.sign(self.owner,disclosure); self.identity.sign=guard_owner
            try: disc=eep.submit_signed_disclosure(disclosure,disc_sig)
            finally: self.identity.sign=original
            self.assertFalse(disc["protected_data_included"])

            listing={"schema":"entity-eep-listing-v1","listing_id":f"{prefix}-listing","venue_id":venue["venue_id"],
                     "instrument_id":instrument["instrument_id"],"lister":self.owner,"min_lot":1,"tick_size":1,"disclosure_sha256":content,
                     "status":"ACTIVE","created_at_ms":int(time.time()*1000)}
            list_sig=self.identity.sign(self.owner,listing); self.identity.sign=guard_owner
            try: listed=eep.submit_signed_listing(listing,list_sig)
            finally: self.identity.sign=original
            self.assertEqual(listed["disclosure_sha256"],content)
            missing=dict(listing,listing_id=f"{prefix}-missing-disc",disclosure_sha256=hashlib.sha256(b"missing").hexdigest())
            missing_sig=self.identity.sign(self.owner,missing)
            with self.assertRaises(ValueError): eep.submit_signed_listing(missing,missing_sig)

    def test_entitlement_receipt_and_expiry_semantics_converge(self):
        required={"schema","entitlement_id","trade_id","instrument_id","holder","quantity","rights",
                  "expires_at_ms","created_at_ms","instrument_issuer","venue_operator",
                  "ownership_of_underlying_transferred","venue_operator_is_not_underlying_owner","signature"}
        for eep,venue,_base,prefix in (
            (*self.make_ref_exchange(),"r"),
            (*self.make_mirror_exchange(),"m"),
        ):
            inst=eep.define_instrument(self.owner,self.dco["object_id"],"SPOT_LICENSE",{"actions":["TRAIN"]},10,"CAD",transferable=True,duration_ms=20)
            content=hashlib.sha256((prefix+"-expiry-disclosure").encode()).hexdigest()
            disc=eep.publish_disclosure(venue["venue_id"],inst["instrument_id"],self.owner,"OFFERING",content)
            eep.list_instrument(venue["venue_id"],inst["instrument_id"],self.owner,min_lot=1,tick_size=1,disclosure_sha256=disc["content_sha256"])
            eep.submit_order(venue["venue_id"],inst["instrument_id"],self.owner,"SELL",1,5,nonce=f"{prefix}-expiry-sell")
            eep.submit_order(venue["venue_id"],inst["instrument_id"],self.buyer,"BUY",1,5,nonce=f"{prefix}-expiry-buy")
            trade=eep.match_order_book(venue["venue_id"],inst["instrument_id"])[0]
            settled=eep.settle_trade(trade["trade_id"],payment_ref=f"{prefix}-expiry-pay",external_verified=False)
            entitlement=settled["entitlement"]
            self.assertEqual(set(entitlement),required)
            self.assertFalse(entitlement["ownership_of_underlying_transferred"])
            self.assertTrue(entitlement["venue_operator_is_not_underlying_owner"])
            self.assertEqual(entitlement["instrument_issuer"],self.owner)
            self.assertEqual(entitlement["venue_operator"],self.owner)
            self.assertIsNotNone(entitlement["expires_at_ms"])
            time.sleep(0.04)
            usage={"schema":"entity-eep-usage-v1","usage_id":f"{prefix}-expired-usage","instrument_id":inst["instrument_id"],
                   "holder":self.buyer,"action":"TRAIN","units":1,"nonce":f"{prefix}-expired-usage-nonce","created_at_ms":int(time.time()*1000)}
            usage_sig=self.identity.sign(self.buyer,usage)
            with self.assertRaises(PermissionError): eep.submit_signed_usage(usage,usage_sig)

    def test_self_trade_is_blocked_and_alerted_in_both(self):
        for eep, venue, inst, prefix in (
            (*self.make_ref_exchange(), "r"),
            (*self.make_mirror_exchange(), "m"),
        ):
            iid, vid = inst["instrument_id"], venue["venue_id"]
            eep.submit_order(vid, iid, self.owner, "SELL", 5, 25, nonce=f"{prefix}-self-sell")
            eep.submit_order(vid, iid, self.owner, "BUY", 5, 25, nonce=f"{prefix}-self-buy")
            trades = eep.match_order_book(vid, iid)
            self.assertEqual(trades, [])
            alerts = eep.surveillance_alerts(vid)
            self.assertTrue(alerts)
            self.assertTrue(any("SELF_" in a["alert_type"] for a in alerts))

if __name__ == "__main__":
    unittest.main()
