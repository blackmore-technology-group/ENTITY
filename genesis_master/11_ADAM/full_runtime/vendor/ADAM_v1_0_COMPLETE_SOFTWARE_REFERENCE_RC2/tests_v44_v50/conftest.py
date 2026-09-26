from __future__ import annotations

import pytest

from adam_v44 import (
    AtomicPhysicsKernel, BondAlgebra, BondFamily, BondTemplate, ConstitutionalLaw,
    FirstClassBond, HyperBondTemplate, ReactionDefinition, TimeScope, ValenceConstraint,
)


@pytest.fixture
def assignment_kernel():
    algebra = BondAlgebra()
    kernel = AtomicPhysicsKernel(algebra)
    for entity_id, entity_type in [
        ("SHAWN", "PERSON"),
        ("SUPERVISOR", "PERSON"),
        ("EX12", "EQUIPMENT"),
        ("YARD", "LOCATION"),
        ("P204", "PROJECT"),
        ("WO88", "WORK_ORDER"),
        ("EVIDENCE1", "EVIDENCE"),
    ]:
        kernel.declare_entity(entity_id, entity_type)
    algebra.register_constraint(ValenceConstraint(
        predicate="ASSIGNED_TO", source_types=("EQUIPMENT",), target_types=("PROJECT",),
        maximum=1, families=(BondFamily.OPERATIONAL,), require_evidence=True,
    ))
    algebra.register_constraint(ValenceConstraint(
        predicate="AVAILABLE_AT", source_types=("EQUIPMENT",), target_types=("LOCATION",),
        maximum=1, families=(BondFamily.OPERATIONAL,),
    ))
    kernel.seed_bond(FirstClassBond(
        "EX12", "AVAILABLE_AT", "YARD", BondFamily.OPERATIONAL,
        authority="OPS", time=TimeScope(0), supporting_evidence=("EVIDENCE1",),
    ))
    for law in [
        ConstitutionalLaw("identity", "identity_conservation"),
        ConstitutionalLaw("history", "history_conservation"),
        ConstitutionalLaw("authority", "authority_required"),
        ConstitutionalLaw("changed", "root_changed"),
        ConstitutionalLaw("independent", "no_model_self_approval"),
        ConstitutionalLaw("evidence", "evidence_required_for_predicate", {"predicate": "ASSIGNED_TO"}),
    ]:
        kernel.register_law(law)
    kernel.register_reaction(ReactionDefinition(
        name="ASSIGN_EQUIPMENT",
        required=(BondTemplate("$equipment", "AVAILABLE_AT", "$location", BondFamily.OPERATIONAL),),
        forbidden=(BondTemplate("$equipment", "ASSIGNED_TO", "$project", BondFamily.OPERATIONAL),),
        break_bonds=(BondTemplate("$equipment", "AVAILABLE_AT", "$location", BondFamily.OPERATIONAL),),
        form_bonds=(BondTemplate("$equipment", "ASSIGNED_TO", "$project", BondFamily.OPERATIONAL, require_evidence_var="evidence"),),
        form_hyperbond=HyperBondTemplate("ASSIGNMENT_EVENT", (
            ("ACTOR", "$actor"), ("EQUIPMENT", "$equipment"), ("DESTINATION", "$project"),
            ("AUTHORITY", "$work_order"), ("APPROVER", "$approver"),
        )),
        required_capabilities=("ASSIGN_EQUIPMENT",),
        laws=("identity", "history", "authority", "changed", "independent", "evidence"),
    ))
    return kernel
