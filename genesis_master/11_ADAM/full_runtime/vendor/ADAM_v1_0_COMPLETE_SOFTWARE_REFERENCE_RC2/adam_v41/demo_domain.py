from __future__ import annotations

from .reactions import Condition, Effect, ReactionDefinition, ReactionEngine
from .schema import StateConstraint, TypeSpec, ValenceRule


def install_equipment_domain(engine: ReactionEngine) -> None:
    engine.register_type(
        TypeSpec(
            name="equipment",
            rules=(
                ValenceRule(
                    "status",
                    minimum=1,
                    maximum=1,
                    allowed_values=("AVAILABLE", "ASSIGNED"),
                    value_type="str",
                ),
                ValenceRule("location", minimum=0, maximum=1, value_type="str"),
                ValenceRule(
                    "assigned_to",
                    minimum=0,
                    maximum=1,
                    target_entity_types=("project",),
                    target_atom_kinds=(),
                ),
            ),
            constraints=(
                StateConstraint(
                    if_predicate="status",
                    if_value="AVAILABLE",
                    require_predicates=("location",),
                    forbid_predicates=("assigned_to",),
                ),
                StateConstraint(
                    if_predicate="status",
                    if_value="ASSIGNED",
                    require_predicates=("assigned_to",),
                    forbid_predicates=("location",),
                ),
            ),
            metadata={"domain": "equipment_assignment"},
        )
    )
    engine.register_type(
        TypeSpec(
            name="project",
            rules=(
                ValenceRule(
                    "status",
                    minimum=1,
                    maximum=1,
                    allowed_values=("ACTIVE", "INACTIVE"),
                    value_type="str",
                ),
                ValenceRule("budget", minimum=0, maximum=1, value_type="number"),
                ValenceRule("cost", minimum=0, maximum=1, value_type="number"),
            ),
            metadata={"domain": "equipment_assignment"},
        )
    )
    engine.register_type(
        TypeSpec(
            name="person",
            rules=(
                ValenceRule("name", minimum=1, maximum=1, value_type="str"),
                ValenceRule("grant::ASSIGN_EQUIPMENT", minimum=1, maximum=1, value_type="bool"),
                ValenceRule("grant::RELEASE_EQUIPMENT", minimum=1, maximum=1, value_type="bool"),
            ),
            metadata={"domain": "equipment_assignment"},
        )
    )

    engine.register_reaction(
        ReactionDefinition(
            name="ASSIGN_EQUIPMENT",
            version=1,
            roles={"equipment": "equipment", "project": "project", "actor": "person"},
            actor_role="actor",
            required_grants=("ASSIGN_EQUIPMENT",),
            conditions=(
                Condition("equipment", "status", "equals", "AVAILABLE"),
                Condition("equipment", "assigned_to", "absent"),
                Condition("project", "status", "equals", "ACTIVE"),
            ),
            effects=(
                Effect("equipment", "status", "set_literal", value="ASSIGNED"),
                Effect("equipment", "assigned_to", "set_role_ref", value_role="project"),
                Effect("equipment", "location", "unset"),
            ),
            reversible=True,
            description="Move available equipment into an active project assignment.",
        )
    )
    engine.register_reaction(
        ReactionDefinition(
            name="RELEASE_EQUIPMENT",
            version=1,
            roles={"equipment": "equipment", "project": "project", "actor": "person"},
            actor_role="actor",
            required_grants=("RELEASE_EQUIPMENT",),
            conditions=(
                Condition("equipment", "status", "equals", "ASSIGNED"),
                Condition("equipment", "assigned_to", "target_is_role", other_role="project"),
            ),
            effects=(
                Effect("equipment", "status", "set_literal", value="AVAILABLE"),
                Effect("equipment", "assigned_to", "unset"),
                Effect("equipment", "location", "set_arg", value_arg="location"),
            ),
            reversible=True,
            description="Return assigned equipment to an available location.",
        )
    )
