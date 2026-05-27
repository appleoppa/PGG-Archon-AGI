from __future__ import annotations

from agent.apex_gep_deobfuscation import (
    build_deobfuscation_review_report,
    review_source_text,
    shannon_entropy,
)


def test_shannon_entropy_basic_cases():
    assert shannon_entropy("") == 0.0
    assert shannon_entropy("aaaa") == 0.0
    assert shannon_entropy("abcd") == 2.0


def test_clean_source_text_passes_static_only_without_execution():
    result = review_source_text("const safe = true;\nconst x = 1 + 2;", component_id="clean")
    assert result["verdict"] == "PASS"
    assert result["dangerous_patterns"] == []
    assert result["static_only"] is True
    assert result["executed"] is False
    assert result["imported"] is False
    assert result["decoded"] is False
    assert result["trusted"] is False


def test_eval_and_base64_patterns_hold_without_execution():
    result = review_source_text("eval(atob('YWxlcnQoMSk='))", component_id="bad")
    assert result["verdict"] == "HOLD"
    assert "eval_usage" in result["dangerous_patterns"]
    assert "base64_decode" in result["obfuscation_signals"]
    assert result["executed"] is False
    assert result["decoded"] is False


def test_exec_hex_escape_holds():
    result = review_source_text(r"exec('\x70\x72\x69\x6e\x74')", component_id="hex")
    assert result["verdict"] == "HOLD"
    assert "exec_usage" in result["dangerous_patterns"]
    assert "hex_escape" in result["obfuscation_signals"]


def test_default_deobfuscation_review_passes_metadata_only_and_keeps_runtime_locked():
    report = build_deobfuscation_review_report()
    assert report["schema"] == "PggArchonGEPDeobfuscationReview/v1"
    assert report["status"] == "PASS"
    assert report["component_count"] >= 5
    assert report["hold_components"] == []
    assert report["static_only"] is True
    assert report["executed"] is False
    assert report["imported"] is False
    assert report["decoded"] is False
    assert report["trusted"] is False
    assert report["runtime_unlocked"] is False
    assert report["gene_write_allowed"] is False
    assert report["agi_completion_claim"] is False


def test_batch_deobfuscation_review_holds_if_any_component_suspicious():
    report = build_deobfuscation_review_report([
        {"component_id": "clean", "source_text": "const x = 1;"},
        {"component_id": "bad", "source_text": "eval('x')"},
    ])
    assert report["status"] == "HOLD"
    assert report["hold_components"] == ["bad"]
    assert report["runtime_unlocked"] is False
