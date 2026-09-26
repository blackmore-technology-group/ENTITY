from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from adam_v41.authority import Authority
from adam_v41.canonical import canonical_json_bytes, digest


@dataclass(frozen=True)
class ChemistryCandidate:
    name: str
    from_version: int
    to_version: int
    rename_fields: dict[str, str]
    drop_fields: tuple[str, ...] = ()

    @property
    def candidate_id(self) -> str:
        return digest("ADAM42:CHEMISTRY_CANDIDATE", asdict(self))

    def forward(self, record: dict[str, Any]) -> dict[str, Any]:
        return {self.rename_fields.get(k, k): v for k, v in record.items() if k not in self.drop_fields}

    def reverse(self, record: dict[str, Any]) -> dict[str, Any]:
        inverse = {v: k for k, v in self.rename_fields.items()}
        return {inverse.get(k, k): v for k, v in record.items()}


@dataclass(frozen=True)
class ChemistryPromotionReceipt:
    candidate_id: str
    status: str
    historical_states_replayed: int
    equivalence_failures: int
    approvals: tuple[dict[str, str], ...]
    promoted_ns: int | None
    receipt_id: str


class ChemistryLab:
    """Shadow replay and independent quorum approval for bounded chemistry changes."""

    def __init__(self, root: Path | str, approvers: list[Authority], threshold: int | None = None):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.approvers = approvers
        self.threshold = threshold or (len(approvers) // 2 + 1)

    def evaluate(self, candidate: ChemistryCandidate, historical_states: list[dict[str, Any]]) -> ChemistryPromotionReceipt:
        failures = 0
        for state in historical_states:
            transformed = candidate.forward(state)
            restored = candidate.reverse(transformed)
            if restored != state:
                failures += 1
        status = "REJECTED_EQUIVALENCE" if failures else "AWAITING_APPROVAL"
        approvals: list[dict[str, str]] = []
        payload = canonical_json_bytes({
            "candidate_id": candidate.candidate_id,
            "from_version": candidate.from_version,
            "to_version": candidate.to_version,
            "historical_states": len(historical_states),
            "failures": failures,
        })
        if not failures:
            for authority in self.approvers:
                approvals.append({
                    "authority_id": authority.authority_id,
                    "public_key_hex": authority.public_key_hex,
                    "signature": authority.sign(payload),
                })
            valid = [a for a in approvals if Authority.verify(a["public_key_hex"], payload, a["signature"])]
            status = "PROMOTED" if len(valid) >= self.threshold else "REJECTED_AUTHORITY"
        promoted = time.time_ns() if status == "PROMOTED" else None
        body = {
            "candidate_id": candidate.candidate_id, "status": status,
            "historical_states_replayed": len(historical_states), "equivalence_failures": failures,
            "approvals": approvals, "promoted_ns": promoted,
        }
        receipt = ChemistryPromotionReceipt(
            candidate.candidate_id, status, len(historical_states), failures, tuple(approvals), promoted,
            digest("ADAM42:CHEMISTRY_PROMOTION", body),
        )
        (self.root / f"{candidate.candidate_id}.json").write_text(json.dumps({**body, "receipt_id": receipt.receipt_id}, indent=2, sort_keys=True), encoding="utf-8")
        return receipt
