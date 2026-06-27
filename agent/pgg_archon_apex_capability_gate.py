#!/usr/bin/env python3
"""PGG Archon APEX Capability evidence gate compatibility surface.

This module provides capability_gate naming while delegating to the existing
bounded Rust-backed APEX evidence implementation. It intentionally preserves the
underlying implementation module for backward compatibility.
"""

from __future__ import annotations

from agent.pgg_archon_apex_asi_gate import (  # noqa: F401
    PggApexAsiGate as PggApexCapabilityGate,
    boundary,
    evaluate,
    sample_config,
    version,
)


PggApexAsiGate = PggApexCapabilityGate


__all__ = [
    "PggApexCapabilityGate",
    "PggApexAsiGate",
    "evaluate",
    "sample_config",
    "version",
    "boundary",
]
