from __future__ import annotations

from .bond_algebra import BondAlgebra, BondFamily, FirstClassBond, TimeScope, ValenceConstraint
from .physics import (
    AtomicPhysicsKernel, BondTemplate, ConstitutionalLaw, HyperBondTemplate,
    ReactionDefinition, ReactionIntent,
)


def build_equipment_physics() -> AtomicPhysicsKernel:
    algebra = BondAlgebra()
    kernel = AtomicPhysicsKernel(algebra)
    for entity_id, entity_type in [
        ("SHAWN", "PERSON"), ("SUPERVISOR", "PERSON"), ("EX12", "EQUIPMENT"),
        ("YARD", "LOCATION"), ("P204", "PROJECT"), ("WO88", "WORK_ORDER"),
        ("EVIDENCE1", "EVIDENCE"),
    ]:
        kernel.declare_entity(entity_id, entity_type)
    algebra.register_constraint(ValenceConstraint(
        "ASSIGNED_TO", ("EQUIPMENT",), ("PROJECT",), maximum=1,
        families=(BondFamily.OPERATIONAL,), require_evidence=True,
    ))
    algebra.register_constraint(ValenceConstraint(
        "AVAILABLE_AT", ("EQUIPMENT",), ("LOCATION",), maximum=1,
        families=(BondFamily.OPERATIONAL,), require_evidence=True,
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
        ConstitutionalLaw("assignment_evidence", "evidence_required_for_predicate", {"predicate": "ASSIGNED_TO"}),
        ConstitutionalLaw("availability_evidence", "evidence_required_for_predicate", {"predicate": "AVAILABLE_AT"}),
    ]:
        kernel.register_law(law)
    common_laws = ("identity", "history", "authority", "changed", "independent")
    kernel.register_reaction(ReactionDefinition(
        "ASSIGN_EQUIPMENT",
        required=(BondTemplate("$equipment", "AVAILABLE_AT", "$location", BondFamily.OPERATIONAL),),
        break_bonds=(BondTemplate("$equipment", "AVAILABLE_AT", "$location", BondFamily.OPERATIONAL),),
        form_bonds=(BondTemplate("$equipment", "ASSIGNED_TO", "$project", BondFamily.OPERATIONAL, require_evidence_var="evidence"),),
        form_hyperbond=HyperBondTemplate("ASSIGNMENT_EVENT", (
            ("ACTOR", "$actor"), ("EQUIPMENT", "$equipment"), ("DESTINATION", "$project"),
            ("AUTHORITY", "$work_order"), ("APPROVER", "$approver"),
        )),
        required_capabilities=("ASSIGN_EQUIPMENT",),
        laws=(*common_laws, "assignment_evidence"),
    ))
    kernel.register_reaction(ReactionDefinition(
        "RELEASE_EQUIPMENT",
        required=(BondTemplate("$equipment", "ASSIGNED_TO", "$project", BondFamily.OPERATIONAL),),
        break_bonds=(BondTemplate("$equipment", "ASSIGNED_TO", "$project", BondFamily.OPERATIONAL),),
        form_bonds=(BondTemplate("$equipment", "AVAILABLE_AT", "$location", BondFamily.OPERATIONAL, require_evidence_var="evidence"),),
        form_hyperbond=HyperBondTemplate("RELEASE_EVENT", (
            ("ACTOR", "$actor"), ("EQUIPMENT", "$equipment"), ("SOURCE", "$project"),
            ("DESTINATION", "$location"), ("AUTHORITY", "$work_order"),
        )),
        required_capabilities=("RELEASE_EQUIPMENT",),
        laws=(*common_laws, "availability_evidence"),
    ))
    return kernel


def assignment_intent(kernel: AtomicPhysicsKernel) -> ReactionIntent:
    return ReactionIntent(
        "ASSIGN_EQUIPMENT",
        {"equipment": "EX12", "location": "YARD", "project": "P204", "actor": "SHAWN",
         "work_order": "WO88", "approver": "SUPERVISOR", "evidence": "EVIDENCE1"},
        actor="SHAWN", authority="OPS", capabilities=("ASSIGN_EQUIPMENT",), expected_root=kernel.root,
        proposer="PLANNER", approvers=("SUPERVISOR",),
    )


def release_intent(kernel: AtomicPhysicsKernel) -> ReactionIntent:
    return ReactionIntent(
        "RELEASE_EQUIPMENT",
        {"equipment": "EX12", "location": "YARD", "project": "P204", "actor": "SHAWN",
         "work_order": "WO88", "evidence": "EVIDENCE1"},
        actor="SHAWN", authority="OPS", capabilities=("RELEASE_EQUIPMENT",), expected_root=kernel.root,
        proposer="PLANNER", approvers=("SUPERVISOR",),
    )
