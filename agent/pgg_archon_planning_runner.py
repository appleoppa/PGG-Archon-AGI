"""PGG Archon planning runner.
Boundary: builds a read-only plan from supplied task metadata; does not execute, schedule, or mutate tasks.
"""
from __future__ import annotations

from typing import Any

try:
    import hermes_pgg_archon_utils as _native_mod  # type: ignore[import-untyped]

    _NATIVE = True
except ImportError:
    _NATIVE = False

import json


if _NATIVE:

    def build_plan(tasks: list[dict[str, Any]]) -> dict[str, Any]:
        raw = _native_mod.build_plan(json.dumps(tasks))
        return json.loads(raw)

else:

    def build_plan(tasks: list[dict[str, Any]]) -> dict[str, Any]:
        warnings = []
        if not isinstance(tasks, list):
            return {"total_tasks": 0, "slice_count": 0, "slices": [], "warnings": ["tasks is not a list"]}
        normalized = []
        seen = set()
        for i, t in enumerate(tasks):
            if not isinstance(t, dict):
                warnings.append(f"task {i} not dict")
                continue
            tid = t.get("id") or t.get("name") or f"task_{i}"
            if tid in seen:
                warnings.append(f"duplicate task id {tid}")
                continue
            seen.add(tid)
            deps = t.get("dependencies", t.get("deps", [])) or []
            if not isinstance(deps, list):
                warnings.append(f"{tid} dependencies not list")
                deps = []
            normalized.append({"id": tid, "name": t.get("name", tid), "dependencies": deps})
        if not normalized:
            return {"total_tasks": 0, "slice_count": 0, "slices": [], "warnings": warnings + ["no valid tasks"]}
        remaining = {t["id"]: t for t in normalized}
        done = set()
        slices = []
        while remaining:
            ready = [
                tid
                for tid, t in remaining.items()
                if all(dep in done or dep not in remaining for dep in t["dependencies"])
            ]
            if not ready:
                warnings.append("cycle_or_unresolved_dependencies")
                ready = list(remaining.keys())
            slices.append(
                {"slice_index": len(slices), "task_ids": ready, "tasks": [remaining[tid] for tid in ready]}
            )
            for tid in ready:
                done.add(tid)
                remaining.pop(tid, None)
        return {"total_tasks": len(normalized), "slice_count": len(slices), "slices": slices, "warnings": warnings}


__all__ = ["build_plan"]