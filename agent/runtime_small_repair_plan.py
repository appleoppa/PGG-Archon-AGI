"""Compatibility wrapper for the renamed PGG Archon small repair planner.

New code should import `agent.pgg_archon_small_repair_plan`. This module remains
so historical RuntimeOS callers do not break during migration.
"""
from __future__ import annotations

from agent.pgg_archon_small_repair_plan import build_pgg_archon_small_repair_plan

build_runtime_small_repair_plan = build_pgg_archon_small_repair_plan

__all__ = ["build_runtime_small_repair_plan", "build_pgg_archon_small_repair_plan"]
