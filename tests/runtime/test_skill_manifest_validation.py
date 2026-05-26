from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import yaml

from runtime.skills.registry_validator import validate_skill_registry_policy


SCHEMA_PATH = Path("runtime/skills/manifest.schema.json")


def _schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_skill_manifest_accepts_candidate_with_provenance():
    manifest = {
        "id": "desktop-search-skill",
        "version": "0.1.0",
        "description": "candidate skill extracted from desktop super evolution materials",
        "entry": "SKILL.md",
        "status": "candidate",
        "capability_tags": ["search", "apex"],
        "required_scopes": ["file_read", "llm_call"],
        "sandbox_profile": "read_only",
        "provenance": {"source": "desktop-super-evolution", "source_hash": "abc123", "license": "unknown", "reviewer": "runtimeos"},
        "checksum": "sha256:abc123",
        "tests": ["tests/runtime/test_skill_manifest_validation.py"],
        "rollback": "remove registry entry",
    }
    Draft202012Validator(_schema()).validate(manifest)


def test_skill_manifest_rejects_missing_provenance():
    manifest = {
        "id": "bad-skill",
        "version": "0.1.0",
        "description": "missing provenance",
        "entry": "SKILL.md",
        "status": "trusted",
        "required_scopes": ["shell"],
        "checksum": "sha256:abc123",
        "tests": [],
    }
    errors = sorted(Draft202012Validator(_schema()).iter_errors(manifest), key=lambda err: err.path)
    assert errors
    assert any("provenance" in str(error.message) for error in errors)


def test_skill_manifest_rejects_unknown_scope():
    manifest = {
        "id": "bad-scope",
        "version": "0.1.0",
        "description": "bad scope",
        "entry": "SKILL.md",
        "status": "candidate",
        "required_scopes": ["root_access"],
        "provenance": {"source": "x", "source_hash": "y"},
        "checksum": "sha256:abc123",
        "tests": [],
    }
    errors = list(Draft202012Validator(_schema()).iter_errors(manifest))
    assert errors


def test_skill_registry_keeps_desktop_and_external_materials_reference_only():
    registry = yaml.safe_load(Path("runtime/skills/registry.yaml").read_text(encoding="utf-8"))
    report = validate_skill_registry_policy(registry)
    assert report["schema"] == "ApexRuntimeOSSkillRegistryPolicyReport/v1"
    assert report["status"] == "PASS"
    assert report["policy"] == "deny_by_default"
    assert report["reference_only_high_risk_count"] >= 4
    assert "desktop-super-evolution-source" in report["reference_only_high_risk_ids"]
    assert "external-github-evolution-source" in report["reference_only_high_risk_ids"]
    assert report["side_effects"] == "read_only_report"
    assert "does not execute" in report["boundary"]


def test_skill_registry_blocks_high_risk_material_outside_reference_only():
    registry = {
        "schema": "ApexRuntimeOSSkillRegistry/v1",
        "policy": "deny_by_default",
        "trusted": [{"id": "bad-github-ingest", "source": "external/github-evolution", "status": "trusted"}],
        "sandboxed": [],
        "candidate": [],
        "reference_only": [],
    }
    report = validate_skill_registry_policy(registry)
    assert report["status"] == "BLOCK"
    assert any(item["code"] == "high_risk_source_not_reference_only" for item in report["violations"])
