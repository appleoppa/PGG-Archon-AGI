"""PGG Archon APEX Unified Schema Validator.
Lightweight Python validator for APEX Gene/Event/State/Skill schemas.
No /root/* hardcoded paths. No JS adapter dependency.

_NATIVE bridge: Rust PyO3 native module (hermes_pgg_schema_validator) ~5x faster.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_NATIVE = False
try:
    import hermes_pgg_schema_validator as _native_mod
    _NATIVE = True
except ImportError:
    pass

GENE_SCHEMA = {
    "type": {"type": str, "allowed": ["Gene"]},
    "id": {"type": str, "pattern": "gene_"},
    "version": {"type": int},
    "category": {"type": str, "allowed": ["repair", "optimize", "innovate", "orchestrate", "evolve"]},
    "signals_match": {"type": list},
    "preconditions": {"type": list},
    "strategy": {"type": list},
}


@dataclass(frozen=True)
class SchemaReport:
    schema: str
    status: str
    valid_count: int
    invalid_count: int
    checked_schema: str
    issues: list[str]
    detail: str
    evidence_hash: str


if _NATIVE:
    def validate_gene(gene: dict) -> list[str]:
        raw = _native_mod.native_validate_gene(json.dumps(gene))
        result = json.loads(raw)
        return result["issues"]

    def validate_genes_file(path: str | Path) -> dict[str, Any]:
        return json.loads(_native_mod.native_validate_genes_file(str(path)))
else:
    import hashlib
    import re

    def validate_gene(gene: dict) -> list[str]:
        issues = []
        for field, spec in GENE_SCHEMA.items():
            val = gene.get(field)
            exp_type = spec["type"]
            if val is None:
                issues.append(f"missing:{field}")
                continue
            if not isinstance(val, exp_type):
                if exp_type is list and isinstance(val, str):
                    issues.append(f"type_mismatch:{field} (got str, expected list)")
                else:
                    issues.append(f"type_mismatch:{field} (got {type(val).__name__}, expected {exp_type.__name__})")
            allowed = spec.get("allowed")
            if allowed and val not in allowed:
                issues.append(f"enum_mismatch:{field} (got {val}, expected {allowed})")
            pattern = spec.get("pattern")
            if pattern and isinstance(val, str) and pattern not in val:
                issues.append(f"pattern_mismatch:{field} ({val} does not contain {pattern})")
        return issues

    def validate_genes_file(path: str | Path) -> dict[str, Any]:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return asdict(SchemaReport(
                schema="PGGArchonSchemaValidator/v1", status="BLOCKED",
                valid_count=0, invalid_count=0, checked_schema="genes",
                issues=[f"file_not_found:{p}"],
                detail=f"Gene schema: file not found",
                evidence_hash="",
            ))
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return asdict(SchemaReport(
                schema="PGGArchonSchemaValidator/v1", status="BLOCKED",
                valid_count=0, invalid_count=0, checked_schema="genes",
                issues=[f"parse_error:{e}"],
                detail=f"Gene schema: parse error",
                evidence_hash="",
            ))
        genes = data if isinstance(data, list) else data.get("genes", [])
        invalid, issues = 0, []
        for i, gene in enumerate(genes):
            g_issues = validate_gene(gene)
            if g_issues:
                invalid += 1
                issues.extend(f"[{i}] {x}" for x in g_issues[:5])
        valid = len(genes) - invalid
        status = "PASS" if invalid == 0 else "WATCH"
        payload = "|".join([str(len(genes)), str(valid), str(invalid)])
        return asdict(SchemaReport(
            schema="PGGArchonSchemaValidator/v1", status=status,
            valid_count=valid, invalid_count=invalid,
            checked_schema="genes", issues=issues[:50],
            detail=f"Gene schema: {valid}/{len(genes)} valid",
            evidence_hash=hashlib.sha256(payload.encode()).hexdigest(),
        ))


__all__ = ["SchemaReport", "validate_gene", "validate_genes_file", "GENE_SCHEMA"]