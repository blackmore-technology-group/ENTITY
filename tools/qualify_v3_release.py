from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
TRADES_PER_IMPLEMENTATION = 250


def load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def setup_modules():
    identity = load("rel_identity", REPO / "src/01_Core_Runtime/identity/canonical_identity.py")
    fabric = load("rel_fabric", REPO / "src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
    reference = load("rel_eep_reference", REPO / "src/31_Profiles/exchange_protocol.py")
    mirror = load("rel_eep_mirror", REPO / "src/32_V3_Hardening/exchange_protocol.py")
    return identity, fabric, reference, mirror

def build_exchange(eep_cls, root, vault, fabric, owner, dco, label):
    root.mkdir(parents=True, exist_ok=True)
    eep = eep_cls(root, vault, fabric)
    venue = eep.create_venue(
        owner, f"{label} Release Venue", "CA", ["ORDER_BOOK", "RFQ"],
        hashlib.sha256(f"{label}-policy".encode()).hexdigest(),
    )
    instrument = eep.define_instrument(
        owner, dco["object_id"], "SPOT_LICENSE",
        {"actions": ["TRAIN", "DERIVE"], "raw_redistribution": False},
        TRADES_PER_IMPLEMENTATION + 100, "CAD", transferable=True,
    )
    disclosure = eep.publish_disclosure(
        venue["venue_id"], instrument["instrument_id"], owner, "LISTING",
        hashlib.sha256(f"{label}-disclosure".encode()).hexdigest(),
    )
    eep.list_instrument(
        venue["venue_id"], instrument["instrument_id"], owner,
        min_lot=1, tick_size=1, disclosure_sha256=disclosure["content_sha256"],
    )
    return eep, venue, instrument

def exercise(eep, venue, instrument, owner, buyer, prefix):
    start = time.perf_counter()
    completed = 0
    for i in range(TRADES_PER_IMPLEMENTATION):
        eep.submit_order(
            venue["venue_id"], instrument["instrument_id"], owner,
            "SELL", 1, 100 + (i % 7), nonce=f"{prefix}-sell-{i}",
        )
        eep.submit_order(
            venue["venue_id"], instrument["instrument_id"], buyer,
            "BUY", 1, 106, nonce=f"{prefix}-buy-{i}",
        )
        trades = eep.match_order_book(venue["venue_id"], instrument["instrument_id"])
        if len(trades) != 1:
            raise AssertionError(f"expected one trade at iteration {i}, got {len(trades)}")
        eep.settle_trade(trades[0]["trade_id"], payment_ref=f"{prefix}-pay-{i}")
        completed += 1
    elapsed = time.perf_counter() - start
    if eep.balance(instrument["instrument_id"], buyer) != completed:
        raise AssertionError("buyer balance does not equal settled trade count")
    return {"trades": completed, "elapsed_seconds": round(elapsed, 3),
            "trades_per_second": round(completed / elapsed, 3)}

def main():
    identity_mod, fabric_mod, ref_mod, mirror_mod = setup_modules()
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        vault = identity_mod.EntityIdentityVault(root)
        fabric = fabric_mod.UniversalTransactionFabric(root, vault)
        owner = vault.create("Release Owner", "business")["entity_id"]
        buyer = vault.create("Release Buyer", "business")["entity_id"]
        dco = fabric.register_digital_commodity(
            owner, "Release Qualification Corpus", hashlib.sha256(b"release-corpus").hexdigest()
        )
        results = {}
        for label, cls in (("reference", ref_mod.ExchangeProtocol), ("mirror", mirror_mod.ExchangeProtocol)):
            eep, venue, inst = build_exchange(cls, root / label, vault, fabric, owner, dco, label)
            results[label] = exercise(eep, venue, inst, owner, buyer, label)
        payload = {
            "schema": "entity-v3-release-load-qualification-v1",
            "qualified": all(v["trades"] == TRADES_PER_IMPLEMENTATION for v in results.values()),
            "trades_per_implementation": TRADES_PER_IMPLEMENTATION,
            "total_settled_trades": sum(v["trades"] for v in results.values()),
            "implementations": results,
            "scope": "bounded local release-load qualification; not production capacity certification",
        }
        print(json.dumps(payload, sort_keys=True, indent=2))
        return 0 if payload["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
