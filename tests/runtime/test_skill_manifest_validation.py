from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


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
