"""PicoAPEX saturation detection and automatic target switching.

Reads active gene fitness distribution from the PGG Archon evolution GeneDB,
computes elite saturation, and when the active pool is saturated writes a new
PicoAPEX target into the self-evolution loop latest.json state file.

Boundary: local SQLite + local JSON state only; no network/LLM calls.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

DEFAULT_DB = Path("/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3")
DEFAULT_STATE_PATH = Path("/Users/appleoppa/.hermes/data/self-evolution-loop/latest.json")

DIMENSION_ORDER = ["creativity", "reasoning", "planning", "coding", "analysis"]
SATURATION_THRESHOLD = 0.30
ELITE_FITNESS_THRESHOLD = 800.0
ENGINE_VERSION = "pgg_picoapex_saturation/v1"
BOUNDARY = "pgg_picoapex_saturation; local GeneDB read + latest.json target write; no LLM/network"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class PicoAPEXEngine:
    """Detect PicoAPEX active-gene saturation and rotate the target dimension.

    Output contract for :meth:`check_and_switch` includes:
    ``{current_dim, elite_ratio, saturated, next_dim, action}``.
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB,
        state_path: str | Path = DEFAULT_STATE_PATH,
        saturation_threshold: float = SATURATION_THRESHOLD,
        elite_fitness_threshold: float = ELITE_FITNESS_THRESHOLD,
    ) -> None:
        self.db_path = Path(db_path)
        self.state_path = Path(state_path)
        self.saturation_threshold = float(saturation_threshold)
        self.elite_fitness_threshold = float(elite_fitness_threshold)

    def check_and_switch(self) -> dict[str, Any]:
        """Check active-gene saturation and write a new goal if saturated."""
        state = self._read_state()
        current_dim = self._current_dimension(state)
        next_dim = self._next_dimension(current_dim)

        try:
            distribution = self._active_fitness_distribution()
            active_count = distribution["active_count"]
            elite_count = distribution["elite_count"]
            elite_ratio = (elite_count / active_count) if active_count else 0.0
            saturated = elite_ratio > self.saturation_threshold

            action = "noop_not_saturated"
            if saturated:
                self._write_new_target(state, current_dim, next_dim, elite_ratio, active_count, elite_count)
                action = f"switched_target_to_{next_dim}"

            return {
                "schema": ENGINE_VERSION,
                "created_at": _now(),
                "current_dim": current_dim,
                "elite_ratio": round(elite_ratio, 6),
                "saturated": saturated,
                "next_dim": next_dim,
                "action": action,
                "active_count": active_count,
                "elite_count": elite_count,
                "thresholds": {
                    "saturation": self.saturation_threshold,
                    "elite_fitness": self.elite_fitness_threshold,
                },
                "db_path": str(self.db_path),
                "state_path": str(self.state_path),
                "boundary": BOUNDARY,
            }
        except Exception as exc:  # keep scheduler-friendly JSON output
            return {
                "schema": ENGINE_VERSION,
                "created_at": _now(),
                "current_dim": current_dim,
                "elite_ratio": 0.0,
                "saturated": False,
                "next_dim": next_dim,
                "action": "error_no_switch",
                "error": f"{type(exc).__name__}: {exc}",
                "db_path": str(self.db_path),
                "state_path": str(self.state_path),
                "boundary": BOUNDARY,
            }

    def _connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"GeneDB not found: {self.db_path}")
        con = sqlite3.connect(str(self.db_path))
        con.row_factory = sqlite3.Row
        return con

    def _active_fitness_distribution(self) -> dict[str, Any]:
        """Return active/elite counts from evolution_genes."""
        with self._connect() as con:
            row = con.execute(
                """
                SELECT
                  COUNT(*) AS active_count,
                  SUM(CASE WHEN COALESCE(fitness, 0) > ? THEN 1 ELSE 0 END) AS elite_count,
                  MIN(fitness) AS min_fitness,
                  AVG(fitness) AS avg_fitness,
                  MAX(fitness) AS max_fitness
                FROM evolution_genes
                WHERE status = 'active'
                """,
                (self.elite_fitness_threshold,),
            ).fetchone()

        active_count = int(row["active_count"] or 0)
        elite_count = int(row["elite_count"] or 0)
        return {
            "active_count": active_count,
            "elite_count": elite_count,
            "min_fitness": _safe_float(row["min_fitness"]),
            "avg_fitness": _safe_float(row["avg_fitness"]),
            "max_fitness": _safe_float(row["max_fitness"]),
        }

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _current_dimension(self, state: dict[str, Any]) -> str:
        """Extract current PicoAPEX dimension from known state keys, else default."""
        candidates: list[Any] = [
            state.get("current_dim"),
            state.get("target_dimension"),
            state.get("dimension"),
        ]

        for nested_key in ("picoapex", "picoapex_goal", "goal", "target"):
            nested = state.get(nested_key)
            if isinstance(nested, dict):
                candidates.extend(
                    [
                        nested.get("current_dim"),
                        nested.get("dimension"),
                        nested.get("target_dimension"),
                    ]
                )

        for value in candidates:
            if isinstance(value, str) and value in DIMENSION_ORDER:
                return value
        return DIMENSION_ORDER[0]

    def _next_dimension(self, current_dim: str) -> str:
        try:
            idx = DIMENSION_ORDER.index(current_dim)
        except ValueError:
            idx = 0
        return DIMENSION_ORDER[(idx + 1) % len(DIMENSION_ORDER)]

    def _write_new_target(
        self,
        state: dict[str, Any],
        current_dim: str,
        next_dim: str,
        elite_ratio: float,
        active_count: int,
        elite_count: int,
    ) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        target = {
            "schema": f"{ENGINE_VERSION}/target",
            "created_at": _now(),
            "from_dim": current_dim,
            "dimension": next_dim,
            "reason": "active_gene_elite_ratio_saturated",
            "elite_ratio": round(elite_ratio, 6),
            "active_count": active_count,
            "elite_count": elite_count,
            "objective": f"PicoAPEX saturated on {current_dim}; rotate optimization target to {next_dim}.",
            "rotation_order": DIMENSION_ORDER,
        }

        updated = dict(state)
        updated["picoapex_goal"] = target
        updated["picoapex"] = {
            "schema": ENGINE_VERSION,
            "updated_at": _now(),
            "current_dim": next_dim,
            "previous_dim": current_dim,
            "elite_ratio": round(elite_ratio, 6),
            "saturated": True,
            "action": f"switched_target_to_{next_dim}",
        }

        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(updated, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.state_path)


def main() -> None:
    print(json.dumps(PicoAPEXEngine().check_and_switch(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
