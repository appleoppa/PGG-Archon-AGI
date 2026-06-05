"""Unit tests for pgg_archon_external_benchmark_provider_run.

These tests use monkeypatched call_chat and load_dotenv_file so they
exercise scoring + aggregation logic without burning real API calls.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from agent import pgg_archon_external_benchmark_provider_run as run_mod


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------
class TestScoreItem:
    def test_yes_match(self):
        score, parsed = run_mod.score_item("yes", "Yes, all A are C.")
        assert score == 1
        assert parsed == "yes"

    def test_no_match(self):
        score, parsed = run_mod.score_item("no", "No, this system cannot replace a lawyer.")
        assert score == 1
        assert parsed == "no"

    def test_yes_expected_no_response(self):
        score, parsed = run_mod.score_item("yes", "No, that is not true.")
        assert score == 0
        assert parsed == ""

    def test_calculator_or_code(self):
        score, parsed = run_mod.score_item(
            "calculator_or_code",
            "Use the calculator tool or run a Python expression to compute 17*19.",
        )
        assert score == 1
        assert parsed in run_mod._EXPECTED_PATTERNS["calculator_or_code"]

    def test_evidence_first(self):
        score, parsed = run_mod.score_item(
            "evidence_first",
            "First summarize the evidence, then form a conclusion.",
        )
        assert score == 1
        assert parsed in run_mod._EXPECTED_PATTERNS["evidence_first"]

    def test_empty_response(self):
        score, parsed = run_mod.score_item("yes", "")
        assert score == 0
        assert parsed == ""

    def test_normalize_strips_punctuation(self):
        # Punctuation in the response should not block match
        score, _ = run_mod.score_item("yes", "Yes, definitely.")
        assert score == 1

    def test_pattern_in_middle(self):
        # Pattern found in middle of response
        score, _ = run_mod.score_item(
            "calculator_or_code",
            "I would call a Python function to compute it exactly.",
        )
        assert score == 1


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
class TestAggregate:
    def _rec(self, **kw: Any):
        defaults: dict[str, Any] = dict(
            provider_id="p1", model="m1", item_id="i1", domain="logic",
            prompt="p", expected="yes", raw_response="yes", visible_output_chars=3,
            parsed_answer="yes", score=1, latency_ms=100, http_status=200, error=None,
        )
        defaults.update(kw)
        return run_mod.ProviderItemResult(**defaults)

    def test_per_provider_pass_rate(self):
        recs = [
            self._rec(provider_id="p1", item_id="i1", score=1),
            self._rec(provider_id="p1", item_id="i2", score=0),
            self._rec(provider_id="p2", item_id="i3", score=1),
        ]
        agg = run_mod.aggregate(recs)
        assert agg["per_provider"]["p1"]["total"] == 2
        assert agg["per_provider"]["p1"]["passed"] == 1
        assert agg["per_provider"]["p1"]["pass_rate"] == 0.5
        assert agg["per_provider"]["p2"]["pass_rate"] == 1.0

    def test_per_provider_domain(self):
        recs = [
            self._rec(provider_id="p1", item_id="i1", domain="logic", score=1),
            self._rec(provider_id="p1", item_id="i2", domain="logic", score=0),
            self._rec(provider_id="p1", item_id="i3", domain="tool-use", score=1),
        ]
        agg = run_mod.aggregate(recs)
        assert agg["per_provider_domain"]["p1"]["logic"]["pass_rate"] == 0.5
        assert agg["per_provider_domain"]["p1"]["tool-use"]["pass_rate"] == 1.0

    def test_errors_counted(self):
        recs = [
            self._rec(provider_id="p1", item_id="i1", score=1, error=None),
            self._rec(provider_id="p1", item_id="i2", score=0, error="timeout"),
        ]
        agg = run_mod.aggregate(recs)
        assert agg["per_provider"]["p1"]["errors"] == 1


# ---------------------------------------------------------------------------
# End-to-end with mocked call_chat
# ---------------------------------------------------------------------------
def _fake_call_chat_factory(canned):
    """Build a fake call_chat that returns canned responses by item_id."""
    def _fake(provider, prompt, *, timeout=60):
        # Find which item this prompt belongs to
        for cid, response_text in canned.items():
            if cid in prompt:
                return response_text, 200, 50, None
        return "", 200, 50, "no canned response for prompt"
    return _fake


class TestEndToEnd:
    def test_smoke_run_with_mocks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        # Disable real .env load
        monkeypatch.setattr(run_mod, "load_dotenv_file", lambda: None)
        # Ensure API key env is present (so call_chat doesn't bail on missing key)
        for k in ["DEEPSEEK_V4_FLASH_API_KEY", "MIMO_V25_PRO_API_KEY", "GPT55_5YUANTOKEN_API_KEY"]:
            monkeypatch.setenv(k, "fake-key-for-test")
        # Patch requests.post to return canned responses keyed by seed phrase
        # (since prompts contain the seed phrase, not the domain string).
        canned = {
            "If all A are B": "Yes, all A are C.",
            "What tool is required": "Use a Python function or calculator to compute it.",
            "Can this system replace a lawyer": "No, this system cannot replace a lawyer.",
            "Summarize evidence before conclusion": "First summarize the evidence, then form a conclusion.",
            "Does 33/33 ACTIVE prove full AGI": "No, 33/33 ACTIVE does not prove full AGI.",
        }

        def fake_post(url, headers=None, json=None, timeout=None):
            class _Resp:
                status_code = 200
                text = "{}"

                def json(self):
                    prompt = json["messages"][-1]["content"]
                    for seed, text in canned.items():
                        if seed in prompt:
                            return {"choices": [{"message": {"content": text}}]}
                    return {"choices": [{"message": {"content": "unknown"}}]}

            return _Resp()

        monkeypatch.setattr(run_mod.requests, "post", fake_post)

        out = tmp_path / "run"
        summary = run_mod.run_external_benchmark_100(
            "/Users/appleoppa/.hermes/workspace/audit/systemwide_agi_audit_20260605/triad_eval_round3/external_benchmark_smoke.json",
            out,
            providers=run_mod.PROVIDERS,
            smoke_limit=5,  # 5 items, one per domain
        )

        assert summary["item_count"] == 5
        assert summary["smoke_limit"] == 5
        # Each provider should have run 5 items
        for pid in [p["provider_id"] for p in run_mod.PROVIDERS]:
            assert pid in summary["per_provider"]
            assert summary["per_provider"][pid]["total"] == 5
        # Files should exist
        assert (out / "summary.json").exists()
        assert (out / "all_results.json").exists()
        for pid in [p["provider_id"] for p in run_mod.PROVIDERS]:
            assert (out / pid / "results.json").exists()
        # With our canned responses, every item should pass for every provider
        # (because all responses match expected)
        for pid in [p["provider_id"] for p in run_mod.PROVIDERS]:
            # logic=yes, tool-use=calculator_or_code, legal-boundary=no,
            # long-context=evidence_first, self-boundary=no
            # All canned responses contain expected patterns
            assert summary["per_provider"][pid]["passed"] == 5
            assert summary["per_provider"][pid]["errors"] == 0

    def test_missing_api_key_marks_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(run_mod, "load_dotenv_file", lambda: None)
        # Make sure no key is set
        for k in ["DEEPSEEK_V4_FLASH_API_KEY", "MIMO_V25_PRO_API_KEY", "GPT55_5YUANTOKEN_API_KEY"]:
            monkeypatch.delenv(k, raising=False)

        out = tmp_path / "run"
        summary = run_mod.run_external_benchmark_100(
            "/Users/appleoppa/.hermes/workspace/audit/systemwide_agi_audit_20260605/triad_eval_round3/external_benchmark_smoke.json",
            out,
            providers=run_mod.PROVIDERS,
            smoke_limit=2,
        )

        for pid in [p["provider_id"] for p in run_mod.PROVIDERS]:
            assert summary["per_provider"][pid]["errors"] == 2
            assert summary["per_provider"][pid]["passed"] == 0
            # Verify per-item error message preserved
            provider_results = json.loads((out / pid / "results.json").read_text())
            for r in provider_results:
                assert r["error"] is not None
                assert "missing api key" in r["error"]

    def test_http_error_handled(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(run_mod, "load_dotenv_file", lambda: None)
        for k in ["DEEPSEEK_V4_FLASH_API_KEY", "MIMO_V25_PRO_API_KEY", "GPT55_5YUANTOKEN_API_KEY"]:
            monkeypatch.setenv(k, "fake-key")

        def fake_post(url, headers=None, json=None, timeout=None):
            class _Resp:
                status_code = 503
                text = "service unavailable"
                def json(self_inner):
                    return {}
            return _Resp()

        monkeypatch.setattr(run_mod.requests, "post", fake_post)

        out = tmp_path / "run"
        summary = run_mod.run_external_benchmark_100(
            "/Users/appleoppa/.hermes/workspace/audit/systemwide_agi_audit_20260605/triad_eval_round3/external_benchmark_smoke.json",
            out,
            providers=run_mod.PROVIDERS[:1],  # only deepseek
            smoke_limit=2,
        )

        assert summary["per_provider"]["deepseek_v4_flash"]["errors"] == 2
        assert summary["per_provider"]["deepseek_v4_flash"]["passed"] == 0
