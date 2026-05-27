"""Promotion and AGI-claim guard for PGG Archon AGI.

A perfect score is not enough to claim AGI or allow autonomous promotion. This
pure guard makes the extra conditions explicit and testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Tuple

from agent.apex_inward_validator import DualInwardValidator


@dataclass(frozen=True)
class PromotionDecision:
    schema: str
    allowed: bool
    hold_reasons: Tuple[str, ...]
    evaluated_at: str
    side_effects: str = "pure_decision"


class PromotionClaimGuard:
    def __init__(self, dual_validator: DualInwardValidator | None = None, clock: Callable[[], datetime] | None = None):
        self.dual_validator = dual_validator or DualInwardValidator()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def evaluate(self, snapshot: Mapping[str, Any], *, gep_actual_execution_allowed: bool, human_ack: bool) -> PromotionDecision:
        hold = []
        if float(snapshot.get("score") or 0) < 100.0:
            hold.append("unified_score_below_100")
        if snapshot.get("hold_reasons"):
            hold.append("unified_hold_reasons_present")
        if not gep_actual_execution_allowed:
            hold.append("gep_actual_execution_not_allowed")
        validation = self.dual_validator.cross_validate(snapshot)
        if not validation.cross_validated:
            hold.append("dual_inward_validation_not_pass")
            hold.extend(validation.hold_reasons[:8])
        if not human_ack:
            hold.append("human_ack_required")
        return PromotionDecision(
            schema="ApexPromotionClaimGuard/v1",
            allowed=not hold,
            hold_reasons=tuple(dict.fromkeys(hold)),
            evaluated_at=self.clock().isoformat(),
        )


def evaluate_promotion_claim_guard(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    policy_raw = snapshot.get("autonomous_promotion_policy")
    policy = policy_raw if isinstance(policy_raw, Mapping) else {}
    decision = PromotionClaimGuard().evaluate(
        snapshot,
        gep_actual_execution_allowed=bool(policy.get("gep_actual_execution_allowed")),
        human_ack=False,
    )
    return {
        "schema": decision.schema,
        "allowed": decision.allowed,
        "hold_reasons": list(decision.hold_reasons),
        "evaluated_at": decision.evaluated_at,
        "side_effects": decision.side_effects,
    }


__all__ = ["PromotionClaimGuard", "PromotionDecision", "evaluate_promotion_claim_guard"]
