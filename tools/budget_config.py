"""Configurable budget constants for tool result persistence.

Per-tool resolution: pinned > config overrides > registry > default.
"""

from dataclasses import dataclass, field
from typing import Any, Dict

# Tools whose thresholds must never be overridden.
# read_file=inf prevents infinite persist->read->persist loops.
PINNED_THRESHOLDS: Dict[str, float] = {
    "read_file": float("inf"),
}

# Defaults matching the current hardcoded values in tool_result_storage.py.
# Kept here as the single source of truth; tool_result_storage.py imports these.
DEFAULT_RESULT_SIZE_CHARS: int = 100_000
DEFAULT_TURN_BUDGET_CHARS: int = 200_000
DEFAULT_PREVIEW_SIZE_CHARS: int = 1_500


@dataclass(frozen=True)
class BudgetConfig:
    """Immutable budget constants for the 3-layer tool result persistence system.

    Layer 2 (per-result): resolve_threshold(tool_name) -> threshold in chars.
    Layer 3 (per-turn):   turn_budget -> aggregate char budget across all tool
                          results in a single assistant turn.
    Preview:              preview_size -> inline snippet size after persistence.
    """

    default_result_size: int = DEFAULT_RESULT_SIZE_CHARS
    turn_budget: int = DEFAULT_TURN_BUDGET_CHARS
    preview_size: int = DEFAULT_PREVIEW_SIZE_CHARS
    tool_overrides: Dict[str, int] = field(default_factory=dict)

    def resolve_threshold(self, tool_name: str) -> int | float:
        """Resolve the persistence threshold for a tool.

        Priority: pinned -> tool_overrides -> registry per-tool -> default.
        """
        if tool_name in PINNED_THRESHOLDS:
            return PINNED_THRESHOLDS[tool_name]
        if tool_name in self.tool_overrides:
            return self.tool_overrides[tool_name]
        from tools.registry import registry
        return registry.get_max_result_size(tool_name, default=self.default_result_size)


# Default config -- matches current hardcoded behavior exactly.
DEFAULT_BUDGET = BudgetConfig()


def _coerce_positive_int(value: Any, default: int) -> int:
    """Return ``value`` as a positive int, or ``default`` on any issue."""
    try:
        iv = int(value)
    except (TypeError, ValueError):
        return default
    return iv if iv > 0 else default


def _coerce_tool_overrides(value: Any) -> Dict[str, int]:
    """Return a sanitized ``{tool_name: positive_int}`` override map."""
    if not isinstance(value, dict):
        return {}
    result: Dict[str, int] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or not key:
            continue
        try:
            iv = int(raw)
        except (TypeError, ValueError):
            continue
        if iv > 0:
            result[key] = iv
    return result


def load_budget_config() -> BudgetConfig:
    """Load tool-result persistence budgets from ``config.yaml``.

    Section name: ``tool_result_budget``.  Missing or malformed values fall
    back to historical defaults so a bad config never breaks tool execution.
    """
    try:
        from hermes_cli.config import load_config
        cfg = load_config() or {}
        section = cfg.get("tool_result_budget") if isinstance(cfg, dict) else None
        if not isinstance(section, dict):
            section = {}
    except Exception:
        section = {}

    return BudgetConfig(
        default_result_size=_coerce_positive_int(
            section.get("default_result_size_chars"),
            DEFAULT_RESULT_SIZE_CHARS,
        ),
        turn_budget=_coerce_positive_int(
            section.get("turn_budget_chars"),
            DEFAULT_TURN_BUDGET_CHARS,
        ),
        preview_size=_coerce_positive_int(
            section.get("preview_size_chars"),
            DEFAULT_PREVIEW_SIZE_CHARS,
        ),
        tool_overrides=_coerce_tool_overrides(section.get("tool_overrides")),
    )
