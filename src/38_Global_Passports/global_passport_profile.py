from __future__ import annotations

CORE_PRIMITIVES=["ENTITY","AUTHORITY","RIGHT","EVENT","VALUE"]
MARKET_LIFECYCLE=["DCO","INSTRUMENT","LISTING","DISCLOSURE","ORDER_RFQ_AUCTION","PRICE_DISCOVERY","TRADE","CLEARING","SETTLEMENT","ENTITLEMENT","USAGE","DERIVED_OUTPUT","ECONOMIC_CONSEQUENCE"]
BUILTIN_PROFILE_REFS=["entity-profile:global@1.0","entity-profile:healthcare@1.0","entity-profile:finance@1.0","entity-profile:manufacturing@1.0","entity-profile:ai@1.0","entity-profile:robotics@1.0","entity-profile:defence-public@1.0"]

def passport_status()->dict:
    return {"schema":"entity-v3-global-passport-profile-status-v1","version":"3.4.0","core_primitives":CORE_PRIMITIVES,
            "core_semantics_changed":False,"market_engine_preserved":True,"market_lifecycle":MARKET_LIFECYCLE,
            "one_passport_many_profiles":True,"profile_composition":True,"continuous_provenance":True,
            "builtin_profile_refs":BUILTIN_PROFILE_REFS,"industry_profiles_do_not_create_silos":True,
            "external_standards_are_mapped_not_redefined":True,"profile_is_not_regulatory_compliance":True,
            "evidence_truth_boundary_preserved":True,"underlying_information_remains_nonrival":True,
            "doctrine":"One ENTITY Passport. Many jurisdictions, industries, standards and contexts. No new sovereignty silos."}
