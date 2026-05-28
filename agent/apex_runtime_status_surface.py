"""Compatibility wrapper for the renamed PGG Archon status surface.

New code should import `agent.pgg_archon_status_surface`. This module remains so
historical RuntimeOS callers do not break during migration.
"""
from __future__ import annotations

from agent.pgg_archon_status_surface import build_pgg_archon_status_surface

build_apex_runtime_status_surface = build_pgg_archon_status_surface

__all__ = ["build_apex_runtime_status_surface", "build_pgg_archon_status_surface"]
