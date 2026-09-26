from __future__ import annotations

from dataclasses import dataclass

from .bond_algebra import BondFamily


@dataclass(frozen=True)
class BondPredicateSpec:
    name: str
    family: BondFamily
    description: str
    temporal: bool = True
    recursive: bool = True
    executable: bool = False
    requires_evidence: bool = False
    probabilistic: bool = False


_STANDARD = {
    BondFamily.STRUCTURAL: ("CONTAINS", "PRECEDES", "PART_OF", "ENCODED_AS", "RECONSTRUCTED_FROM", "DEPENDS_ON"),
    BondFamily.SEMANTIC: ("IS_A", "HAS_PROPERTY", "WORKS_ON", "LOCATED_IN", "REPRESENTS", "HAS_IDENTITY"),
    BondFamily.TEMPORAL: ("VALID_FROM", "VALID_UNTIL", "PRECEDED_BY", "SUPERSEDES", "CONCURRENT_WITH"),
    BondFamily.CAUSAL: ("CAUSED", "ENABLED", "PREVENTED", "CONTRIBUTED_TO", "RESULTED_IN"),
    BondFamily.EVIDENTIARY: ("SUPPORTED_BY", "OBSERVED_IN", "DERIVED_FROM", "CONTRADICTED_BY", "VERIFIED_BY"),
    BondFamily.COGNITIVE: ("PREDICTS", "BELIEVES", "ATTENDS_TO", "ABSTRACTS", "PLANS", "EXPLAINS"),
    BondFamily.OPERATIONAL: ("CAN_EXECUTE", "REQUIRES", "BREAKS", "FORMS", "TRANSFORMS", "ROLLS_BACK"),
    BondFamily.SECURITY: ("AUTHORIZED_BY", "VISIBLE_TO", "RESTRICTED_TO", "REQUIRES_PURPOSE", "REDACTED_FROM"),
    BondFamily.PROBABILISTIC: ("LIKELY_CAUSES", "POSSIBLY_RELATED", "PREDICTED_NEXT", "UNCERTAIN_IDENTITY"),
}


def default_bond_periodic_table() -> dict[str, BondPredicateSpec]:
    table: dict[str, BondPredicateSpec] = {}
    for family, predicates in _STANDARD.items():
        for predicate in predicates:
            table[predicate] = BondPredicateSpec(
                predicate,
                family,
                f"ADAM standard {family.value} bond {predicate}",
                executable=family is BondFamily.OPERATIONAL,
                requires_evidence=family in {BondFamily.CAUSAL, BondFamily.EVIDENTIARY},
                probabilistic=family is BondFamily.PROBABILISTIC,
            )
    return table


STANDARD_BOND_TABLE = default_bond_periodic_table()
