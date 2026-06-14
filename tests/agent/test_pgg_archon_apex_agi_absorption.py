"""Tests for the PGG Archon APEX-AGI absorption surface."""
from __future__ import annotations

import json
from pathlib import Path

from agent.pgg_archon_apex_agi_absorption import (
    build_apex_agi_absorption_candidates,
    build_pgg_archon_apex_agi_absorption_surface,
    run_apex_absorption_quality_gates,
)


def _make_layout(root: Path) -> Path:
    files = {
        "omega_pipeline/quality_gates.py": "class GateResult: pass\n",
        "omega_pipeline/self_healing.py": "class SelfHealer: pass\n",
        "omega-agi/runtime/src/swarm/mod.rs": "pub fn generate_id() {}\n",
        "omega-agi/runtime/src/swarm/consensus.rs": "pub struct ConsensusEngine;\n",
        "omega-agi/runtime/src/swarm/crdt.rs": "pub struct CollaborativeText;\n",
        "web_ui/app.py": "from flask import Flask\napp = Flask(__name__)\n",
        "launcher.sh": "#!/bin/sh\necho ok\n",
        "requirements.txt": "flask>=3.0.0\npsutil>=5.9.0\n",
        "omega-agi/avatar/src/chat.rs": "pub struct ChatEngine;\n",
        "omega-agi/superpowers/src/boost.rs": "pub struct BoostManager;\n",
    }
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def test_candidates_have_blocked_side_effects(tmp_path: Path) -> None:
    root = _make_layout(tmp_path)
    candidates = build_apex_agi_absorption_candidates(source_root=root)
    assert candidates, "expected absorption candidates"
    for item in candidates:
        assert item["blocked_side_effects"], item
        assert item["status"] == "SOURCE_PRESENT"
        assert item["secret_review_hits"] == []


def test_quality_gates_block_when_no_model_review(tmp_path: Path) -> None:
    root = _make_layout(tmp_path)
    candidates = build_apex_agi_absorption_candidates(source_root=root)
    gates = run_apex_absorption_quality_gates(candidates, model_reviews=[])
    blocking = [g for g in gates if g["severity"] == "blocking" and not g["passed"]]
    assert any(g["gate_name"] == "gpt_or_claude_review_present" for g in blocking)


def test_quality_gates_pass_with_dual_channel(tmp_path: Path) -> None:
    root = _make_layout(tmp_path)
    candidates = build_apex_agi_absorption_candidates(source_root=root)
    reviews = [
        "gpt55_5yuantoken:/tmp/gpt_review.json",
        "claude_opus47_5yuantoken:/tmp/claude_review.json",
    ]
    gates = run_apex_absorption_quality_gates(candidates, model_reviews=reviews)
    assert all(g["passed"] for g in gates if g["severity"] == "blocking"), gates


def test_secret_material_blocks_absorption(tmp_path: Path) -> None:
    root = _make_layout(tmp_path)
    (root / "web_ui/app.py").write_text("API_KEY=sk-1234567890abcdefABCDEF1234567890\n", encoding="utf-8")
    candidates = build_apex_agi_absorption_candidates(source_root=root)
    deploy = next(item for item in candidates if item["capability_id"] == "apex_local_deployment_safety_profile")
    assert deploy["secret_review_hits"], deploy
    gates = run_apex_absorption_quality_gates(
        candidates,
        model_reviews=[
            "gpt55_5yuantoken:/tmp/gpt_review.json",
            "claude_opus47_5yuantoken:/tmp/claude_review.json",
        ],
    )
    blocked = [g for g in gates if g["severity"] == "blocking" and not g["passed"]]
    assert any(g["gate_name"] == "no_secret_material_absorbed" for g in blocked)


def test_surface_writes_evidence_file(tmp_path: Path) -> None:
    root = _make_layout(tmp_path)
    out_dir = tmp_path / "evidence"
    surface = build_pgg_archon_apex_agi_absorption_surface(
        source_root=root,
        write_report=True,
        report_dir=out_dir,
        model_reviews=[
            "gpt55_5yuantoken:/tmp/gpt_review.json",
            "claude_opus47_5yuantoken:/tmp/claude_review.json",
        ],
    )
    assert surface["status"] == "PASS"
    assert surface["agi_completion_claim"] is False
    assert surface["report_path"], surface
    on_disk = json.loads(Path(surface["report_path"]).read_text(encoding="utf-8"))
    assert on_disk["schema"] == "PGGArchonApexAGIAbsorptionSurface/v1"
    assert on_disk["surface_hash"] == surface["surface_hash"]
