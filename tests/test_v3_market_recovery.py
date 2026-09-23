import copy
import hashlib
import importlib.util
import pathlib
import sqlite3
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


identity_mod = load("mr_identity", REPO / "src/01_Core_Runtime/identity/canonical_identity.py")
fabric_mod = load("mr_fabric", REPO / "src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
eep_mod = load("mr_eep", REPO / "src/32_V3_Hardening/exchange_protocol.py")
econ_mod = load("mr_econ", REPO / "src/33_Economic_Participation/economic_participation.py")
recovery_mod = load("mr_recovery", REPO / "src/34_Market_Recovery/market_recovery.py")


class MarketRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.identity = identity_mod.EntityIdentityVault(self.root)
        self.originator = self.identity.create("Originator", "business")["entity_id"]
        self.treasury_entity = self.identity.create("Treasury", "business")["entity_id"]
        self.buyer = self.identity.create("Buyer", "business")["entity_id"]
        self.verifier = self.identity.create("Verifier", "system")["entity_id"]
        self.fabric = fabric_mod.UniversalTransactionFabric(self.root, self.identity)
        self.exchange = eep_mod.ExchangeProtocol(self.root, self.identity, self.fabric)
        self.econ = econ_mod.EconomicParticipationProfile(self.root, self.identity)
        self.asset = self.fabric.register_digital_commodity(
            self.originator, "Recovery Corpus", hashlib.sha256(b"recovery-corpus").hexdigest()
        )
        self.instrument = self.exchange.define_instrument(
            self.originator, self.asset["object_id"], "SPOT_LICENSE",
            {"actions": ["DERIVE", "TRAIN"], "raw_redistribution": False},
            1000, "CAD", transferable=True, duration_ms=86_400_000,
        )
        self.treasury = self.econ.create_treasury(
            self.originator, self.treasury_entity, "Treasury", "CA",
            hashlib.sha256(b"treasury-policy").hexdigest(),
        )
        self.econ.authorize_settlement_verifier(
            self.treasury["treasury_id"], self.originator, self.verifier
        )
        self.policy = self.econ.define_participation(
            self.originator, self.treasury["treasury_id"], self.instrument["instrument_id"],
            1000, 200, "CAD", primary_treasury_bps=2500,
            secondary_royalty_bps=150, derivative_participation_bps=100,
            terms={"raw_redistribution": "PROHIBITED"},
        )
        self.econ.allocate_eep_reserve(self.exchange, self.policy["policy_id"])
        self.venue = self.exchange.create_venue(
            self.originator, "Recovery Venue", "CA", ["ORDER_BOOK", "RFQ"],
            hashlib.sha256(b"venue-policy").hexdigest(),
        )
        disclosure = hashlib.sha256(b"market-disclosure").hexdigest()
        self.exchange.publish_disclosure(
            self.venue["venue_id"], self.instrument["instrument_id"],
            self.originator, "OFFERING", disclosure,
        )
        self.exchange.list_instrument(
            self.venue["venue_id"], self.instrument["instrument_id"], self.originator,
            1, 1, disclosure,
        )
        self.exchange.set_revenue_rules(
            self.instrument["instrument_id"], self.originator,
            {self.originator: 150, self.treasury_entity: 50}, nonce="recovery-rules",
        )
        sell = self.exchange.submit_order(
            self.venue["venue_id"], self.instrument["instrument_id"], self.originator,
            "SELL", 10, 100, "recovery-sell",
        )
        buy = self.exchange.submit_order(
            self.venue["venue_id"], self.instrument["instrument_id"], self.buyer,
            "BUY", 10, 100, "recovery-buy",
        )
        self.assertEqual(sell["status"], "OPEN")
        self.assertEqual(buy["status"], "OPEN")
        trade = self.exchange.match_order_book(
            self.venue["venue_id"], self.instrument["instrument_id"]
        )[0]
        payment_ref = "bank:recovery-1"
        attestation = self.exchange.attest_payment(
            trade["trade_id"], self.buyer, payment_ref,
            hashlib.sha256(b"bank-evidence").hexdigest(), nonce="recovery-payment-attestation",
        )
        self.exchange.settle_trade(
            trade["trade_id"], payment_ref,
            external_verified=True, payment_attestation_id=attestation["attestation_id"],
        )
        self.trade_id = trade["trade_id"]
        captured = self.econ.capture_settled_eep_trade(self.exchange, self.trade_id)
        self.obligation_id = captured["obligation"]["obligation_id"]
        self.econ.settle_obligation(
            self.obligation_id, self.verifier, "treasury-bank:1", external_verified=True,
            evidence_sha256=hashlib.sha256(b"treasury-bank-evidence").hexdigest(),
        )
        self.econ.record_service_revenue(
            self.treasury["treasury_id"], self.buyer, "MARKET_DATA", 300, "CAD",
            "invoice:market-data-recovery",
        )
        self.exchange.meter_usage(
            self.instrument["instrument_id"], self.buyer, "TRAIN", 2, "recovery-usage"
        )
        self.econ.seal_snapshot(
            self.treasury["treasury_id"], self.originator, self.exchange
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _export(self):
        core = self.fabric.export_bundle(self.asset["object_id"])
        return recovery_mod.MarketStateRecovery.export(
            self.exchange.path, self.econ.path, self.identity, core_bundles=[core]
        )

    def test_bundle_verifies_without_source_private_keys(self):
        bundle = self._export()
        result = recovery_mod.MarketStateRecovery.verify(
            bundle,
            verify_manifest=identity_mod.EntityIdentityVault.verify_manifest,
            verify_signature=identity_mod.EntityIdentityVault.verify_signature,
            verify_core_bundle=self.fabric.verify_bundle,
        )
        self.assertTrue(result["valid"], result["failures"])
        self.assertTrue(result["logical_state_not_database_bytes"])
        self.assertGreater(result["embedded_manifest_count"], 0)
        self.assertEqual(
            result["exchange_state_sha256"], bundle["exchange"]["state_sha256"]
        )

    def test_tampered_market_state_fails_closed(self):
        bundle = self._export()
        tampered = copy.deepcopy(bundle)
        rows = tampered["exchange"]["tables"]["balances"]["rows"]
        self.assertTrue(rows)
        rows[0]["units"] += 1
        result = recovery_mod.MarketStateRecovery.verify(
            tampered,
            verify_manifest=identity_mod.EntityIdentityVault.verify_manifest,
            verify_signature=identity_mod.EntityIdentityVault.verify_signature,
            verify_core_bundle=self.fabric.verify_bundle,
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any(x.startswith("table_hash_invalid:exchange:balances") for x in result["failures"]))
        self.assertIn("bundle_semantic_hash_invalid", result["failures"])

    def test_rehashed_tamper_still_fails_controller_signatures(self):
        bundle = self._export()
        tampered = copy.deepcopy(bundle)
        balance = tampered["exchange"]["tables"]["balances"]
        balance["rows"][0]["units"] += 7
        balance["semantic_sha256"] = recovery_mod.semantic_sha256(
            recovery_mod._table_payload(balance)
        )
        tampered["exchange"]["state_sha256"] = recovery_mod.semantic_sha256(
            {"tables": tampered["exchange"]["tables"]}
        )
        semantic = {
            k: v for k, v in tampered.items()
            if k not in {"exported_at_ms", "semantic_sha256", "bundle_attestations"}
        }
        tampered["semantic_sha256"] = recovery_mod.semantic_sha256(semantic)
        for attestation in tampered["bundle_attestations"]:
            attestation["semantic_sha256"] = tampered["semantic_sha256"]
        result = recovery_mod.MarketStateRecovery.verify(
            tampered,
            verify_manifest=identity_mod.EntityIdentityVault.verify_manifest,
            verify_signature=identity_mod.EntityIdentityVault.verify_signature,
            verify_core_bundle=self.fabric.verify_bundle,
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any(
            x.startswith("controller_attestation_signature_invalid:")
            for x in result["failures"]
        ))

    def test_destructive_market_database_recovery_preserves_state_roots(self):
        bundle = self._export()
        expected_exchange = bundle["exchange"]["state_sha256"]
        expected_economic = bundle["economic_participation"]["state_sha256"]
        self.exchange.path.unlink()
        self.econ.path.unlink()

        restored_exchange = eep_mod.ExchangeProtocol(self.root, self.identity, self.fabric)
        restored_econ = econ_mod.EconomicParticipationProfile(self.root, self.identity)
        result = recovery_mod.MarketStateRecovery.restore(
            bundle, restored_exchange.path, restored_econ.path,
            verify_manifest=identity_mod.EntityIdentityVault.verify_manifest,
            verify_signature=identity_mod.EntityIdentityVault.verify_signature,
            verify_core_bundle=self.fabric.verify_bundle,
        )
        self.assertTrue(result["restored"])
        self.assertTrue(result["atomic_cross_database_restore"])
        self.assertEqual(result["exchange_state_sha256"], expected_exchange)
        self.assertEqual(result["economic_state_sha256"], expected_economic)
        self.assertEqual(
            restored_exchange.balance(self.instrument["instrument_id"], self.buyer), 10
        )
        self.assertEqual(
            restored_exchange.balance(self.instrument["instrument_id"], self.treasury_entity), 200
        )
        with restored_exchange._db() as db:
            trade = db.execute(
                "SELECT status FROM trades WHERE trade_id=?", (self.trade_id,)
            ).fetchone()
            entitlements = db.execute(
                "SELECT COUNT(*) FROM entitlements WHERE trade_id=?", (self.trade_id,)
            ).fetchone()[0]
            attestations = db.execute(
                "SELECT COUNT(*) FROM payment_attestations WHERE trade_id=?", (self.trade_id,)
            ).fetchone()[0]
            usage = db.execute(
                "SELECT COUNT(*) FROM usage WHERE instrument_id=? AND holder=?",
                (self.instrument["instrument_id"], self.buyer),
            ).fetchone()[0]
        self.assertEqual(trade["status"], "SETTLED")
        self.assertEqual(entitlements, 1)
        self.assertEqual(attestations, 1)
        self.assertEqual(usage, 1)

        with restored_econ._db() as db:
            statuses = [r[0] for r in db.execute(
                "SELECT status FROM obligations ORDER BY obligation_id"
            ).fetchall()]
        self.assertIn("SETTLED", statuses)
        self.assertIn("ACCRUED", statuses)

    def test_restore_refuses_nonempty_destination(self):
        bundle = self._export()
        target_root = self.root / "nonempty-target"
        target_root.mkdir()
        target_exchange = eep_mod.ExchangeProtocol(target_root, self.identity, self.fabric)
        target_econ = econ_mod.EconomicParticipationProfile(target_root, self.identity)
        with target_exchange._db() as db:
            db.execute(
                "INSERT INTO balances(instrument_id,holder,units) VALUES(?,?,?)",
                ("inst-existing", "holder-existing", 1),
            )
        with self.assertRaises(ValueError):
            recovery_mod.MarketStateRecovery.restore(
                bundle, target_exchange.path, target_econ.path,
                verify_manifest=identity_mod.EntityIdentityVault.verify_manifest,
                verify_signature=identity_mod.EntityIdentityVault.verify_signature,
                verify_core_bundle=self.fabric.verify_bundle,
            )
        with target_exchange._db() as db:
            self.assertEqual(
                db.execute("SELECT units FROM balances WHERE instrument_id='inst-existing'").fetchone()[0],
                1,
            )

    def test_cross_database_restore_rolls_back_on_eopp_failure(self):
        bundle = self._export()
        target_root = self.root / "rollback-target"
        target_root.mkdir()
        target_exchange = eep_mod.ExchangeProtocol(target_root, self.identity, self.fabric)
        target_econ = econ_mod.EconomicParticipationProfile(target_root, self.identity)
        with target_econ._db() as db:
            db.execute(
                "CREATE TRIGGER fail_restore_obligation BEFORE INSERT ON obligations "
                "BEGIN SELECT RAISE(ABORT,'forced recovery failure'); END"
            )
        with self.assertRaises(sqlite3.DatabaseError):
            recovery_mod.MarketStateRecovery.restore(
                bundle, target_exchange.path, target_econ.path,
                verify_manifest=identity_mod.EntityIdentityVault.verify_manifest,
                verify_signature=identity_mod.EntityIdentityVault.verify_signature,
                verify_core_bundle=self.fabric.verify_bundle,
            )
        with target_exchange._db() as db:
            for table in recovery_mod.EEP_REQUIRED:
                self.assertEqual(
                    db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0], 0,
                    table,
                )
        with target_econ._db() as db:
            for table in recovery_mod.EOPP_REQUIRED:
                self.assertEqual(
                    db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0], 0,
                    table,
                )


    def test_market_recovery_evidence_manifest_self_verifies(self):
        path = REPO / "ENTITY_V3_MARKET_RECOVERY_MANIFEST.json"
        evidence = __import__("json").loads(path.read_text(encoding="utf-8"))
        for entry in evidence["files"]:
            actual = hashlib.sha256((REPO / entry["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, entry["sha256"], entry["path"])
        base = {k: v for k, v in evidence.items() if k not in {"files", "snapshot_sha256"}}
        seed = __import__("json").dumps(
            base, sort_keys=True, separators=(",", ":")
        ).encode() + b"\n"
        seed += b"\n".join(
            (entry["path"] + " " + entry["sha256"]).encode()
            for entry in evidence["files"]
        )
        self.assertEqual(hashlib.sha256(seed).hexdigest(), evidence["snapshot_sha256"])


if __name__ == "__main__":
    unittest.main()
