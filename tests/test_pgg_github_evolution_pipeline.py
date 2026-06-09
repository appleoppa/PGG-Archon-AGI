from __future__ import annotations

import json
from pathlib import Path

from agent import pgg_github_evolution_pipeline as pipe


def test_ensure_default_config(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "evolution-pipeline.yaml"
    monkeypatch.setattr(pipe, "DEFAULT_CONFIG", cfg)
    result = pipe.ensure_default_config(cfg)
    assert cfg.exists()
    assert result["sha256"]
    assert "auto_merge: false" in cfg.read_text()


def test_status_blocks_when_self_status_missing(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "evolution-pipeline.yaml"
    monkeypatch.setattr(pipe, "DEFAULT_CONFIG", cfg)
    monkeypatch.setattr(pipe, "_load_self_status", lambda: {"status": "ERROR_SELF_STATUS_MISSING", "checks": {}, "blockers": ["missing"]})
    monkeypatch.setattr(pipe, "_git_state", lambda repo_root: {"repo_root": str(repo_root), "head": "h", "branch": "b", "status_short": "", "remote": ""})
    def fake_run(cmd, cwd=None, timeout=30):
        text = "last exit code = 0" if "launchctl" in " ".join(cmd) else '{"nameWithOwner":"appleoppa/z-dashen"}'
        return pipe.CommandResult(list(cmd), 0, text, "")
    monkeypatch.setattr(pipe, "_run", fake_run)
    result = pipe.build_status(repo_root=tmp_path)
    assert result["status"] == "WATCH_GITHUB_EVOLUTION_PIPELINE"
    assert "self_status_non_skillflow_core_pass" in result["blockers"]


def test_github_source_readable_falls_back_to_local_git_remote(tmp_path: Path, monkeypatch) -> None:
    source_repo = tmp_path / ".hermes" / "workspace" / "github" / "z-dashen"
    source_repo.mkdir(parents=True)
    monkeypatch.setattr(pipe, "DEFAULT_HOME", tmp_path)

    def fake_run(cmd, cwd=None, timeout=30):
        assert cmd[:2] == ["git", "ls-remote"]
        assert cwd == source_repo
        return pipe.CommandResult(list(cmd), 0, "abc123\tHEAD\nabc123\trefs/heads/main\n", "")

    monkeypatch.setattr(pipe, "_run", fake_run)
    stale_gh = pipe.CommandResult(["gh", "repo", "view"], 1, "", "HTTP 401")
    assert pipe._github_source_readable(stale_gh) is True


def test_github_auth_status_exposes_watch_without_secret() -> None:
    stale_gh = pipe.CommandResult(["gh", "repo", "view"], 1, "", "HTTP 401: Requires authentication")
    assert pipe._github_auth_status(stale_gh) == "WATCH_GH_CLI_AUTH_REQUIRED"
    assert pipe._github_auth_status(pipe.CommandResult(["gh", "repo", "view"], 0, "{}", "")) == "PASS_GH_CLI_AUTH_READABLE"


def test_status_reports_github_auth_watch_separately(tmp_path: Path, monkeypatch) -> None:
    cfg = tmp_path / "evolution-pipeline.yaml"
    monkeypatch.setattr(pipe, "DEFAULT_CONFIG", cfg)
    monkeypatch.setattr(pipe, "_load_self_status", lambda: {"status": "PASS", "checks": {
        "hermes_cli_available": True,
        "mcp_hermes_studio_enabled": True,
        "commit_discipline_hooks_installed": True,
        "unified_formula_latest_present": True,
    }, "blockers": []})
    monkeypatch.setattr(pipe, "_git_state", lambda repo_root: {"repo_root": str(repo_root), "head": "h", "branch": "b", "status_short": "", "remote": ""})

    def fake_run(cmd, cwd=None, timeout=30):
        joined = " ".join(cmd)
        if "launchctl" in joined:
            return pipe.CommandResult(list(cmd), 0, "last exit code = 0", "")
        if cmd[:3] == ["gh", "repo", "view"]:
            return pipe.CommandResult(list(cmd), 1, "", "HTTP 401: Requires authentication")
        if cmd[:2] == ["git", "ls-remote"]:
            return pipe.CommandResult(list(cmd), 0, "abc123\tHEAD\n", "")
        return pipe.CommandResult(list(cmd), 0, "", "")

    source_repo = tmp_path / ".hermes" / "workspace" / "github" / "z-dashen"
    source_repo.mkdir(parents=True)
    monkeypatch.setattr(pipe, "DEFAULT_HOME", tmp_path)
    monkeypatch.setattr(pipe, "_run", fake_run)
    result = pipe.build_status(repo_root=tmp_path)
    assert result["github_auth_status"] == "WATCH_GH_CLI_AUTH_REQUIRED"
    assert result["checks"]["github_source_readable"] is True


def test_review_package_writes_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(pipe, "build_status", lambda repo_root: {"status": "PASS_GITHUB_EVOLUTION_PIPELINE_BOUNDED", "blockers": []})
    monkeypatch.setattr(pipe, "discover", lambda: {"commits_exit": 0, "commit_count": 1})
    result = pipe.build_review_package(output_dir=tmp_path, repo_root=tmp_path)
    assert result["status"] == "READY_FOR_BOT_BRANCH_PR_PROPOSAL"
    payload = json.loads(Path(result["path"]).read_text())
    assert payload["boundary"].startswith("Review package only")


def test_create_pr_request_is_blocked_without_scoped_patch(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(pipe, "build_status", lambda repo_root: {"status": "PASS_GITHUB_EVOLUTION_PIPELINE_BOUNDED", "blockers": []})
    monkeypatch.setattr(pipe, "build_review_package", lambda output_dir, repo_root: {"path": str(tmp_path / "p.json"), "status": "READY_FOR_BOT_BRANCH_PR_PROPOSAL"})
    monkeypatch.setattr(pipe, "write_latest", lambda payload: None)
    code = pipe.main(["run", "--repo-root", str(tmp_path), "--output-dir", str(tmp_path), "--create-pr"])
    out = json.loads(capsys.readouterr().out)
    assert code == 1
    assert out["pr_status"] == "BLOCKED_CREATE_PR_NO_SCOPED_PATCH_SELECTED"


def test_bare_main_defaults_to_status(monkeypatch, capsys) -> None:
    monkeypatch.setattr(pipe.sys, "argv", ["hermes-evolve"])
    monkeypatch.setattr(pipe, "cmd_status", lambda args: print("STATUS_CALLED") or 0)
    assert pipe.main() == 0
    assert "STATUS_CALLED" in capsys.readouterr().out


def test_flag_status_alias_defaults_to_status(monkeypatch, capsys) -> None:
    monkeypatch.setattr(pipe.sys, "argv", ["hermes-evolve", "--status"])
    monkeypatch.setattr(pipe, "cmd_status", lambda args: print("STATUS_ALIAS_CALLED") or 0)
    assert pipe.main() == 0
    assert "STATUS_ALIAS_CALLED" in capsys.readouterr().out


def test_explicit_status_alias_defaults_to_status(monkeypatch, capsys) -> None:
    monkeypatch.setattr(pipe, "cmd_status", lambda args: print("EXPLICIT_STATUS_ALIAS_CALLED") or 0)
    assert pipe.main(["--status"]) == 0
    assert "EXPLICIT_STATUS_ALIAS_CALLED" in capsys.readouterr().out


def test_explicit_empty_argv_still_requires_subcommand() -> None:
    try:
        pipe.main([])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - defensive: argparse should always exit here.
        raise AssertionError("empty argv must keep argparse validation")
