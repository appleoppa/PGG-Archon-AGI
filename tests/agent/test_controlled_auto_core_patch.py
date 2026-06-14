import json
from pathlib import Path

from agent.controlled_auto_core_patch import controlled_auto_core_patch, validate_promotion_record


def _promotion(path: Path, *, ok: bool = True) -> Path:
    data = {
        "schema": "RouteChainControlledAutonomousPromotion/v1",
        "status": "PROMOTED_CONTROLLED" if ok else "BLOCK",
        "success": ok,
        "gene_id": "gene-x",
        "rollback_plan": "restore backup",
        "agi_completion_claim": False,
        "promotion_hash": "abc",
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_validate_promotion_record_requires_controlled_success(tmp_path):
    good = _promotion(tmp_path / "good.json")
    assert validate_promotion_record(good)["status"] == "PASS"
    bad = _promotion(tmp_path / "bad.json", ok=False)
    report = validate_promotion_record(bad)
    assert report["status"] == "BLOCK"
    assert "promotion_not_controlled_success" in report["issues"]


def test_controlled_auto_core_patch_applies_allowlisted_patch_and_audits(tmp_path, monkeypatch):
    monkeypatch.setenv("PGG_AUTO_CORE_PATCH_ALLOW_EXTERNAL_TEST_TARGETS", "1")
    target = tmp_path / "target.py"
    target.write_text("VALUE = 'old'\n", encoding="utf-8")
    promotion = _promotion(tmp_path / "promotion.json")
    report = controlled_auto_core_patch(
        promotion_path=promotion,
        target_path=target,
        old_text="VALUE = 'old'",
        new_text="VALUE = 'new'",
        reason="unit test",
        verify_commands=[f"python -m py_compile {target}"],
        allowlist=[str(target.relative_to(Path.cwd())) if target.is_relative_to(Path.cwd()) else str(target)],
        audit_dir=tmp_path / "audit",
        backup_dir=tmp_path / "backup",
    )
    assert report["status"] == "PASS"
    assert report["success"] is True
    assert "VALUE = 'new'" in target.read_text(encoding="utf-8")
    assert Path(report["audit_path"]).exists()
    assert Path(report["backup_path"]).exists()


def test_controlled_auto_core_patch_blocks_non_allowlisted_target(tmp_path, monkeypatch):
    monkeypatch.setenv("PGG_AUTO_CORE_PATCH_ALLOW_EXTERNAL_TEST_TARGETS", "1")
    target = tmp_path / "target.py"
    target.write_text("VALUE = 'old'\n", encoding="utf-8")
    promotion = _promotion(tmp_path / "promotion.json")
    report = controlled_auto_core_patch(
        promotion_path=promotion,
        target_path=target,
        old_text="VALUE = 'old'",
        new_text="VALUE = 'new'",
        reason="unit test",
        verify_commands=[],
        allowlist=[],
        audit_dir=tmp_path / "audit",
        backup_dir=tmp_path / "backup",
    )
    assert report["status"] == "BLOCK"
    assert "target_not_allowlisted" in report["issues"]
    assert "VALUE = 'old'" in target.read_text(encoding="utf-8")


def test_controlled_auto_core_patch_rolls_back_on_failed_verification(tmp_path, monkeypatch):
    monkeypatch.setenv("PGG_AUTO_CORE_PATCH_ALLOW_EXTERNAL_TEST_TARGETS", "1")
    target = tmp_path / "target.py"
    target.write_text("VALUE = 'old'\n", encoding="utf-8")
    promotion = _promotion(tmp_path / "promotion.json")
    report = controlled_auto_core_patch(
        promotion_path=promotion,
        target_path=target,
        old_text="VALUE = 'old'",
        new_text="VALUE = 'new'",
        reason="unit test",
        verify_commands=["python -c 'import sys; sys.exit(2)'"],
        allowlist=[str(target)],
        audit_dir=tmp_path / "audit",
        backup_dir=tmp_path / "backup",
    )
    assert report["status"] == "ROLLBACK"
    assert "VALUE = 'old'" in target.read_text(encoding="utf-8")
