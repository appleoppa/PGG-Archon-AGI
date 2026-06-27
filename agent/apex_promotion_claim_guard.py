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


def _config_human_ack_token() -> str:
    """Read the route_chain_gate.autonomous_promotion_human_ack_token from config.yaml.

    The presence of a non-empty token at evaluation time is treated as the
    user's explicit, persistent pre-acknowledgement of autonomous promotion.
    Clearing the token (or removing the key) revokes that ack on the next
    evaluation, so the guard remains user-controlled and auditable.
    """
    try:
        import yaml  # type: ignore
    except Exception:  # pragma: no cover — defensive
        return ""
    from pathlib import Path

    cfg_path = Path("/Users/appleoppa/.hermes/config.yaml")
    if not cfg_path.exists():
        return ""
    try:
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:  # pragma: no cover — defensive
        return ""
    if not isinstance(data, Mapping):
        return ""
    raw = data.get("route_chain_gate")
    if not isinstance(raw, Mapping):
        return ""
    token = raw.get("autonomous_promotion_human_ack_token")
    return str(token).strip() if token else ""


def evaluate_promotion_claim_guard(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    policy_raw = snapshot.get("autonomous_promotion_policy")
    policy = policy_raw if isinstance(policy_raw, Mapping) else {}
    explicit_ack_raw = snapshot.get("human_ack")
    if explicit_ack_raw is not None:
        human_ack = bool(explicit_ack_raw)
        ack_source = "snapshot_explicit"
    else:
        token = _config_human_ack_token()
        human_ack = bool(token)
        ack_source = "config_human_ack_token" if token else "absent"
    decision = PromotionClaimGuard().evaluate(
        snapshot,
        gep_actual_execution_allowed=bool(policy.get("gep_actual_execution_allowed")),
        human_ack=human_ack,
    )
    return {
        "schema": decision.schema,
        "allowed": decision.allowed,
        "hold_reasons": list(decision.hold_reasons),
        "evaluated_at": decision.evaluated_at,
        "side_effects": decision.side_effects,
        "human_ack_source": ack_source,
        "human_ack_present": bool(human_ack),
    }


__all__ = ["PromotionClaimGuard", "PromotionDecision", "evaluate_promotion_claim_guard"]
