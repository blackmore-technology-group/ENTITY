from __future__ import annotations

ADOPTION_VERSION = "3.2.0"
CORE_PRIMITIVES = ("ENTITY", "AUTHORITY", "RIGHT", "EVENT", "VALUE")
MARKET_LIFECYCLE = (
    "DCO", "INSTRUMENT", "LISTING", "DISCLOSURE", "ORDER_RFQ_AUCTION",
    "PRICE_DISCOVERY", "TRADE", "CLEARING", "SETTLEMENT", "ENTITLEMENT",
    "USAGE", "DERIVED_OUTPUT", "ECONOMIC_CONSEQUENCE",
)
CONFORMANCE_LANGUAGES = ("RUST", "TYPESCRIPT", "CSHARP", "GO", "SWIFT", "JAVA")
EXCHANGE_API = {
    "POST /instruments": "define/submit rights instrument",
    "POST /listings": "publish instrument listing",
    "POST /orders": "submit signed order",
    "POST /rfq": "create request for quote",
    "POST /auctions": "execute call-auction profile",
    "POST /settlements": "settle executed trade",
    "GET /positions": "query rights-unit balances/entitlements",
    "GET /market-data": "query venue market observations",
}

class EntityAdoptionSDK:
    """Thin adoption facade. It composes existing v3 components without taking their authority."""
    def __init__(self, *, fabric=None, exchange=None, passport_registry=None,
                 rights_ontology=None, jurisdiction_registry=None,
                 federated_resolution=None, semantic_registry=None):
        self.fabric = fabric
        self.exchange = exchange
        self.passports = passport_registry
        self.rights_ontology = rights_ontology
        self.jurisdictions = jurisdiction_registry
        self.resolution = federated_resolution
        self.semantics = semantic_registry

    def issue_rights_passport(self, *args, **kwargs) -> dict:
        if self.passports is None:
            raise RuntimeError("rights passport registry not configured")
        return self.passports.issue(*args, **kwargs)

    def authorize(self, passport: dict, action: str, *, context: dict | None = None,
                  jurisdictions: list[str] | None = None, domain: str = "DATA") -> dict:
        context = dict(context or {})
        action = str(action).upper()
        if self.rights_ontology is None:
            raise RuntimeError("rights ontology not configured")
        rights = self.rights_ontology.evaluate(list(passport.get("rights") or []), action, context)
        jurisdiction = None
        if jurisdictions:
            if self.jurisdictions is None:
                raise RuntimeError("jurisdiction registry not configured")
            jurisdiction = self.jurisdictions.evaluate(jurisdictions, domain, action, context)
        final = rights["decision"]
        if jurisdiction and jurisdiction["decision"] == "DENY":
            final = "DENY"
        elif jurisdiction and jurisdiction["decision"] == "CONDITIONAL" and final == "ALLOW":
            final = "CONDITIONAL"
        return {
            "action": action, "decision": final, "rights_decision": rights,
            "jurisdiction_decision": jurisdiction, "deny_by_default": True,
            "sdk_does_not_create_authority": True,
        }

    def resolver_quorum(self, object_id: str, *, minimum_resolvers: int = 2) -> dict:
        if self.resolution is None:
            raise RuntimeError("federated resolution not configured")
        return self.resolution.resolve_quorum(object_id, minimum_resolvers=minimum_resolvers)

    def market_status(self) -> dict:
        if self.exchange is None:
            raise RuntimeError("exchange not configured")
        status = self.exchange.status()
        return {
            "market_engine_status": status,
            "market_lifecycle": list(MARKET_LIFECYCLE),
            "market_engine_preserved": True,
            "rights_are_traded_not_bytes": bool(status.get("rights_are_traded_not_bytes")),
        }

    @staticmethod
    def exchange_routes() -> dict[str, str]:
        return dict(EXCHANGE_API)

    @staticmethod
    def resolver_deployment(*, mode: str = "FEDERATED", minimum_resolvers: int = 2,
                            offline_verify: bool = True) -> dict:
        mode = str(mode).upper()
        if mode != "FEDERATED":
            raise ValueError("v3.2 adoption resolver deployment is federated")
        if int(minimum_resolvers) < 2:
            raise ValueError("independent resolver quorum must be at least two")
        return {
            "schema": "entity-v3-resolver-deployment-v1",
            "mode": "FEDERATED",
            "minimum_resolvers": int(minimum_resolvers),
            "offline_verify": bool(offline_verify),
            "resolver_is_not_authority": True,
            "single_provider_dependency_prohibited": True,
            "fail_closed": True,
        }

def legal_classification_assertion(jurisdiction: str, profile_ref: str, asserted_by: str,
                                   classification: str, *, evidence_refs: list[str] | None = None) -> dict:
    if not asserted_by or not classification:
        raise ValueError("classification assertion requires actor and classification")
    return {
        "schema": "entity-v3-legal-classification-assertion-v1",
        "jurisdiction": str(jurisdiction).upper(),
        "profile_ref": str(profile_ref),
        "asserted_by": str(asserted_by),
        "classification": str(classification).upper(),
        "evidence_refs": sorted(set(evidence_refs or [])),
        "classification_is_assertion_not_protocol_legal_truth": True,
    }

def adoption_status() -> dict:
    return {
        "schema": "entity-v3-adoption-profile-status-v1",
        "version": ADOPTION_VERSION,
        "core_primitives": list(CORE_PRIMITIVES),
        "core_semantics_changed": False,
        "market_engine_preserved": True,
        "market_lifecycle": list(MARKET_LIFECYCLE),
        "conformance_languages": list(CONFORMANCE_LANGUAGES),
        "capabilities": [
            "RIGHTS_PASSPORT", "STANDARDS_ADAPTERS", "CUSTODY_CONNECTORS",
            "DEVELOPER_SDK", "PROFILE_AND_ONTOLOGY_BINDINGS",
            "FEDERATED_RESOLVER_DEPLOYMENT", "PRIVACY_PROOF_BINDINGS", "EXCHANGE_API",
        ],
        "provider_custody_is_not_authority": True,
        "legal_classification_is_external_assertion": True,
        "information_bytes_need_not_be_scarce": True,
    }
