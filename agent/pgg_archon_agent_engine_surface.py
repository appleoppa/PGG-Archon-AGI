"""PGG Archon — AgentEngineSurface/v1.

Read-only engine capability declaration surface, adapted from:
- APEX-AGI omega-agi/agent/src/engines.rs (selected capabilities)

This module declares available agent engines as data structures. It does not
execute, load, or run any engine — it is purely a read-only capability declaration
surface with no model calls, no gene writes, no daemon starts, no AGI completion claims.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

SURFACE_VERSION = "PGGArchonAgentEngineSurface/v1"
SURFACE_SOURCE = "APEX-AGI omega-agi/agent/src/engines.rs"


@dataclass(frozen=True)
class AgentEngine:
    """Declaration of an agent engine capability."""
    name: str
    version: str = "1.0"
    capability_tags: list[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "capability_tags": list(self.capability_tags),
            "description": self.description,
        }


def _default_engines() -> list[AgentEngine]:
    """Return the built-in engine declarations from engines.rs patterns."""
    return [
        AgentEngine(
            name="react_engine",
            version="1.0",
            capability_tags=["agent", "react", "loop", "execution"],
            description="ReAct loop agent execution — iterative reasoning and action cycle.",
        ),
        AgentEngine(
            name="inference_engine",
            version="1.0",
            capability_tags=["agent", "inference", "llm", "dispatch"],
            description="LLM inference dispatch — routes prompts to configured language models.",
        ),
        AgentEngine(
            name="tool_execution_engine",
            version="1.0",
            capability_tags=["agent", "tool", "execution", "dispatch"],
            description="Tool call execution — dispatches tool invocations to registered handlers.",
        ),
        AgentEngine(
            name="feedback_engine",
            version="1.0",
            capability_tags=["agent", "feedback", "loop", "integration"],
            description="Feedback integration loop — processes execution feedback and adjusts behavior.",
        ),
        AgentEngine(
            name="knowledge_engine",
            version="1.0",
            capability_tags=["agent", "knowledge", "retrieval", "management"],
            description="Knowledge retrieval and management — queries and updates the knowledge base.",
        ),
    ]


def _engines_to_report(engines: list[AgentEngine]) -> dict[str, Any]:
    """Convert a list of AgentEngine declarations into a structured report."""
    engine_dicts = [e.to_dict() for e in engines]
    status = "PASS" if engines else "WATCH"
    warnings = [] if engines else ["NoAgentEnginesDeclared"]
    return {
        "schema": SURFACE_VERSION,
        "source": SURFACE_SOURCE,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": status,
        "engine_count": len(engines),
        "engines": engine_dicts,
        "engine_names": [e.name for e in engines],
        "warnings": warnings,
        "failures": [],
        "agi_completion_claim": False,
        "boundary": "Read-only engine capability declaration surface. No engines are executed, loaded, or run.",
    }


def build_pgg_archon_agent_engine_surface(
    custom_engines: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a structured agent engine surface.

    This is a pure function with no side effects. Returns built-in engine declarations
    by default, or custom engines if provided.

    Args:
        custom_engines: Optional list of engine declaration dicts to override built-ins.
            Each dict may have: name, version, capability_tags, description.

    Returns:
        A structured report dict with schema, status, engine count, and engine details.
    """
    if custom_engines is not None:
        engines = [
            AgentEngine(
                name=str(e.get("name", "unnamed")),
                version=str(e.get("version", "1.0")),
                capability_tags=list(e.get("capability_tags", []) or []),
                description=str(e.get("description", "")),
            )
            for e in custom_engines
        ]
    else:
        engines = _default_engines()

    return _engines_to_report(engines)


__all__ = [
    "SURFACE_VERSION",
    "SURFACE_SOURCE",
    "AgentEngine",
    "build_pgg_archon_agent_engine_surface",
]
