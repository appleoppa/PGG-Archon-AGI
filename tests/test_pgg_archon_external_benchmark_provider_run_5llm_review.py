"""Unit tests for pgg_archon_external_benchmark_provider_run_5llm_review.

Mocked HTTP for each of the 5 audit providers; MiniMax response includes a
<think> block to exercise the structured adapter path.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from agent import pgg_archon_external_benchmark_provider_run_5llm_review as rev_mod


SAMPLE_SUMMARY: dict[str, Any] = {
    "schema": "PGGArchonExternalBenchmarkProviderRun/v1",
    "spec_path": "/tmp/spec.json",
    "item_count": 100,
    "per_provider": {
        "deepseek_v4_flash": {"model": "deepseek-v4-flash", "total": 100, "passed": 80, "pass_rate": 0.8, "errors": 0},
        "mimo_v25_pro_auditor": {"model": "mimo-v2.5-pro", "total": 100, "passed": 70, "pass_rate": 0.7, "errors": 5},
        "gpt55_5yuantoken": {"model": "gpt-5.5", "total": 100, "passed": 75, "pass_rate": 0.75, "errors": 0},
    },
    "per_provider_domain": {
        "deepseek_v4_flash": {
            "logic": {"total": 20, "passed": 18, "pass_rate": 0.9},
            "tool-use": {"total": 20, "passed": 12, "pass_rate": 0.6},
            "legal-boundary": {"total": 20, "passed": 18, "pass_rate": 0.9},
            "long-context": {"total": 20, "passed": 14, "pass_rate": 0.7},
            "self-boundary": {"total": 20, "passed": 18, "pass_rate": 0.9},
        },
    },
    "boundary": "Real provider-run of 100-item frozen internal benchmark. NOT an official MMLU/GSM8K/BigBench/LegalBench score.",
}


def _canned_response(provider: str) -> str:
    """Return a JSON verdict string tailored per provider."""
    base = {
        "real_progress": [
            "Real provider-run of 100 frozen items completed; per-provider pass_rates are recorded honestly.",
        ],
        "remaining_gaps": [
            "Short-answer substring scorer is coarse; semantic correctness not measured.",
        ],
        "next_actions": [
            "Run provider safety eval (P1) and reproducible research artifact (P2).",
        ],
        "caveats": [
            "Not an official external benchmark. Boundary must not be relaxed.",
        ],
    }
    if provider == "deepseek":
        return json.dumps({"verdict": "WATCH", "updated_agi_score_0_100": 41, "level": "L1", **base})
    if provider == "mimo":
        return json.dumps({"verdict": "PASS", "updated_agi_score_0_100": 45, "level": "L1", **base})
    if provider == "agnes":
        return json.dumps({"verdict": "WATCH", "updated_agi_score_0_100": 30, "level": "L0", **base})
    if provider == "minimax":
        # Wrap in <think> block to exercise structured adapter
        verdict = {"verdict": "WATCH", "updated_agi_score_0_100": 50, "level": "L1", **base}
        return "<think>analysis</think>\n" + json.dumps(verdict)
    if provider == "gpt55":
        return json.dumps({"verdict": "WATCH", "updated_agi_score_0_100": 48, "level": "L1", **base})
    return json.dumps({"verdict": "WATCH", "updated_agi_score_0_100": 30, "level": "L0", **base})


class TestAuditPrompt:
    def test_prompt_contains_summary(self):
        prompt = rev_mod._build_audit_prompt(SAMPLE_SUMMARY)
        assert "deepseek_v4_flash" in prompt
        assert "real provider-run" in prompt.lower() or "real provider run" in prompt.lower()
        # Should ask for structured JSON output
        assert "verdict" in prompt
        assert "updated_agi_score_0_100" in prompt
        # Should include the boundary statement
        assert "NOT an official MMLU" in prompt


class TestRun5LLMReview:
    def test_all_5_providers_parsed(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(rev_mod, "load_dotenv_file", lambda: None)
        for k in [p["key_env"] for p in rev_mod.AUDIT_PROVIDERS]:
            monkeypatch.setenv(k, "fake-key")

        def fake_post(url, headers=None, json=None, timeout=None):
            class _Resp:
                status_code = 200
                text = "{}"

                def json(self):
                    # Heuristic: pick canned by URL host
                    if "deepseek" in url:
                        body = _canned_response("deepseek")
                    elif "mimo" in url or "xiaomi" in url:
                        body = _canned_response("mimo")
                    elif "agnes" in url:
                        body = _canned_response("agnes")
                    elif "minimax" in url:
                        body = _canned_response("minimax")
                    elif "chuangagent" in url:
                        body = _canned_response("gpt55")
                    else:
                        body = _canned_response("deepseek")
                    return {"choices": [{"message": {"content": body}}]}

            return _Resp()

        monkeypatch.setattr(rev_mod.requests, "post", fake_post)

        out = rev_mod.run_5llm_review(SAMPLE_SUMMARY, providers=rev_mod.AUDIT_PROVIDERS)
        # All 5 should have ok=True and parsed dict
        for pid in [p["provider_id"] for p in rev_mod.AUDIT_PROVIDERS]:
            assert pid in out["providers"]
            assert out["providers"][pid]["ok"] is True
            assert out["providers"][pid]["parsed"] is not None
            assert out["providers"][pid]["parsed"]["verdict"] in {"WATCH", "PASS", "BLOCKED"}
        assert out["structured_provider_count"] == 5
        # MiniMax path: verify the <think> stripping worked
        mm_raw = out["providers"]["minimax"]["raw_preview"]
        assert "<think>" not in mm_raw or "verdict" in mm_raw  # parsed dict was extracted from <think>-stripped text
        # Mean score = (41+45+30+50+48)/5 = 42.8
        assert abs(out["mean_score"] - 42.8) < 0.1
        assert out["verdicts"] == ["WATCH", "PASS", "WATCH", "WATCH", "WATCH"]
        # boundary
        assert "Claude excluded" in out["boundary"]
        assert "MiniMax parsed via pgg_archon_minimax_structured_adapter" in out["boundary"]

    def test_missing_api_key_marks_error(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(rev_mod, "load_dotenv_file", lambda: None)
        for k in [p["key_env"] for p in rev_mod.AUDIT_PROVIDERS]:
            monkeypatch.delenv(k, raising=False)

        out = rev_mod.run_5llm_review(SAMPLE_SUMMARY, providers=rev_mod.AUDIT_PROVIDERS)
        for pid in [p["provider_id"] for p in rev_mod.AUDIT_PROVIDERS]:
            assert out["providers"][pid]["ok"] is False
            assert "missing api key" in out["providers"][pid]["error"]
        assert out["structured_provider_count"] == 0
        assert out["mean_score"] == 0.0

    def test_http_5xx_marks_error(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(rev_mod, "load_dotenv_file", lambda: None)
        for k in [p["key_env"] for p in rev_mod.AUDIT_PROVIDERS]:
            monkeypatch.setenv(k, "fake-key")

        def fake_post_500(url, headers=None, json=None, timeout=None):
            class _Resp:
                status_code = 500
                text = "internal error"
                def json(self):
                    return {}
            return _Resp()

        monkeypatch.setattr(rev_mod.requests, "post", fake_post_500)

        out = rev_mod.run_5llm_review(SAMPLE_SUMMARY, providers=rev_mod.AUDIT_PROVIDERS)
        for pid in [p["provider_id"] for p in rev_mod.AUDIT_PROVIDERS]:
            assert out["providers"][pid]["ok"] is False
            assert "HTTP 500" in out["providers"][pid]["error"]
        assert out["structured_provider_count"] == 0

    def test_unparseable_response_recorded(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setattr(rev_mod, "load_dotenv_file", lambda: None)
        for k in [p["key_env"] for p in rev_mod.AUDIT_PROVIDERS]:
            monkeypatch.setenv(k, "fake-key")

        def fake_post_bad_json(url, headers=None, json=None, timeout=None):
            class _Resp:
                status_code = 200
                text = "{}"

                def json(self):
                    # Not a JSON, not even close
                    return {"choices": [{"message": {"content": "Sorry, I cannot help with that."}}]}

            return _Resp()

        monkeypatch.setattr(rev_mod.requests, "post", fake_post_bad_json)

        out = rev_mod.run_5llm_review(SAMPLE_SUMMARY, providers=rev_mod.AUDIT_PROVIDERS)
        # Each provider gets text but parse fails; ok=True but parsed=None
        for pid in [p["provider_id"] for p in rev_mod.AUDIT_PROVIDERS]:
            assert out["providers"][pid]["ok"] is True
            assert out["providers"][pid]["parsed"] is None
        assert out["structured_provider_count"] == 0
        assert out["mean_score"] == 0.0
