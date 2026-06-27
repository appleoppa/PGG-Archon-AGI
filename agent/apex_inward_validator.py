"""Dual inward validation for PGG Archon AGI scoring.

This module turns GPT/Claude inward validation into a deterministic, testable
advisory layer. It performs no network access, reads no credentials, and has no
side effects unless an explicit transport is injected by a caller.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, Protocol, Tuple


class NetworkExecutionDenied(RuntimeError):
    """Raised when a validator transport is used without explicit network allow."""


@dataclass(frozen=True)
class ValidationVerdict:
    provider: str
    status: str
    score: float
    reasons: Tuple[str, ...] = ()
    invariant_violations: Tuple[str, ...] = ()
    raw_response_hash: str = ""


@dataclass(frozen=True)
class CrossValidationResult:
    schema: str = "ApexInwardValidation/v1"
    cross_validated: bool = False
    per_provider: Dict[str, ValidationVerdict] = field(default_factory=dict)
    disagreements: Tuple[str, ...] = ()
    hold_reasons: Tuple[str, ...] = ()
    side_effects: str = "read_only_advisory"


class InwardValidator(Protocol):
    name: str

    def evaluate(self, snapshot: Mapping[str, Any]) -> ValidationVerdict:
        ...


def _layer_scores(snapshot: Mapping[str, Any]) -> Dict[str, float]:
    layer_map = snapshot.get("layers")
    layers = layer_map if isinstance(layer_map, Mapping) else {}
    out: Dict[str, float] = {}
    for name, data in layers.items():
        if isinstance(data, Mapping):
            try:
                out[str(name)] = float(data.get("score") or 0)
            except (TypeError, ValueError):
                out[str(name)] = 0.0
    return out


class OfflineDeterministicValidator:
    """Deterministic offline validator used for CI and default runtime."""

    def __init__(self, name: str):
        self.name = name

    def evaluate(self, snapshot: Mapping[str, Any]) -> ValidationVerdict:
        violations = []
        score = float(snapshot.get("score") or 0)
        hold_reasons = snapshot.get("hold_reasons") if isinstance(snapshot.get("hold_reasons"), list) else []
        policy_raw = snapshot.get("autonomous_promotion_policy")
        policy = policy_raw if isinstance(policy_raw, Mapping) else {}
        agi_claim = bool(snapshot.get("agi_completion_claim"))
        gep_exec = bool(policy.get("gep_actual_execution_allowed"))
        if agi_claim:
            violations.append("agi_completion_claim_must_remain_false")
        if not gep_exec and bool(snapshot.get("allows_autonomous_promotion")):
            violations.append("no_autopromotion_without_gep_execution")
        for layer, layer_score in _layer_scores(snapshot).items():
            if layer_score < 75:
                violations.append(f"layer_below_threshold:{layer}")
        if score >= 100 and hold_reasons:
            violations.append("perfect_score_with_hold_reasons")
        status = "PASS" if not violations else "FAIL"
        return ValidationVerdict(
            provider=self.name,
            status=status,
            score=100.0 if status == "PASS" else max(0.0, 100.0 - 20.0 * len(violations)),
            reasons=("deterministic_invariant_check",),
            invariant_violations=tuple(violations),
            raw_response_hash="offline-deterministic",
        )


class TransportInwardValidator:
    """Optional adapter for caller-injected GPT/Claude transports.

    The transport must be injected explicitly. This class never reads API keys
    and never enables network by itself.
    """

    def __init__(self, name: str, transport: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None, *, allow_network: bool = False):
        self.name = name
        self._transport = transport
        self._allow_network = allow_network

    def evaluate(self, snapshot: Mapping[str, Any]) -> ValidationVerdict:
        if self._transport is None:
            return OfflineDeterministicValidator(self.name).evaluate(snapshot)
        if not self._allow_network:
            raise NetworkExecutionDenied("inward validator network transport denied")
        raw = self._transport({
            "schema": snapshot.get("schema"),
            "score": snapshot.get("score"),
            "hold_reasons": snapshot.get("hold_reasons", []),
            "layers": snapshot.get("layers", {}),
            "agi_completion_claim": snapshot.get("agi_completion_claim"),
            "autonomous_promotion_policy": snapshot.get("autonomous_promotion_policy", {}),
        })
        status = str(raw.get("status") or "ABSTAIN").upper()
        if status not in {"PASS", "FAIL", "ABSTAIN"}:
            status = "ABSTAIN"
        return ValidationVerdict(
            provider=self.name,
            status=status,
            score=float(raw.get("score") or 0),
            reasons=tuple(str(x) for x in raw.get("reasons", [])[:8]) if isinstance(raw.get("reasons"), list) else (),
            invariant_violations=tuple(str(x) for x in raw.get("invariant_violations", [])[:8]) if isinstance(raw.get("invariant_violations"), list) else (),
            raw_response_hash=str(raw.get("raw_response_hash") or "transport-redacted")[:80],
        )


class DualInwardValidator:
    def __init__(self, gpt: InwardValidator | None = None, claude: InwardValidator | None = None):
        self.gpt = gpt or OfflineDeterministicValidator("gpt")
        self.claude = claude or OfflineDeterministicValidator("claude")

    def cross_validate(self, snapshot: Mapping[str, Any]) -> CrossValidationResult:
        verdicts = {"gpt": self.gpt.evaluate(snapshot), "claude": self.claude.evaluate(snapshot)}
        hold = []
        disagreements = []
        statuses = {name: verdict.status for name, verdict in verdicts.items()}
        if len(set(statuses.values())) > 1:
            disagreements.append("validator_status_disagreement")
        for name, verdict in verdicts.items():
            if verdict.status != "PASS":
                hold.append(f"{name}_validator_not_pass")
            for violation in verdict.invariant_violations:
                hold.append(f"{name}:{violation}")
        return CrossValidationResult(
            cross_validated=not hold and not disagreements,
            per_provider=verdicts,
            disagreements=tuple(disagreements),
            hold_reasons=tuple(hold),
        )


def cross_validate_unified_score(snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    result = DualInwardValidator().cross_validate(snapshot)
    return {
        "schema": result.schema,
        "cross_validated": result.cross_validated,
        "providers": {name: {"status": v.status, "score": v.score, "violations": list(v.invariant_violations)} for name, v in result.per_provider.items()},
        "disagreements": list(result.disagreements),
        "hold_reasons": list(result.hold_reasons),
        "side_effects": result.side_effects,
    }


__all__ = [
    "CrossValidationResult",
    "DualInwardValidator",
    "InwardValidator",
    "NetworkExecutionDenied",
    "OfflineDeterministicValidator",
    "TransportInwardValidator",
    "ValidationVerdict",
    "cross_validate_unified_score",
]
