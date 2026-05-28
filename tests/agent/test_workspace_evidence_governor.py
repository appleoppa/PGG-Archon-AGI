from agent.workspace_evidence_governor import classify_workspace_artifacts


def test_classify_workspace_artifacts_buckets_known_workspace_items(tmp_path):
    repo = tmp_path
    (repo / "workspace").mkdir()
    (repo / "workspace" / "GITHUB_REPO_CORE_PY_INDEX.json").write_text("{}", encoding="utf-8")
    report = classify_workspace_artifacts(["?? workspace/GITHUB_REPO_CORE_PY_INDEX.json"], repo_root=repo)
    assert report["artifact_count"] == 1
    assert report["bucket_counts"] == {"github_audit_inventory": 1}
    artifact = report["artifacts"][0]
    assert artifact["tracked_action"] == "keep_unstaged_review"
    assert artifact["content_hash"]
    assert report["agi_completion_claim"] is False


def test_classify_workspace_artifacts_marks_unknown_for_manual_review(tmp_path):
    repo = tmp_path
    report = classify_workspace_artifacts(["?? workspace/random.bin", "?? agent/new_module.py"], repo_root=repo)
    assert report["bucket_counts"] == {"non_workspace_untracked": 1, "workspace_unknown": 1}
    actions = {item["path"]: item["tracked_action"] for item in report["artifacts"]}
    assert actions["workspace/random.bin"] == "manual_review"
    assert actions["agent/new_module.py"] == "manual_review"


def test_classify_workspace_artifacts_is_read_only(tmp_path):
    repo = tmp_path
    item = repo / "workspace" / "flow_reward" / "flow_status.json"
    item.parent.mkdir(parents=True)
    item.write_text('{"status":"WATCH"}', encoding="utf-8")
    before = item.read_text(encoding="utf-8")
    report = classify_workspace_artifacts(["?? workspace/flow_reward/flow_status.json"], repo_root=repo)
    assert report["bucket_counts"] == {"flow_or_promotion_evidence": 1}
    assert item.read_text(encoding="utf-8") == before
    assert report["side_effects"] == "read_only_classification"
