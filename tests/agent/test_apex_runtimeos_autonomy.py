import json

from agent.apex_runtimeos_autonomy import (
    apply_runtime_rewrite,
    build_runtime_rewrite_plan,
    build_runtimeos_health_report,
    build_runtimeos_health_watchdog_notice,
    _watchdog_config,
    execute_promotion_rollbacks,
    persist_autowrite_candidate,
    promote_autowrite_candidates,
    record_cron_dryrun_result,
    run_autopromotion_scheduler,
    score_autowrite_candidates,
    summarize_autonomy_status,
    summarize_cron_dryrun_ledger,
)


class DummyCompressorAgent:
    compression_enabled = True
    context_compressor = object()

    def _compress_context(self, messages, system_message, approx_tokens=None, task_id=None):
        return messages[:1] + messages[-1:], "compressed-system"


def _heavy_checkpoint():
    return {
        "recommendations": {
            "status": "WATCH",
            "items": [
                {
                    "organ": "planner",
                    "code": "planner_context_heavy",
                    "severity": "warn",
                    "actions": ["compress_context", "review_budget"],
                    "applied": False,
                    "mutates_runtime": False,
                }
            ],
        }
    }


def test_runtime_rewrite_plan_disabled_by_default(monkeypatch):
    monkeypatch.delenv("APEX_RUNTIMEOS_AUTO_REWRITE_ENABLED", raising=False)
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    plan = build_runtime_rewrite_plan(_heavy_checkpoint())
    assert plan["enabled"] is False
    assert plan["actions"] == []
    assert plan["mutates_runtime"] is False


def test_runtime_rewrite_applies_compression_only_when_enabled(monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTO_REWRITE_ENABLED", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    messages = [
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
    ]
    result = apply_runtime_rewrite(
        agent=DummyCompressorAgent(),
        messages=messages,
        system_message="sys",
        active_system_prompt="sys",
        approx_tokens=999999,
        task_id="t1",
        checkpoint=_heavy_checkpoint(),
    )
    assert result["applied"] is True
    assert result["mutates_runtime"] is True
    assert result["before_message_count"] == 3
    assert result["after_message_count"] == 2
    assert result["messages"] == [messages[0], messages[-1]]


def test_autowrite_candidate_is_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path))
    monkeypatch.delenv("APEX_RUNTIMEOS_AUTO_WRITE_ENABLED", raising=False)
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    result = persist_autowrite_candidate(stage="pre_completion", session_id="secret-session", recommendations=_heavy_checkpoint()["recommendations"])
    assert result["written"] is False
    assert not (tmp_path / "candidates.jsonl").exists()


def test_autowrite_candidate_writes_sanitized_promotion_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path))
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTO_WRITE_ENABLED", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    result = persist_autowrite_candidate(
        stage="pre_completion",
        session_id="secret-session",
        recommendations={
            "status": "WATCH",
            "items": [
                {
                    "organ": "gene_selector",
                    "code": "gene_completion_incomplete",
                    "severity": "warn",
                    "actions": ["hold_gene_entry", "/Users/appleoppa/private"],
                    "reason": "raw prompt should not be stored",
                }
            ],
        },
    )
    assert result["written"] is True
    assert result["promotion_required"] is True
    assert result["applied_to_core_memory_or_skill"] is False
    raw = (tmp_path / "candidates.jsonl").read_text(encoding="utf-8")
    assert "/Users/appleoppa/private" not in raw
    assert "secret-session" not in raw
    record = json.loads(raw)
    assert record["schema"] == "ApexRuntimeOSAutoWriteCandidate/v1"
    assert record["promotion_required"] is True
    assert record["applied_to_core_memory_or_skill"] is False
    assert record["items"][0]["actions"][1] == "[REDACTED_PATH]"
    assert "reason" not in record["items"][0]


def test_promotion_enabled_by_default_but_requires_candidates(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.delenv("APEX_RUNTIMEOS_PROMOTION_ENABLED", raising=False)
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    result = promote_autowrite_candidates(candidate_path=tmp_path / "missing.jsonl", target="memory")
    assert result["enabled"] is True
    assert result["promoted"] == 0
    assert result["skipped"] == 0


def test_promote_candidate_to_memory_with_audit_and_dedup(tmp_path, monkeypatch):
    home = tmp_path / "hermes_home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setenv("APEX_RUNTIMEOS_PROMOTION_ENABLED", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    monkeypatch.setenv("APEX_RUNTIMEOS_BYPASS_GENE_LIFECYCLE_GATE", "1")
    candidate_path = tmp_path / "candidates.jsonl"
    candidate = {
        "schema": "ApexRuntimeOSAutoWriteCandidate/v1",
        "promotion_required": True,
        "items": [{"code": "planner_context_heavy", "severity": "warn", "actions": ["compress_context"]}],
    }
    candidate_path.write_text(json.dumps(candidate, ensure_ascii=False) + "\n" + json.dumps(candidate, ensure_ascii=False) + "\n", encoding="utf-8")
    first = promote_autowrite_candidates(candidate_path=candidate_path, target="memory")
    second = promote_autowrite_candidates(candidate_path=candidate_path, target="memory")
    assert first["promoted"] == 1
    assert first["skipped"] == 1
    assert second["promoted"] == 0
    assert second["details"][0]["reason"] == "duplicate_existing_promotion"
    assert (home / "memories" / "MEMORY.md").exists()
    memory_text = (home / "memories" / "MEMORY.md").read_text(encoding="utf-8")
    assert "planner_context_heavy" in memory_text
    assert "factual task completion" in memory_text
    audit_text = (tmp_path / "auto" / "promotions.jsonl").read_text(encoding="utf-8")
    assert "ApexRuntimeOSPromotion/v1" in audit_text
    assert "rollback" in audit_text
    assert str(home) not in audit_text


def test_promote_candidate_to_skill_with_rollback_metadata(tmp_path, monkeypatch):
    home = tmp_path / "hermes_home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setenv("APEX_RUNTIMEOS_PROMOTION_ENABLED", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    monkeypatch.setenv("APEX_RUNTIMEOS_BYPASS_GENE_LIFECYCLE_GATE", "1")
    candidate_path = tmp_path / "candidates.jsonl"
    candidate = {
        "schema": "ApexRuntimeOSAutoWriteCandidate/v1",
        "promotion_required": True,
        "items": [{"code": "gene_completion_incomplete", "severity": "warn", "actions": ["hold_gene_entry"]}],
    }
    candidate_path.write_text(json.dumps(candidate, ensure_ascii=False) + "\n", encoding="utf-8")
    result = promote_autowrite_candidates(candidate_path=candidate_path, target="skill")
    assert result["promoted"] == 1
    skill_path = home / "skills" / "apex-runtimeos-autogen" / "SKILL.md"
    assert skill_path.exists()
    text = skill_path.read_text(encoding="utf-8")
    assert "gene_completion_incomplete" in text
    assert "不包含原始对话、路径或凭据" in text
    audit_text = (tmp_path / "auto" / "promotions.jsonl").read_text(encoding="utf-8")
    assert "path_hash" in audit_text
    assert str(skill_path) not in audit_text


def test_stability_score_requires_min_occurrences(tmp_path):
    candidate_path = tmp_path / "candidates.jsonl"
    c1 = {"schema": "ApexRuntimeOSAutoWriteCandidate/v1", "promotion_required": True, "items": [{"code": "planner_context_heavy", "severity": "warn"}]}
    c2 = {"schema": "ApexRuntimeOSAutoWriteCandidate/v1", "promotion_required": True, "items": [{"code": "planner_context_heavy", "severity": "warn"}]}
    c3 = {"schema": "ApexRuntimeOSAutoWriteCandidate/v1", "promotion_required": True, "items": [{"code": "gene_completion_incomplete", "severity": "warn"}]}
    candidate_path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [c1, c2, c3]) + "\n", encoding="utf-8")
    score = score_autowrite_candidates(candidate_path=candidate_path, min_occurrences=2)
    assert score["ready_count"] == 1
    assert score["ready"][0]["key"] == "planner_context_heavy"
    assert score["ready"][0]["count"] == 2


def test_promotion_holds_when_gene_lifecycle_not_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setenv("APEX_RUNTIMEOS_PROMOTION_ENABLED", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    monkeypatch.setenv("APEX_GENE_LIFECYCLE_DB_PATH", str(tmp_path / "missing.sqlite3"))
    candidate_path = tmp_path / "candidates.jsonl"
    candidate_path.write_text(json.dumps({"schema": "ApexRuntimeOSAutoWriteCandidate/v1", "promotion_required": True, "items": [{"code": "planner_context_heavy", "severity": "warn"}]}, ensure_ascii=False) + "\n", encoding="utf-8")
    result = promote_autowrite_candidates(candidate_path=candidate_path, target="memory")
    assert result["promoted"] == 0
    assert result["reason"] == "gene_lifecycle_hold"
    assert result["lifecycle_gate"]["status"] == "HOLD"
    assert result["lifecycle_gate"]["lifecycle_status"] == "BLOCK"


def test_autopromotion_holds_when_gene_lifecycle_not_pass(tmp_path, monkeypatch):
    candidate_path = tmp_path / "candidates.jsonl"
    candidate = {"schema": "ApexRuntimeOSAutoWriteCandidate/v1", "promotion_required": True, "items": [{"code": "planner_context_heavy", "severity": "warn"}]}
    candidate_path.write_text(json.dumps(candidate, ensure_ascii=False) + "\n" + json.dumps(candidate, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOPROMOTE_ENABLED", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    monkeypatch.setenv("APEX_GENE_LIFECYCLE_DB_PATH", str(tmp_path / "missing.sqlite3"))
    result = run_autopromotion_scheduler(candidate_path=candidate_path, min_occurrences=2)
    assert result["promoted"] == 0
    assert result["score"]["ready_count"] == 1
    assert result["reason"] == "gene_lifecycle_hold"
    assert result["lifecycle_gate"]["status"] == "HOLD"


def test_autopromotion_scheduler_enabled_by_default_after_scoring(tmp_path, monkeypatch):
    home = tmp_path / "hermes_home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setenv("APEX_RUNTIMEOS_BYPASS_GENE_LIFECYCLE_GATE", "1")
    candidate_path = tmp_path / "candidates.jsonl"
    candidate = {"schema": "ApexRuntimeOSAutoWriteCandidate/v1", "promotion_required": True, "items": [{"code": "planner_context_heavy", "severity": "warn"}]}
    candidate_path.write_text(json.dumps(candidate, ensure_ascii=False) + "\n" + json.dumps(candidate, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.delenv("APEX_RUNTIMEOS_AUTOPROMOTE_ENABLED", raising=False)
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    result = run_autopromotion_scheduler(candidate_path=candidate_path, min_occurrences=2)
    assert result["enabled"] is True
    assert result["promoted"] == 1
    assert result["score"]["ready_count"] == 1


def test_autopromotion_scheduler_promotes_stable_memory(tmp_path, monkeypatch):
    home = tmp_path / "hermes_home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOPROMOTE_ENABLED", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    monkeypatch.setenv("APEX_RUNTIMEOS_BYPASS_GENE_LIFECYCLE_GATE", "1")
    candidate_path = tmp_path / "candidates.jsonl"
    stable = {"schema": "ApexRuntimeOSAutoWriteCandidate/v1", "promotion_required": True, "items": [{"code": "planner_context_heavy", "severity": "warn", "actions": ["compress_context"]}]}
    unstable = {"schema": "ApexRuntimeOSAutoWriteCandidate/v1", "promotion_required": True, "items": [{"code": "gene_completion_incomplete", "severity": "warn"}]}
    candidate_path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [stable, stable, unstable]) + "\n", encoding="utf-8")
    result = run_autopromotion_scheduler(candidate_path=candidate_path, target="memory", min_occurrences=2)
    assert result["promoted"] == 1
    assert result["score"]["ready_count"] == 1
    memory_text = (home / "memories" / "MEMORY.md").read_text(encoding="utf-8")
    assert "planner_context_heavy" in memory_text
    assert "gene_completion_incomplete" not in memory_text


def test_rollback_disabled_defaults_to_dry_run(tmp_path, monkeypatch):
    audit_path = tmp_path / "promotions.jsonl"
    record = {"schema": "ApexRuntimeOSPromotion/v1", "target": "memory", "success": True, "content_hash": "h1", "rollback": {"action": "remove", "old_text": "x"}, "rollback_status": "pending"}
    audit_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.delenv("APEX_RUNTIMEOS_ROLLBACK_ENABLED", raising=False)
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    result = execute_promotion_rollbacks(audit_path=audit_path, target="memory", dry_run=False)
    assert result["dry_run"] is True
    assert result["rolled_back"] == 1
    assert result["events"][0]["status"] == "dry_run"


def test_rollback_memory_remove_executes_when_enabled(tmp_path, monkeypatch):
    home = tmp_path / "hermes_home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("APEX_RUNTIMEOS_ROLLBACK_ENABLED", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    mem = home / "memories" / "MEMORY.md"
    mem.parent.mkdir(parents=True)
    mem.write_text("entry to remove", encoding="utf-8")
    audit_path = tmp_path / "promotions.jsonl"
    record = {"schema": "ApexRuntimeOSPromotion/v1", "target": "memory", "success": True, "content_hash": "h1", "rollback": {"action": "remove", "old_text": "entry to remove"}, "rollback_status": "pending"}
    audit_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    result = execute_promotion_rollbacks(audit_path=audit_path, target="memory", dry_run=False)
    assert result["rolled_back"] == 1
    assert "entry to remove" not in mem.read_text(encoding="utf-8")
    raw = audit_path.read_text(encoding="utf-8")
    assert "ApexRuntimeOSRollbackEvent/v1" in raw
    assert "\"rollback_status\":\"done\"" in raw
    second = execute_promotion_rollbacks(audit_path=audit_path, target="memory", dry_run=False)
    assert second["rolled_back"] == 0
    assert second["events"][0]["reason"] == "already_done"


def test_rollback_skill_delete_checks_current_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_ROLLBACK_ENABLED", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    skill = tmp_path / "SKILL.md"
    skill.write_text("new content", encoding="utf-8")
    from agent.apex_runtimeos_autonomy import _hash_text
    audit_path = tmp_path / "promotions.jsonl"
    record = {"schema": "ApexRuntimeOSPromotion/v1", "target": "skill", "success": True, "content_hash": "h2", "rollback": {"action": "delete", "path": str(skill), "current_content_hash": _hash_text("different")}, "rollback_status": "pending"}
    audit_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    result = execute_promotion_rollbacks(audit_path=audit_path, target="skill", dry_run=False)
    assert result["rolled_back"] == 0
    assert result["events"][0]["reason"] == "content_hash_mismatch"
    assert skill.exists()


def test_rollback_skill_restore_executes_when_hash_matches(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_ROLLBACK_ENABLED", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    skill = tmp_path / "SKILL.md"
    skill.write_text("new content", encoding="utf-8")
    from agent.apex_runtimeos_autonomy import _hash_text
    audit_path = tmp_path / "promotions.jsonl"
    record = {"schema": "ApexRuntimeOSPromotion/v1", "target": "skill", "success": True, "content_hash": "h3", "rollback": {"action": "restore", "path": str(skill), "current_content_hash": _hash_text("new content"), "old_content": "old content"}, "rollback_status": "pending"}
    audit_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    result = execute_promotion_rollbacks(audit_path=audit_path, target="skill", dry_run=False)
    assert result["rolled_back"] == 1
    assert skill.read_text(encoding="utf-8") == "old content"


def test_apex_runtimeos_cli_rollback_dry_run_json(monkeypatch, tmp_path):
    from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli
    monkeypatch.setenv("APEX_RUNTIMEOS_PROMOTION_AUDIT_PATH", str(tmp_path / "promotions.jsonl"))
    output = run_apex_runtimeos_cli(["rollback", "--json"])
    data = json.loads(output)
    assert data["object"] == "hermes.apex_runtimeos.rollback"
    assert data["result"]["dry_run"] is True


def test_cron_dryrun_ledger_records_redacted_idempotent_summary(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    payload = {
        "task": "apex-runtimeos-autopromote-dryrun",
        "enabled": False,
        "mode": "warn",
        "ready_count": 0,
        "secret": "sk-sho...pear",
        "path": str(tmp_path / "private"),
    }
    first = record_cron_dryrun_result(task="apex-runtimeos-autopromote-dryrun", result=payload, ledger_path=ledger)
    second = record_cron_dryrun_result(task="apex-runtimeos-autopromote-dryrun", result=payload, ledger_path=ledger)
    assert first["ledger_key"] == second["ledger_key"]
    assert second["count"] == 2
    raw = ledger.read_text(encoding="utf-8")
    assert "sk-sho...pear" not in raw
    assert str(tmp_path) not in raw
    summary = summarize_cron_dryrun_ledger(ledger_path=ledger)
    assert summary["unique_keys"] == 1
    assert summary["tasks"]["apex-runtimeos-autopromote-dryrun"]["total_count"] == 2


def test_cron_dryrun_ledger_bad_lines_quarantined_only_when_enabled(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.jsonl"
    record_cron_dryrun_result(task="apex-runtimeos-rollback-dryrun", result={"task": "apex-runtimeos-rollback-dryrun", "mode": "warn"}, ledger_path=ledger)
    ledger.write_text(ledger.read_text(encoding="utf-8") + "not-json-secret-token\n", encoding="utf-8")
    summary = summarize_cron_dryrun_ledger(ledger_path=ledger)
    assert summary["bad_lines"] == 1
    assert summary["quarantine_exists"] is False
    assert "not-json-secret-token" in ledger.read_text(encoding="utf-8")

    monkeypatch.setenv("APEX_RUNTIMEOS_CRON_LEDGER_REPAIR_ENABLED", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    repaired = summarize_cron_dryrun_ledger(ledger_path=ledger)
    assert repaired["bad_lines"] == 1
    assert repaired["repair_enabled"] is True
    assert (tmp_path / "ledger.jsonl.bad").exists()
    assert "not-json-secret-token" not in ledger.read_text(encoding="utf-8")
    assert "not-json-secret-token" not in (tmp_path / "ledger.jsonl.bad").read_text(encoding="utf-8")


def test_runtimeos_health_report_threshold_alerts():
    report = build_runtimeos_health_report({
        "pending_rollbacks": 2,
        "stable_ready_count": 1,
        "autopromote_enabled": False,
        "cron_dryrun": {"bad_lines": 1, "unique_keys": 3},
        "quality_gate": {"status": "BLOCK", "blocking_failed": 2, "warning_failed": 1},
    })
    assert report["status"] == "WATCH"
    assert report["alert_count"] == 4
    codes = {item["code"] for item in report["alerts"]}
    assert "cron_ledger_bad_lines" in codes
    assert "pending_rollbacks" in codes
    assert "stable_candidates_waiting" in codes
    assert "cmmi_quality_gate_not_pass" in codes
    assert report["side_effects"] == "read_only_report"


def test_runtimeos_health_uses_unresolved_stable_candidates_when_available():
    report = build_runtimeos_health_report({
        "pending_rollbacks": 0,
        "stable_ready_count": 1,
        "stable_ready_unresolved_count": 0,
        "autopromote_enabled": False,
        "cron_dryrun": {"bad_lines": 0, "unique_keys": 3},
    })
    assert report["status"] == "OK"
    assert report["alert_count"] == 0
    assert report["metrics"]["stable_ready_count"] == 0
    assert report["metrics"]["stable_ready_total_count"] == 1


def test_resolved_promoted_candidate_not_counted_as_unresolved(tmp_path, monkeypatch):
    home = tmp_path / "hermes_home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setenv("APEX_RUNTIMEOS_PROMOTION_ENABLED", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_ROLLBACK_ENABLED", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_GATE_MODE", "enforce")
    monkeypatch.setenv("APEX_RUNTIMEOS_BYPASS_GENE_LIFECYCLE_GATE", "1")
    monkeypatch.setenv("APEX_RUNTIMEOS_SEQUENCE_LEDGER_PATH", str(tmp_path / "sequence.jsonl"))
    candidate_path = tmp_path / "auto" / "candidates.jsonl"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate = {"schema": "ApexRuntimeOSAutoWriteCandidate/v1", "promotion_required": True, "items": [{"code": "planner_context_heavy", "severity": "warn", "actions": ["compress_context"]}]}
    candidate_path.write_text(json.dumps(candidate, ensure_ascii=False) + "\n" + json.dumps(candidate, ensure_ascii=False) + "\n", encoding="utf-8")
    score = score_autowrite_candidates(candidate_path=candidate_path, min_occurrences=2)
    assert score["ready_count"] == 1
    from agent.apex_runtimeos_autonomy import _candidate_to_memory_entry, _hash_text
    content_hash = _hash_text("memory:" + _candidate_to_memory_entry(candidate))
    audit_path = tmp_path / "auto" / "promotions.jsonl"
    audit_path.write_text(
        json.dumps({
            "schema": "ApexRuntimeOSPromotion/v1",
            "target": "memory",
            "success": True,
            "content_hash": content_hash,
            "rollback": {"action": "remove", "old_text": "planner_context_heavy"},
            "rollback_status": "pending",
        }, ensure_ascii=False) + "\n" +
        json.dumps({
            "schema": "ApexRuntimeOSRollbackEvent/v1",
            "promotion_id": content_hash,
            "target": "memory",
            "rollback_status": "done",
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    status = summarize_autonomy_status(limit=100, min_occurrences=2)
    assert status["stable_ready_count"] == 1
    assert status["stable_ready_unresolved_count"] == 0
    assert status["health_report"]["status"] == "OK"



def test_pending_rollback_closed_by_legacy_content_hash_event(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    audit_path = tmp_path / "auto" / "promotions.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        json.dumps({
            "schema": "ApexRuntimeOSPromotion/v1",
            "promotion_id": "new-style-id",
            "target": "memory",
            "success": True,
            "content_hash": "legacy-hash",
            "rollback": {"action": "remove", "old_text": "x"},
            "rollback_status": "pending",
        }, ensure_ascii=False) + "\n" +
        json.dumps({
            "schema": "ApexRuntimeOSRollbackEvent/v1",
            "promotion_id": "legacy-hash",
            "target": "memory",
            "rollback_status": "done",
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    status = summarize_autonomy_status(limit=100)
    assert status["pending_rollbacks"] == 0
    assert status["rollback_status"]["done"] == 1
    assert status["health_report"]["status"] == "OK"
    assert status["apex_v3_unified_score"]["layers"]["verification"]["signals"]["no_pending_rollbacks"] is True

def test_runtimeos_health_watchdog_notice_suppresses_repeat_watch(tmp_path):
    payload = {
        "status": {
            "health_report": {
                "status": "WATCH",
                "alert_count": 1,
                "alerts": [{"code": "cron_ledger_bad_lines", "severity": "warn", "count": 1}],
            }
        }
    }
    state_path = tmp_path / "watchdog_state.json"
    first = build_runtimeos_health_watchdog_notice(payload, state_path=state_path, cooldown_seconds=2700, now_ts=1000.0)
    second = build_runtimeos_health_watchdog_notice(payload, state_path=state_path, cooldown_seconds=2700, now_ts=1100.0)
    third = build_runtimeos_health_watchdog_notice({"status": {"health_report": {"status": "OK", "alerts": []}}}, state_path=state_path, cooldown_seconds=2700, now_ts=1200.0)
    assert first["should_emit"] is True
    assert first["reason"] == "alert"
    assert second["should_emit"] is False
    assert second["reason"] == "cooldown"
    assert third["should_emit"] is False
    assert third["reason"] == "ok"
    assert not state_path.exists()


def test_runtimeos_health_watchdog_notice_uses_configured_cooldown(tmp_path):
    payload = {
        "status": {
            "health_report": {
                "status": "WATCH",
                "alert_count": 1,
                "alerts": [{"code": "cron_ledger_bad_lines", "severity": "warn", "count": 1}],
            }
        }
    }
    state_path = tmp_path / "watchdog_state.json"
    first = build_runtimeos_health_watchdog_notice(payload, state_path=state_path, cooldown_seconds=60, now_ts=1000.0)
    second = build_runtimeos_health_watchdog_notice(payload, state_path=state_path, cooldown_seconds=60, now_ts=1030.0)
    third = build_runtimeos_health_watchdog_notice(payload, state_path=state_path, cooldown_seconds=60, now_ts=1070.0)
    assert first["should_emit"] is True
    assert second["should_emit"] is False
    assert second["reason"] == "cooldown"
    assert third["should_emit"] is True
    assert third["reason"] == "alert"


def test_watchdog_config_exposes_default_values(monkeypatch):
    monkeypatch.delenv("APEX_RUNTIMEOS_WATCHDOG_STATE_PATH", raising=False)
    monkeypatch.delenv("APEX_RUNTIMEOS_WATCHDOG_COOLDOWN_SECONDS", raising=False)
    cfg = _watchdog_config()
    assert cfg["schema"] == "ApexRuntimeOSWatchdogConfig/v1"
    assert cfg["state_configured"] is False
    assert cfg["cooldown_seconds"] == 2700


def test_autonomy_status_includes_read_only_evm_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    status = summarize_autonomy_status(limit=10)
    assert status["evm_gate"]["schema"] == "ApexRuntimeOSEVMGate/v1"
    assert status["evm_gate"]["side_effects"] == "read_only_report"
    assert status["evm_gate"]["boundary"].startswith("EVM means APEX RuntimeOS")


def test_autonomy_status_includes_read_only_sequence_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setenv("APEX_RUNTIMEOS_SEQUENCE_LEDGER_PATH", str(tmp_path / "sequence.jsonl"))
    status = summarize_autonomy_status(limit=10)
    assert status["sequence_gate"]["schema"] == "ApexRuntimeOSSequenceGate/v1"
    assert status["sequence_gate"]["status"] == "BLOCK"
    assert status["sequence_gate"]["side_effects"] == "read_only_report"
    assert status["sequence_gate"]["missing_sequences"] == ["21354", "12534", "14325"]


def test_autonomy_status_includes_read_only_gene_lifecycle_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setenv("APEX_GENE_LIFECYCLE_DB_PATH", str(tmp_path / "missing.sqlite3"))
    monkeypatch.setattr("agent.apex_co_scientist.load_latest_gene_candidate", lambda: None)
    status = summarize_autonomy_status(limit=10)
    assert status["gene_lifecycle_gate"]["schema"] == "ApexRuntimeOSGeneLifecycleGate/v1"
    assert status["gene_lifecycle_gate"]["status"] == "BLOCK"
    assert status["gene_lifecycle_gate"]["side_effects"] == "read_only_report"
    assert status["gene_lifecycle_gate"]["gene_count"] == 0
    assert status["gene_lifecycle_gate"]["sqlite_read"]["db_exists"] is False


def test_autonomy_status_includes_read_only_formula_report(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    status = summarize_autonomy_status(limit=10)
    assert status["formula_report"]["schema"] == "ApexRuntimeOSFormulaReport/v1"
    assert status["formula_report"]["status"] in {"PASS", "WARN"}
    assert status["formula_report"]["live_params_used"] is True
    assert status["formula_report"]["telemetry_source"] == "runtimeos_aggregate_status"
    assert status["formula_report"]["side_effects"] == "read_only_report"
    assert "aggregate counters" in status["formula_report"]["boundary"]


def test_autonomy_status_includes_read_only_gep_report(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    status = summarize_autonomy_status(limit=10)
    assert status["gep_report"]["schema"] == "ApexRuntimeOSGEPReport/v1"
    assert status["gep_report"]["status"] == "PASS"
    assert status["gep_report"]["side_effects"] == "read_only_report"
    assert status["gep_report"]["capability_index"]["counts"]["archived_obfuscated"] >= 1


def test_autonomy_status_includes_read_only_quality_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setattr("runtime.quality.evidence_bundle.load_latest_quality_evidence_bundle", lambda: None)
    status = summarize_autonomy_status(limit=10)
    quality_gate = status["quality_gate"]
    assert quality_gate["schema"] == "ApexRuntimeOSQualityGateReport/v1"
    assert quality_gate["status"] == "BLOCK"
    assert quality_gate["blocking_failed"] >= 1
    assert quality_gate["evidence_summary"]["requirements"] is True
    assert "test_report" in quality_gate["missing_blocking_evidence"]
    assert quality_gate["side_effects"] == "read_only_report"
    assert quality_gate["boundary"].startswith("CMMI gate is read-only")
    health = status["health_report"]
    assert health["status"] == "WATCH"
    assert health["metrics"]["quality_gate_status"] == "BLOCK"
    assert any(item["code"] == "cmmi_quality_gate_not_pass" for item in health["alerts"])


def test_autonomy_status_uses_latest_quality_evidence_bundle(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    bundle = {
        "schema": "ApexRuntimeOSQualityEvidenceBundle/v1",
        "source": "unit-test",
        "evidence": {
            "test_report": {"present": True, "summary": "tests passed"},
            "audit_log": {"present": True, "summary": "audit present"},
            "documentation": {"present": True, "summary": "docs present"},
        },
    }
    monkeypatch.setattr("runtime.quality.evidence_bundle.load_latest_quality_evidence_bundle", lambda: bundle)
    status = summarize_autonomy_status(limit=10)
    quality_gate = status["quality_gate"]
    assert status["quality_evidence_bundle"]["source"] == "unit-test"
    assert quality_gate["status"] == "PASS"
    assert quality_gate["blocking_failed"] == 0
    assert quality_gate["evidence_bundle"]["valid"] is True
    promotion_gate = status["promotion_lifecycle_gate"]
    assert promotion_gate["quality_evidence_required"] is True
    assert promotion_gate["quality_evidence_valid"] is True
    assert promotion_gate["quality_evidence_hash"]


def test_autonomy_status_holds_promotion_when_quality_evidence_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setenv("APEX_GENE_LIFECYCLE_DB_PATH", str(tmp_path / "missing.sqlite3"))
    monkeypatch.setattr("runtime.quality.evidence_bundle.load_latest_quality_evidence_bundle", lambda: None)
    monkeypatch.setattr("agent.apex_co_scientist.load_latest_gene_candidate", lambda: {
        "schema": "ApexCoScientistGeneCandidateSummary/v1",
        "status": "READY",
        "candidate_id": "candidate-1",
        "eligible": True,
        "evidence_level": "unit-test",
        "gene_library_written": False,
    })
    status = summarize_autonomy_status(limit=10)
    assert status["gene_lifecycle_gate"]["status"] == "PASS"
    promotion_gate = status["promotion_lifecycle_gate"]
    assert promotion_gate["status"] == "HOLD"
    assert promotion_gate["reason"] == "quality_evidence_bundle_missing_or_invalid"
    assert promotion_gate["quality_evidence_required"] is True
    assert promotion_gate["quality_evidence_valid"] is False


def test_autonomy_status_reports_quality_evidence_load_error(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))

    def fail():
        raise ValueError("bad bundle")

    monkeypatch.setattr("runtime.quality.evidence_bundle.load_latest_quality_evidence_bundle", fail)
    status = summarize_autonomy_status(limit=10)
    assert status["quality_evidence_bundle_error"] == "ValueError"
    assert status["quality_gate"]["status"] == "BLOCK"


def test_autonomy_recommendations_use_quality_gate_missing_evidence_actions():
    from agent.apex_runtimeos_autonomy import build_autonomy_recommendations

    recommendations = build_autonomy_recommendations({
        "quality_gate": {
            "status": "BLOCK",
            "missing_blocking_evidence": ["test_report", "audit_log"],
            "missing_warning_evidence": ["documentation"],
        }
    })
    item = recommendations["items"][0]
    assert item["code"] == "cmmi_quality_evidence_incomplete"
    assert item["severity"] == "block"
    assert item["actions"] == [
        "attach_test_report",
        "attach_audit_log",
        "review_documentation",
        "keep_quality_gate_read_only",
    ]


def test_autonomy_status_includes_read_only_skill_registry_policy(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    status = summarize_autonomy_status(limit=10)
    policy = status["skill_registry_policy"]
    assert policy["schema"] == "ApexRuntimeOSSkillRegistryPolicyReport/v1"
    assert policy["status"] == "PASS"
    assert policy["policy"] == "deny_by_default"
    assert policy["reference_only_high_risk_count"] >= 4
    assert "desktop-super-evolution-source" in policy["reference_only_high_risk_ids"]
    assert policy["side_effects"] == "read_only_report"


def test_apex_runtimeos_cli_autonomy_shows_quality_missing_evidence(tmp_path, monkeypatch):
    from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli

    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setattr("runtime.quality.evidence_bundle.load_latest_quality_evidence_bundle", lambda: None)
    output = run_apex_runtimeos_cli(["autonomy"])
    assert "字段：CMMI缺失阻断证据" in output
    assert "test_report" in output
    assert "字段：CMMI证据包已读取" in output
    assert "字段：CMMI证据包有效" in output


def test_apex_runtimeos_cli_autonomy_shows_quality_evidence_bundle_status(tmp_path, monkeypatch):
    from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli

    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    bundle = {
        "schema": "ApexRuntimeOSQualityEvidenceBundle/v1",
        "source": "cli-unit-test",
        "evidence": {
            "test_report": {"present": True, "summary": "tests passed"},
            "audit_log": {"present": True, "summary": "audit present"},
            "documentation": {"present": True, "summary": "docs present"},
        },
    }
    monkeypatch.setattr("runtime.quality.evidence_bundle.load_latest_quality_evidence_bundle", lambda: bundle)
    output = run_apex_runtimeos_cli(["autonomy"])
    assert "字段：CMMI证据包已读取" in output
    assert "字段：CMMI证据包有效" in output
    assert "字段：CMMI证据包来源" in output
    assert "cli-unit-test" in output
    assert "test_report" in output


def test_apex_runtimeos_cli_autonomy_shows_skill_registry_policy(tmp_path, monkeypatch):
    from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli

    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    output = run_apex_runtimeos_cli(["autonomy"])
    assert "字段：技能注册表策略状态" in output
    assert "deny_by_default" in output
    assert "desktop-super-evolution-source" in output


def test_autonomy_status_includes_co_scientist_report(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    report = {
        "schema": "ApexCoScientistDebateSummary/v1",
        "valid": True,
        "status": "PASS",
        "topic": "unit co scientist",
        "reviewer_count": 2,
        "ok_count": 2,
        "decision": "execute",
        "promotion_required": True,
        "applied_to_memory_or_skill": False,
        "validation_errors": [],
        "side_effects": "read_only_report",
    }
    monkeypatch.setattr("agent.apex_co_scientist.load_latest_debate_report", lambda: report)
    status = summarize_autonomy_status(limit=10)
    assert status["co_scientist_report"]["status"] == "PASS"
    assert status["co_scientist_report"]["reviewer_count"] == 2


def test_apex_runtimeos_cli_autonomy_shows_co_scientist_report(tmp_path, monkeypatch):
    from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli

    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    report = {
        "schema": "ApexCoScientistDebateSummary/v1",
        "valid": True,
        "status": "PASS",
        "topic": "cli co scientist",
        "reviewer_count": 2,
        "ok_count": 2,
        "decision": "execute",
        "promotion_required": True,
        "applied_to_memory_or_skill": False,
        "validation_errors": [],
        "side_effects": "read_only_report",
    }
    monkeypatch.setattr("agent.apex_co_scientist.load_latest_debate_report", lambda: report)
    output = run_apex_runtimeos_cli(["autonomy"])
    assert "字段：Co_Scientist状态" in output
    assert "字段：Co_Scientist审查员数" in output
    assert "cli co scientist" in output


def test_autonomy_status_includes_co_scientist_gene_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setattr("agent.apex_co_scientist.load_latest_debate_report", lambda: None)
    candidate = {
        "schema": "ApexCoScientistGeneCandidateSummary/v1",
        "status": "READY",
        "eligible": True,
        "candidate_id": "abc123",
        "topic": "unit gene",
        "decision": "execute",
        "reviewer_count": 2,
        "evidence_level": "multi_model_debate",
        "promotion_required": True,
        "gene_library_written": False,
        "side_effects": "read_only_candidate",
    }
    monkeypatch.setattr("agent.apex_co_scientist.load_latest_gene_candidate", lambda: candidate)
    status = summarize_autonomy_status(limit=10)
    assert status["co_scientist_gene_candidate"]["status"] == "READY"
    assert status["co_scientist_gene_candidate"]["gene_library_written"] is False


def test_apex_runtimeos_cli_autonomy_shows_co_scientist_gene_candidate(tmp_path, monkeypatch):
    from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli

    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    monkeypatch.setattr("agent.apex_co_scientist.load_latest_debate_report", lambda: None)
    candidate = {
        "schema": "ApexCoScientistGeneCandidateSummary/v1",
        "status": "READY",
        "eligible": True,
        "candidate_id": "abc123",
        "topic": "cli gene",
        "decision": "execute",
        "reviewer_count": 2,
        "evidence_level": "multi_model_debate",
        "promotion_required": True,
        "gene_library_written": False,
        "side_effects": "read_only_candidate",
    }
    monkeypatch.setattr("agent.apex_co_scientist.load_latest_gene_candidate", lambda: candidate)
    output = run_apex_runtimeos_cli(["autonomy"])
    assert "字段：Co_Scientist基因候选状态" in output
    assert "字段：Co_Scientist基因候选已写库" in output
    assert "multi_model_debate" in output


def test_autonomy_status_includes_era_report(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    era = {
        "schema": "ApexERAPathSearchSummary/v1",
        "valid": True,
        "status": "PASS",
        "task": "unit era",
        "path_count": 3,
        "selected_path_id": "safe",
        "selected_score": 0.72,
        "executed": False,
        "promotion_required": True,
        "side_effects": "read_only_report",
    }
    monkeypatch.setattr("agent.apex_era.load_latest_era_report", lambda: era)
    status = summarize_autonomy_status(limit=10)
    assert status["era_report"]["status"] == "PASS"
    assert status["era_report"]["selected_path_id"] == "safe"
    assert status["era_report"]["executed"] is False


def test_apex_runtimeos_cli_autonomy_shows_era_report(tmp_path, monkeypatch):
    from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli

    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    era = {
        "schema": "ApexERAPathSearchSummary/v1",
        "valid": True,
        "status": "PASS",
        "task": "cli era",
        "path_count": 3,
        "selected_path_id": "safe",
        "selected_score": 0.72,
        "executed": False,
        "promotion_required": True,
        "side_effects": "read_only_report",
    }
    monkeypatch.setattr("agent.apex_era.load_latest_era_report", lambda: era)
    output = run_apex_runtimeos_cli(["autonomy"])
    assert "字段：ERA路径搜索状态" in output
    assert "字段：ERA选中路径" in output
    assert "safe" in output


def test_autonomy_status_includes_apex_v3_unified_score(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    status = summarize_autonomy_status(limit=10)
    report = status["apex_v3_unified_score"]
    assert report["schema"] == "ApexV3UnifiedScoreReport/v1"
    assert report["agi_completion_claim"] is False
    assert isinstance(report["allows_autonomous_promotion"], bool)
    assert report["autonomous_promotion_policy"]["autopromote_enabled"] is True
    assert report["side_effects"] == "read_only_report"


def test_apex_runtimeos_cli_autonomy_shows_apex_v3_unified_score(tmp_path, monkeypatch):
    from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli

    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    output = run_apex_runtimeos_cli(["autonomy"])
    assert "字段：APEX v3统一评分状态" in output
    assert "字段：APEX v3统一评分" in output
    assert "字段：APEX v3允许自动晋升" in output


def test_autonomy_status_includes_gpo_report(tmp_path, monkeypatch):
    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    status = summarize_autonomy_status(limit=10)
    gpo = status["gpo_report"]
    assert gpo["schema"] == "ApexGenePrincipleOntologyReport/v2"
    assert gpo["source_repo"] == "omega-agi-supremacy"
    assert gpo["runtime_allowed"] is False
    assert gpo["side_effects"] == "read_only_report"


def test_apex_runtimeos_cli_autonomy_shows_gpo_report(tmp_path, monkeypatch):
    from hermes_cli.apex_runtimeos import run_apex_runtimeos_cli

    monkeypatch.setenv("APEX_RUNTIMEOS_AUTOWRITE_DIR", str(tmp_path / "auto"))
    output = run_apex_runtimeos_cli(["autonomy"])
    assert "字段：GPO状态" in output
    assert "字段：GPO原则数" in output
    assert "字段：GPO知识源" in output
    assert "字段：Omega运行接入允许" in output

