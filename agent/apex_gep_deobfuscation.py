"""PGG Archon GEP static deobfuscation review gate.

The review is text/metadata-only. It never executes, imports, decodes, or trusts
archived GEP components. PASS means static metadata review is staged and no
known dangerous pattern is present in the inspected text; it does not unlock
runtime execution.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, Mapping, Sequence

_DANGEROUS_PATTERNS = {
    "eval_usage": re.compile(r"\beval\s*\(", re.I),
    "exec_usage": re.compile(r"\bexec\s*\(", re.I),
    "dynamic_function_constructor": re.compile(r"\bFunction\s*\(", re.I),
    "node_child_process": re.compile(r"child_process", re.I),
    "spawn_call": re.compile(r"\bspawn\s*\(", re.I),
    "network_fetch": re.compile(r"\bfetch\s*\(|XMLHttpRequest|WebSocket", re.I),
    "env_access": re.compile(r"process\.env|os\.environ", re.I),
}
_OBFUSCATION_PATTERNS = {
    "base64_decode": re.compile(r"\batob\s*\(|base64", re.I),
    "hex_escape": re.compile(r"\\x[0-9a-fA-F]{2}"),
    "unicode_escape": re.compile(r"\\u[0-9a-fA-F]{4}"),
    "long_base64_like_blob": re.compile(r"[A-Za-z0-9+/]{80,}={0,2}"),
    "charcode_decode": re.compile(r"fromCharCode", re.I),
    "infinite_loop_pattern": re.compile(r"while\s*\(\s*true\s*\)|for\s*\(\s*;\s*;\s*\)", re.I),
}


def shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = {ch: text.count(ch) for ch in set(text)}
    total = len(text)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def review_source_text(source: str, *, component_id: str = "") -> Dict[str, Any]:
    text = str(source or "")
    dangerous = [name for name, pattern in _DANGEROUS_PATTERNS.items() if pattern.search(text)]
    obfuscation = [name for name, pattern in _OBFUSCATION_PATTERNS.items() if pattern.search(text)]
    entropy = round(shannon_entropy(text), 4)
    high_entropy = entropy >= 5.5 and len(text) >= 120
    if high_entropy:
        obfuscation.append("high_entropy")
    suspicious_count = len(set(dangerous + obfuscation))
    verdict = "PASS" if not dangerous and suspicious_count < 2 else "HOLD"
    reasons = []
    for item in dangerous:
        reasons.append({"code": item, "level": "blocker", "component_id": component_id})
    for item in obfuscation:
        reasons.append({"code": item, "level": "warning", "component_id": component_id})
    return {
        "schema": "PggArchonGEPDeobfuscationComponentReview/v1",
        "component_id": component_id,
        "verdict": verdict,
        "entropy": entropy,
        "dangerous_patterns": dangerous,
        "obfuscation_signals": sorted(set(obfuscation)),
        "suspicious_count": suspicious_count,
        "reasons": reasons,
        "static_only": True,
        "executed": False,
        "imported": False,
        "decoded": False,
        "trusted": False,
        "side_effects": "read_only_report",
    }


def build_default_deobfuscation_inputs(components: Mapping[str, Mapping[str, Any]] | None = None) -> list[Dict[str, Any]]:
    from agent.apex_gep import GEP_COMPONENTS

    source = components if isinstance(components, Mapping) else GEP_COMPONENTS
    items: list[Dict[str, Any]] = []
    for name, raw in source.items():
        if not isinstance(raw, Mapping):
            continue
        # Deliberately review metadata text, not archived source bytes. Archived
        # files are not imported, decoded, or executed here.
        text = " ".join(
            str(raw.get(key) or "")
            for key in ("role", "status", "risk", "feature_gate")
        )
        if raw.get("strategies"):
            text += " " + " ".join(str(item) for item in raw.get("strategies") or [])
        items.append({"component_id": name, "source_text": text, "metadata_only": True})
    return items


def build_deobfuscation_review_report(inputs: Sequence[Mapping[str, Any]] | None = None) -> Dict[str, Any]:
    items = list(inputs) if inputs is not None else build_default_deobfuscation_inputs()
    reviews = []
    for raw in items:
        component_id = str(raw.get("component_id") or "component") if isinstance(raw, Mapping) else "component"
        source_text = str(raw.get("source_text") or "") if isinstance(raw, Mapping) else ""
        reviews.append(review_source_text(source_text, component_id=component_id))
    hold_components = [item["component_id"] for item in reviews if item.get("verdict") != "PASS"]
    status = "PASS" if reviews and not hold_components else "HOLD"
    return {
        "schema": "PggArchonGEPDeobfuscationReview/v1",
        "status": status,
        "decision": status,
        "component_count": len(reviews),
        "hold_components": hold_components,
        "reviews": reviews,
        "static_only": True,
        "executed": False,
        "imported": False,
        "decoded": False,
        "trusted": False,
        "runtime_unlocked": False,
        "gene_write_allowed": False,
        "agi_completion_claim": False,
        "side_effects": "read_only_report",
    }


__all__ = [
    "build_default_deobfuscation_inputs",
    "build_deobfuscation_review_report",
    "review_source_text",
    "shannon_entropy",
]
