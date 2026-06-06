from __future__ import annotations

from dataclasses import dataclass

from agent import pgg_archon_quantum_channel_router as mod


@dataclass
class Provider:
    name: str
    model: str = "m"
    api_mode: str = "chat"


def test_mimo_aliases_are_third_party_judge_only() -> None:
    assert mod._is_third_party_judge_provider("mimo") is True
    assert mod._is_third_party_judge_provider("mimo_v25_pro_auditor") is True
    assert mod._is_third_party_judge_provider("custom:mimo_v25_pro_auditor") is True
    assert mod._is_third_party_judge_provider("deepseek") is False


def test_default_multi_provider_pool_excludes_mimo(monkeypatch) -> None:
    providers = [Provider("deepseek"), Provider("mimo"), Provider("gpt55")]
    monkeypatch.setattr(mod, "PROVIDERS", providers, raising=False)
    assert mod._ordinary_callable_provider_names(providers) == ["deepseek", "gpt55"]


def test_provider_call_rejects_mimo_before_registry_call(monkeypatch) -> None:
    monkeypatch.setattr(
        mod,
        "decide_omniroute_provider",
        lambda task_type="general", requested_provider="": {"selected_provider": "mimo", "task_type": task_type},
    )
    called = {"value": False}
    def fake_call_provider(*args, **kwargs):
        called["value"] = True
        raise AssertionError("MiMo should not be called")
    import agent.pgg_archon_external_benchmark_provider_run as registry
    monkeypatch.setattr(registry, "PROVIDERS", [Provider("mimo")])
    monkeypatch.setattr(registry, "_load_env", lambda *args, **kwargs: 0)
    monkeypatch.setattr(registry, "call_provider", fake_call_provider)
    result = mod.execute_omniroute_provider_call(prompt="hello", requested_provider="mimo")
    assert result["participated"] is False
    assert "reserved for audit/judge" in result["error"]
    assert called["value"] is False


def test_route_enforce_canary_default_off_and_denies_legal(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(mod, "OMNIROUTE_ENFORCE_CONFIG", tmp_path / "enforce.json")
    monkeypatch.setattr(mod, "OMNIROUTE_ENFORCE_EVENTS", tmp_path / "events.jsonl")
    route = {
        "selected_provider": "deepseek",
        "route_policy_version": mod.OMNIROUTE_ROUTE_POLICY_VERSION,
        "route_policy": {"intent": "chinese_legal"},
    }
    decision = mod.evaluate_route_enforce_canary(route, actual_provider="deepseek", model="deepseek-v4-flash")
    assert decision["would_enforce"] is False
    assert decision["fail_open_passthrough"] is True
    assert "config_disabled_default_off" in decision["reasons"]
    assert "intent_denied:chinese_legal" in decision["reasons"]
    assert "intent_not_allowed:chinese_legal" in decision["reasons"]
    assert "Default-off guarded canary" in decision["boundary"]
    assert mod.recent_route_enforce_events(5)


def test_route_enforce_canary_hard_denied_intents_are_immutable(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(mod, "OMNIROUTE_ENFORCE_CONFIG", tmp_path / "enforce.json")
    monkeypatch.setattr(mod, "OMNIROUTE_ENFORCE_EVENTS", tmp_path / "events.jsonl")
    cfg = mod.write_route_enforce_canary_config({
        "enabled": True,
        "mode": "canary",
        "allowed_intents": ["chinese_legal", "audit_judge", "agi_architecture_coding", "general"],
        "denied_intents": [],
    })
    assert set(cfg["hard_denied_intents"]) == mod.OMNIROUTE_HARD_DENIED_ENFORCE_INTENTS
    assert not (set(cfg["allowed_intents"]) & mod.OMNIROUTE_HARD_DENIED_ENFORCE_INTENTS)
    for intent in sorted(mod.OMNIROUTE_HARD_DENIED_ENFORCE_INTENTS):
        route = {
            "selected_provider": "gpt55",
            "route_policy_version": mod.OMNIROUTE_ROUTE_POLICY_VERSION,
            "route_policy": {"intent": intent},
        }
        decision = mod.evaluate_route_enforce_canary(route, actual_provider="custom:gpt55_5yuantoken", model="gpt-5.5")
        assert decision["would_enforce"] is False
        assert decision["fail_open_passthrough"] is True
        assert f"intent_denied:{intent}" in decision["reasons"]


def test_route_enforce_canary_observe_only_policy_mismatch_and_bad_mode_block(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(mod, "OMNIROUTE_ENFORCE_CONFIG", tmp_path / "enforce.json")
    monkeypatch.setattr(mod, "OMNIROUTE_ENFORCE_EVENTS", tmp_path / "events.jsonl")
    mod.write_route_enforce_canary_config({"enabled": True, "mode": "observe_only"})
    route = {"selected_provider": "gpt55", "route_policy_version": mod.OMNIROUTE_ROUTE_POLICY_VERSION, "route_policy": {"intent": "general"}}
    observe = mod.evaluate_route_enforce_canary(route, actual_provider="custom:gpt55_5yuantoken", model="gpt-5.5")
    assert observe["would_enforce"] is False
    assert observe["mode"] == "observe_only"
    mod.write_route_enforce_canary_config({"enabled": True, "mode": "canary"})
    bad_version = dict(route, route_policy_version="old")
    mismatch = mod.evaluate_route_enforce_canary(bad_version, actual_provider="custom:gpt55_5yuantoken", model="gpt-5.5")
    assert mismatch["would_enforce"] is False
    assert "policy_version_mismatch" in mismatch["reasons"]
    cfg = mod.write_route_enforce_canary_config({"mode": "unsafe_replace"})
    assert cfg["mode"] == "observe_only"


def test_route_enforce_canary_allows_only_enabled_safe_match(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(mod, "OMNIROUTE_ENFORCE_CONFIG", tmp_path / "enforce.json")
    monkeypatch.setattr(mod, "OMNIROUTE_ENFORCE_EVENTS", tmp_path / "events.jsonl")
    cfg = mod.write_route_enforce_canary_config({"enabled": True, "mode": "canary"})
    assert cfg["enabled"] is True
    route = {
        "selected_provider": "gpt55",
        "route_policy_version": mod.OMNIROUTE_ROUTE_POLICY_VERSION,
        "route_policy": {"intent": "general"},
    }
    decision = mod.evaluate_route_enforce_canary(route, actual_provider="custom:gpt55_5yuantoken", model="gpt-5.5")
    assert decision["would_enforce"] is True
    assert decision["reasons"] == []
    mismatch = mod.evaluate_route_enforce_canary(route, actual_provider="deepseek", model="deepseek-v4-flash")
    assert mismatch["would_enforce"] is False
    assert any(r.startswith("route_class_mismatch") for r in mismatch["reasons"])


def test_record_core_mirror_includes_route_enforce_canary(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(mod, "OMNIROUTE_ENFORCE_CONFIG", tmp_path / "enforce.json")
    monkeypatch.setattr(mod, "OMNIROUTE_ENFORCE_EVENTS", tmp_path / "events.jsonl")
    monkeypatch.setattr(mod, "OMNIROUTE_MIRROR_EVENTS", tmp_path / "mirror.jsonl")
    route = {
        "selected_provider": "deepseek",
        "route_policy_version": mod.OMNIROUTE_ROUTE_POLICY_VERSION,
        "route_policy": {"intent": "chinese_legal"},
    }
    payload = mod.record_omniroute_core_mirror(user_message="法律任务", result={"final_response": "ok"}, provider="deepseek", model="deepseek-v4-flash", route_suggestion=route)
    assert payload["route_enforce_would_enforce"] is False
    assert payload["route_enforce_canary"]["schema"] == "PGGArchonOmniRouteEnforceDecision/v1"


def test_route_enforce_canary_window_test_passes_rolls_back_and_blocks_leakage(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(mod, "OMNIROUTE_ENFORCE_CONFIG", tmp_path / "enforce.json")
    monkeypatch.setattr(mod, "OMNIROUTE_ENFORCE_EVENTS", tmp_path / "events.jsonl")
    previous = mod.write_route_enforce_canary_config({"enabled": False, "mode": "observe_only"})
    result = mod.run_route_enforce_canary_window_test(1)
    assert result["schema"] == "PGGArchonOmniRouteEnforceCanaryWindowTest/v1"
    assert result["sample_count"] == 10
    assert result["passed"] is True
    assert result["allowed_count"] == 10
    assert result["leakage_count"] == 0
    assert "no provider substitution" in result["boundary"]
    restored = mod.read_route_enforce_canary_config()
    assert restored["enabled"] == previous["enabled"]
    assert restored["mode"] == previous["mode"]


def test_provider_substitution_fallback_is_cross_class_participation_not_same_class_success(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(mod, "OMNIROUTE_SUBSTITUTION_EVENTS", tmp_path / "subst.jsonl")
    monkeypatch.setattr(mod, "plan_provider_substitution_canary", lambda task, task_type="exact": {"allowed": True, "substitution_provider": "gpt55"})
    calls = []

    def fake_execute(task, task_type="", requested_provider="", timeout=60.0):
        calls.append((task_type, requested_provider))
        if requested_provider == "gpt55":
            return {"success": False, "provider": "gpt55", "error": "registry failed"}
        return {"success": False, "participated": True, "provider": requested_provider, "http_status": 200, "parsed_text_preview": "ok"}

    monkeypatch.setattr(mod, "execute_omniroute_task", fake_execute)
    result = mod.execute_provider_substitution_canary("Reply exactly: PGG_V30_CANARY_OK", fallback_provider="deepseek")
    assert result["success"] is True
    assert result["same_class_substitution_success"] is False
    assert result["fallback_participation_success"] is True
    assert result["fallback_execution"]["cross_class_fallback"] is True
    assert result["fallback_execution"]["fallback_from_provider"] == "gpt55"
    assert "not be counted as same-class GPT substitution success" in result["fallback_execution"]["boundary"]
    assert calls == [("substitution_canary:exact", "gpt55"), ("substitution_canary_fallback:exact", "deepseek")]


def test_provider_substitution_fallback_window_summarizes_cross_class(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(mod, "OMNIROUTE_SUBSTITUTION_EVENTS", tmp_path / "subst.jsonl")
    def fake_plan(task, task_type="exact"):
        if task_type in mod.OMNIROUTE_HARD_DENIED_ENFORCE_INTENTS or task_type in {"legal", "audit", "agi"}:
            return {"allowed": False, "substitution_provider": "", "enforce_decision": {"reasons": [f"intent_denied:{task_type}"]}}
        return {"allowed": True, "substitution_provider": "gpt55", "enforce_decision": {"reasons": []}}

    monkeypatch.setattr(mod, "plan_provider_substitution_canary", fake_plan)
    monkeypatch.setattr(mod, "execute_provider_substitution_canary", lambda task, task_type="exact", timeout=60.0, fallback_provider="deepseek": {
        "success": True,
        "same_class_substitution_success": False,
        "fallback_participation_success": True,
        "execution": {"provider": "gpt55", "http_status": 502, "participated": False},
        "fallback_execution": {"provider": fallback_provider, "http_status": 200, "participated": True, "cross_class_fallback": True, "answer_preview": "ok"},
    })
    summary = mod.run_provider_substitution_fallback_window(sample_count=1, fallback_provider="deepseek")
    assert summary["sample_count"] == 2
    assert summary["passed"] is True
    assert summary["primary_success_count"] == 0
    assert summary["fallback_success_count"] == 2
    assert summary["cross_class_fallback_count"] == 2
    assert "not GPT same-class substitution" in summary["boundary"]


def test_route_policy_intent_classification_order_and_version() -> None:
    assert mod.OMNIROUTE_ROUTE_POLICY_VERSION == "v2.6-fresh-calibrated-window-20260606"
    assert mod._classify_route_intent(prompt="legal contract litigation review")["intent"] == "chinese_legal"
    assert mod._classify_route_intent(prompt="PGG Archon audit evaluation verdict")["intent"] == "audit_judge"
    assert mod._classify_route_intent(prompt="PGG Archon Rust router compile fix")["intent"] == "agi_architecture_coding"


def test_route_policy_version_is_emitted_in_decision_and_mirror(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(mod, "OMNIROUTE_ROUTE_CALL_EVENTS", tmp_path / "route_events.jsonl")
    monkeypatch.setattr(mod, "OMNIROUTE_MIRROR_EVENTS", tmp_path / "mirror_events.jsonl")
    decision = mod.decide_omniroute_provider(task_type="general", prompt_preview="hello")
    assert decision["route_policy_version"] == mod.OMNIROUTE_ROUTE_POLICY_VERSION
    mod.record_omniroute_core_mirror(
        user_message="hello",
        result={"final_response": "ok", "completed": True, "api_calls": 1},
        provider="deepseek",
        model="m",
        route_suggestion=decision,
    )
    assert mod.OMNIROUTE_ROUTE_POLICY_VERSION in (tmp_path / "mirror_events.jsonl").read_text(encoding="utf-8")


def test_multi_provider_explicit_mimo_is_recorded_failed_not_called(monkeypatch) -> None:
    import agent.pgg_archon_external_benchmark_provider_run as registry
    monkeypatch.setattr(registry, "PROVIDERS", [Provider("deepseek"), Provider("mimo")])
    monkeypatch.setattr(registry, "_load_env", lambda *args, **kwargs: 0)
    calls = []
    def fake_call_provider(provider, prompt, timeout):
        calls.append(provider.name)
        return {"http_status": 200, "parsed_text": "ok", "elapsed_sec": 0.01, "error": ""}
    monkeypatch.setattr(registry, "call_provider", fake_call_provider)
    result = mod.execute_omniroute_multi_provider_task("hello", providers=["deepseek", "mimo"], cooldown_sec=0)
    assert calls == ["deepseek"]
    assert result["successful_count"] == 1
    failed = [c for c in result["calls"] if c["provider"] == "mimo"][0]
    assert failed["participated"] is False
    assert "reserved for audit/judge" in failed["error"]