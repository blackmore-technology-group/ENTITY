from __future__ import annotations
from typing import Any
import hashlib, json, time

DOCTRINE_ID = "ENTITY-DATA-ECONOMIC-SOVEREIGNTY"
PROFILE_ID = "DATA-ECONOMIC-SOVEREIGNTY"
PROFILE_VERSION = "1.0"
SCARCITY_SOURCES = {
    "RIGHT", "ENTITLEMENT", "CAPACITY", "DURATION", "JURISDICTION",
    "USAGE_QUANTITY", "DERIVATION", "PARTICIPATION", "TRANSFERABILITY",
}

def now_ms() -> int: return int(time.time() * 1000)
def canon(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
def sha(v: Any) -> str:
    return hashlib.sha256(v if isinstance(v, (bytes, bytearray)) else canon(v)).hexdigest()
def require_sha256(v: str) -> str:
    s = str(v or "").lower()
    if len(s) != 64 or any(c not in "0123456789abcdef" for c in s): raise ValueError("SHA-256 required")
    return s

class DataEconomicSovereignty:
    """Machine-enforced doctrine for data as productive capital without byte scarcity."""
    @staticmethod
    def doctrine_status() -> dict:
        return {
            "schema": "entity-v3-data-economic-sovereignty-status-v1",
            "doctrine_id": DOCTRINE_ID,
            "profile_id": PROFILE_ID,
            "profile_version": PROFILE_VERSION,
            "data_may_be_productive_capital": True,
            "artificial_information_scarcity_required": False,
            "scarcity_may_exist_in_bounded_economic_interests": True,
            "originator_participation_requires_validly_established_terms": True,
            "provenance_must_link_information_right_use_derivative_value": True,
            "protocol_determines_legal_title": False,
            "protocol_determines_fair_value": False,
            "protocol_determines_regulatory_classification": False,
        }

    @staticmethod
    def declare_digital_capital(dco_ref: str, originator_entity_id: str,
                                provenance_root: str, content_sha256: str,
                                *, asset_class="DATA", metadata=None) -> dict:
        if not str(dco_ref): raise ValueError("DCO reference required")
        if not str(originator_entity_id): raise ValueError("originator required")
        return {
            "schema": "entity-v3-data-economic-capital-v1",
            "dco_ref": str(dco_ref), "originator_entity_id": str(originator_entity_id),
            "asset_class": str(asset_class).upper(), "provenance_root": require_sha256(provenance_root),
            "content_sha256": require_sha256(content_sha256), "metadata": dict(metadata or {}),
            "information_bytes_are_not_declared_scarce": True, "created_at_ms": now_ms(),
        }

    @staticmethod
    def define_bounded_interest(capital_record: dict, holder_entity_id: str, *,
                                actions: list[str], quantity: int | None = None,
                                duration_ms: int | None = None, jurisdiction: str | None = None,
                                transferable=False, derivation_allowed=False,
                                participation_bps=0, additional_bounds=None) -> dict:
        if capital_record.get("schema") != "entity-v3-data-economic-capital-v1":
            raise ValueError("data economic capital record required")
        acts = sorted({str(a).upper() for a in actions if str(a).strip()})
        if not acts: raise ValueError("at least one economic right action required")
        if quantity is not None and int(quantity) < 1: raise ValueError("quantity must be positive")
        if duration_ms is not None and int(duration_ms) < 1: raise ValueError("duration must be positive")
        participation = int(participation_bps)
        if participation < 0 or participation > 10000: raise ValueError("participation_bps must be 0..10000")
        bounds = dict(additional_bounds or {})
        sources = {"RIGHT"}
        if quantity is not None: sources.add("USAGE_QUANTITY")
        if duration_ms is not None: sources.add("DURATION")
        if jurisdiction: sources.add("JURISDICTION")
        if transferable: sources.add("TRANSFERABILITY")
        if derivation_allowed: sources.add("DERIVATION")
        if participation: sources.add("PARTICIPATION")
        body = {
            "schema": "entity-v3-bounded-economic-interest-v1",
            "interest_id": "interest3-" + sha([capital_record["dco_ref"], holder_entity_id, acts, quantity,
                                                duration_ms, jurisdiction, transferable, derivation_allowed,
                                                participation, bounds])[:24],
            "dco_ref": capital_record["dco_ref"], "holder_entity_id": str(holder_entity_id),
            "actions": acts, "quantity": None if quantity is None else int(quantity),
            "duration_ms": None if duration_ms is None else int(duration_ms),
            "jurisdiction": None if jurisdiction is None else str(jurisdiction).upper(),
            "transferable": bool(transferable), "derivation_allowed": bool(derivation_allowed),
            "participation_bps": participation, "additional_bounds": bounds,
            "scarcity_sources": sorted(sources), "underlying_information_remains_nonrival": True,
            "created_at_ms": now_ms(),
        }
        return body

    @staticmethod
    def validate_interest(interest: dict) -> dict:
        failures = []
        if interest.get("schema") != "entity-v3-bounded-economic-interest-v1": failures.append("wrong_schema")
        actions = interest.get("actions") or []
        if not actions or actions != sorted(set(actions)): failures.append("actions_not_canonical")
        sources = set(interest.get("scarcity_sources") or [])
        if not sources or not sources.issubset(SCARCITY_SOURCES): failures.append("invalid_scarcity_source")
        if "RIGHT" not in sources: failures.append("right_boundary_missing")
        if interest.get("underlying_information_remains_nonrival") is not True:
            failures.append("information_scarcity_asserted")
        q = interest.get("quantity")
        if q is not None and (type(q) is not int or q < 1): failures.append("invalid_quantity")
        d = interest.get("duration_ms")
        if d is not None and (type(d) is not int or d < 1): failures.append("invalid_duration")
        p = interest.get("participation_bps")
        if type(p) is not int or p < 0 or p > 10000: failures.append("invalid_participation")
        return {"valid": not failures, "failures": failures,
                "information_scarcity_required": False,
                "economic_scarcity_is_rights_based": True}

    @staticmethod
    def bind_economic_consequence(*, dco_ref: str, interest_id: str, use_event_ref: str,
                                  derivative_ref: str | None, value_ref: str,
                                  evidence_sha256: str, methodology_ref: str | None = None) -> dict:
        required = {"dco_ref": dco_ref, "interest_id": interest_id,
                    "use_event_ref": use_event_ref, "value_ref": value_ref}
        if any(not str(v) for v in required.values()): raise ValueError("complete economic chain required")
        return {
            "schema": "entity-v3-data-economic-consequence-v1",
            "dco_ref": str(dco_ref), "interest_id": str(interest_id),
            "use_event_ref": str(use_event_ref), "derivative_ref": derivative_ref,
            "value_ref": str(value_ref), "evidence_sha256": require_sha256(evidence_sha256),
            "methodology_ref": methodology_ref, "created_at_ms": now_ms(),
            "provenance_chain_complete": True,
            "economic_consequence_is_evidence_not_objective_truth": True,
            "legal_title_not_determined": True, "fair_value_not_determined": True,
            "regulatory_classification_not_determined": True,
        }

    @staticmethod
    def validate_market_instrument(instrument: dict, interest: dict) -> dict:
        failures = []
        iv = DataEconomicSovereignty.validate_interest(interest)
        failures.extend(iv["failures"])
        rights = dict(instrument.get("rights") or {})
        actions = rights.get("actions") or []
        if not actions: failures.append("instrument_rights_missing")
        if sorted(set(str(a).upper() for a in actions)) != interest.get("actions"):
            failures.append("instrument_interest_rights_mismatch")
        if int(instrument.get("total_units") or 0) < 1: failures.append("instrument_units_invalid")
        if instrument.get("underlying_data_ownership_transferred") is True:
            failures.append("instrument_silently_transfers_data_ownership")
        if instrument.get("protocol_declares_fair_value") is True:
            failures.append("protocol_fair_value_claim_prohibited")
        if instrument.get("protocol_declares_regulatory_classification") is True:
            failures.append("protocol_classification_claim_prohibited")
        return {"valid": not failures, "failures": failures,
                "tradable_object": "BOUNDED_RIGHT_OR_ENTITLEMENT",
                "underlying_information_is_not_the_scarce_unit": True}

    @staticmethod
    def doctrine_invariants() -> tuple[str, ...]:
        return (
            "DATA_MAY_BE_PRODUCTIVE_CAPITAL",
            "INFORMATION_SCARCITY_NOT_REQUIRED",
            "SCARCITY_MUST_BE_EXPLICITLY_BOUNDED",
            "ORIGINATOR_PARTICIPATION_MUST_BE_ESTABLISHED_BY_TERMS",
            "PROVENANCE_LINKS_RIGHT_USE_DERIVATION_VALUE",
            "PROTOCOL_DOES_NOT_DETERMINE_LEGAL_TITLE",
            "PROTOCOL_DOES_NOT_DETERMINE_FAIR_VALUE",
            "PROTOCOL_DOES_NOT_DETERMINE_REGULATORY_CLASSIFICATION",
        )
