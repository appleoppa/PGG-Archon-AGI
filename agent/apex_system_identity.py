"""Current APEX/PGG system identity metadata.

This module keeps the public/current system name separate from historical
RuntimeOS implementation names.  Code modules may keep stable import paths for
compatibility, while user-facing surfaces should prefer CURRENT_SYSTEM_NAME.
"""

from __future__ import annotations

CURRENT_SYSTEM_NAME = "PGG Archon AGI"
CURRENT_SYSTEM_SLUG = "pgg-archon-agi"
LEGACY_RUNTIME_NAME = "APEX RuntimeOS"

# Prefer the current public command while keeping old commands stable for scripts.
PRIMARY_DIAGNOSTIC_COMMAND = "pgg-archon"
DIAGNOSTIC_COMMAND_ALIASES = ("apex-runtimeos", "apex", "archon")

USER_FACING_SYSTEM_LABEL = CURRENT_SYSTEM_NAME

__all__ = [
    "CURRENT_SYSTEM_NAME",
    "CURRENT_SYSTEM_SLUG",
    "LEGACY_RUNTIME_NAME",
    "PRIMARY_DIAGNOSTIC_COMMAND",
    "DIAGNOSTIC_COMMAND_ALIASES",
    "USER_FACING_SYSTEM_LABEL",
]
