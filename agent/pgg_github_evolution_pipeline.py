"""PGG/Hermes GitHub self-evolution pipeline.

Safety boundary:
- Read-only discovery/status by default.
- No automatic merge.
- PR creation is disabled unless the caller passes --create-pr and the working
  tree/branch gates pass; default run only produces a review package.
- No scheduler/security/provider/production route mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_HOME = Path.home()
DEFAULT_REPO = DEFAULT_HOME / ".hermes" / "hermes-agent"
DEFAULT_CONFIG = DEFAULT_HOME / ".hermes" / "config" / "evolution-pipeline.yaml"
DEFAULT_LATEST = DEFAULT_HOME / ".hermes" / "data" / "pgg_github_evolution_pipeline_latest.json"
DEFAULT_LEDGER = DEFAULT_HOME / ".hermes" / "data" / "pgg_github_evolution_pipeline_ledger.jsonl"
DEFAULT_REVIEW_DIR = DEFAULT_HOME / ".hermes" / "workspace" / "pgg-archon-governance" / "github-evolution-pipeline"
DEFAULT_STATUS_SCRIPT = DEFAULT_HOME / ".hermes" / "scripts" / "pgg_github_self_evolution_status.py"
DEFAULT_BOT_BRANCH_PREFIX = "bot/evolver"


@dataclass(frozen=True)
class CommandResult:
    cmd: list[str]
    exit: int
    stdout: str
    stderr: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _run(cmd: Sequence[str], *, cwd: Path | None = None, timeout: int = 30) -> CommandResult:
    try:
        proc = subprocess.run(list(cmd), cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout)
        return CommandResult(list(cmd), proc.returncode, proc.stdout[-4000:], proc.stderr[-4000:])
    except Exception as exc:  # noqa: BLE001
        return CommandResult(list(cmd), 999, "", repr(exc))


def _github_source_readable(gh: CommandResult) -> bool:
    """Return whether the configured GitHub source is readable.

    Prefer ``gh repo view`` when GitHub CLI auth is healthy, but keep the
    pipeline useful when ``gh`` auth is stale and the local source checkout or
    git credential helper can still perform read-only remote discovery.
    """
    if gh.exit == 0:
        return True
    source_repo = DEFAULT_HOME / ".hermes" / "workspace" / "github" / "z-dashen"
    if not source_repo.exists():
        return False
    remote = _run(["git", "ls-remote", "origin", "HEAD", "refs/heads/main"], cwd=source_repo, timeout=20)
    return remote.exit == 0 and bool(remote.stdout.strip())


def _github_auth_status(gh: CommandResult) -> str:
    """Classify GitHub CLI auth without treating auth as required for read-only status.

    The pipeline can still be PASS when local/read-only source discovery works,
    but exposing this WATCH prevents a bounded PASS from being mistaken for
    authenticated GitHub write/PR readiness.
    """
    if gh.exit == 0:
        return "PASS_GH_CLI_AUTH_READABLE"
    stderr = (gh.stderr or "").lower()
    if "requires authentication" in stderr or "gh auth login" in stderr or "http 401" in stderr:
        return "WATCH_GH_CLI_AUTH_REQUIRED"
    return "WATCH_GH_CLI_UNREADABLE"


def _read_yaml_like_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        # Best-effort fallback: status must not fail just because YAML is missing.
        return {"_parse_error": True, "path": str(path)}


def default_config_payload() -> str:
    repo_root = str(Path.home() / ".hermes" / "hermes-agent")
    return f"""# PGG/Hermes GitHub self-evolution pipeline (bounded, no auto-merge)
schema: PGGGithubEvolutionPipelineConfig/v1
version: 0.1.0
repo_root: {repo_root}
source_repos:
  - appleoppa/z-dashen
bot_branch_prefix: bot/evolver
schedule:
  runtime: launchd
  label: ai.hermes.pgg-github-cli-mcp-self-evolution
  interval_seconds: 1800
safety:
  auto_merge: false
  auto_push: false
  auto_pr: false
  require_human_or_llm_review_for_pr: true
  no_external_code_execution: true
  no_scheduler_security_mutation: true
  no_provider_config_mutation: true
stages:
  discover:
    enabled: true
    mode: read_only_github_metadata
  score:
    enabled: true
    gates:
      - mcp_cli_github_status
      - commit_discipline
      - unified_formula_score
  fetch:
    enabled: false
    reason: requires explicit per-source approval before cloning/executing external content
  upgrade:
    enabled: false
    reason: generate proposal first; no automatic core mutation
  pr:
    enabled: false
    reason: default HOLD; use --create-pr with explicit scope to open a bot branch PR
"""


def ensure_default_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(default_config_payload(), encoding="utf-8")
    return {"path": str(path), "sha256": _sha_file(path)}


def _load_self_status() -> dict[str, Any]:
    if DEFAULT_STATUS_SCRIPT.exists():
        r = _run([str(DEFAULT_HOME / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"), str(DEFAULT_STATUS_SCRIPT), "--quiet-pass"], timeout=90)
    latest = DEFAULT_HOME / ".hermes" / "data" / "pgg_github_cli_mcp_self_evolution_latest.json"
    if latest.exists():
        try:
            data = json.loads(latest.read_text(encoding="utf-8"))
            data["_latest_path"] = str(latest)
            return data
        except Exception as exc:  # noqa: BLE001
            return {"status": "ERROR_SELF_STATUS_PARSE", "error": repr(exc), "_latest_path": str(latest)}
    return {"status": "ERROR_SELF_STATUS_MISSING", "_latest_path": str(latest)}


def _git_state(repo_root: Path = DEFAULT_REPO) -> dict[str, Any]:
    return {
        "repo_root": str(repo_root),
        "head": _run(["git", "rev-parse", "HEAD"], cwd=repo_root).stdout.strip(),
        "branch": _run(["git", "branch", "--show-current"], cwd=repo_root).stdout.strip(),
        "status_short": _run(["git", "status", "--short"], cwd=repo_root).stdout,
        "remote": _run(["git", "remote", "-v"], cwd=repo_root).stdout,
    }


def build_status(*, repo_root: Path = DEFAULT_REPO) -> dict[str, Any]:
    ensure = ensure_default_config()
    cfg = _read_yaml_like_config(DEFAULT_CONFIG)
    self_status = _load_self_status()
    launchd = _run(["bash", "-lc", "launchctl print gui/$(id -u)/ai.hermes.pgg-github-cli-mcp-self-evolution 2>&1 | grep -E 'state =|runs =|last exit code|run interval|program =' | head -30"], timeout=20)
    gh = _run(["gh", "repo", "view", "appleoppa/z-dashen", "--json", "nameWithOwner,visibility,defaultBranchRef,url"], timeout=30)
    git_state = _git_state(repo_root)
    safety = (cfg.get("safety") or {}) if isinstance(cfg.get("safety"), dict) else {}
    stages = (cfg.get("stages") or {}) if isinstance(cfg.get("stages"), dict) else {}
    pr_stage = (stages.get("pr") or {}) if isinstance(stages.get("pr"), dict) else {}
    self_checks = self_status.get("checks") if isinstance(self_status.get("checks"), dict) else {}
    self_non_skillflow_ok = all(bool(self_checks.get(k)) for k in [
        "hermes_cli_available",
        "mcp_hermes_studio_enabled",
        "commit_discipline_hooks_installed",
        "unified_formula_latest_present",
    ])
    scoped_bot_write_enabled = (
        bool(safety.get("auto_push", False))
        and bool(safety.get("auto_pr", False))
        and not bool(safety.get("auto_merge", False))
        and str(safety.get("push_target", "")).lower() == "scoped_bot_branch"
        and str(safety.get("bot_branch_prefix", "")).startswith("bot/")
        and bool(safety.get("require_human_or_llm_review_for_pr", False))
        and bool(pr_stage.get("enabled", False))
    )
    checks = {
        "config_present": Path(ensure["path"]).exists(),
        "self_status_non_skillflow_core_pass": self_non_skillflow_ok,
        "launchd_runner_exit0": "last exit code = 0" in launchd.stdout,
        "github_source_readable": _github_source_readable(gh),
        "auto_merge_disabled": not bool(safety.get("auto_merge", False)),
        "direct_default_push_disabled": str(safety.get("push_target", "")).lower() != "default_branch",
        "scoped_bot_branch_pr_enabled": scoped_bot_write_enabled,
    }
    blockers = [name for name, ok in checks.items() if not ok]
    return {
        "schema": "PGGGithubEvolutionPipelineStatus/v1",
        "generated_at": _now(),
        "status": "PASS_GITHUB_EVOLUTION_PIPELINE_BOUNDED" if not blockers else "WATCH_GITHUB_EVOLUTION_PIPELINE",
        "checks": checks,
        "blockers": blockers,
        "config": ensure,
        "launchd_probe": launchd.to_json_dict(),
        "github_probe": gh.to_json_dict(),
        "github_auth_status": _github_auth_status(gh),
        "self_status": {"status": self_status.get("status"), "checks": self_status.get("checks"), "blockers": self_status.get("blockers"), "latest": self_status.get("_latest_path")},
        "git": git_state,
        "write_mode": "scoped_bot_branch_pr_enabled" if checks.get("scoped_bot_branch_pr_enabled") else "read_only_or_blocked",
        "boundary": "Bounded pipeline status only; scoped bot branch + PR may be enabled when gates pass; no auto-merge, no default-branch direct push, no scheduler/security/provider/production route mutation.",
    }


def discover(*, repo: str = "appleoppa/z-dashen", limit: int = 5) -> dict[str, Any]:
    view = _run(["gh", "repo", "view", repo, "--json", "nameWithOwner,visibility,defaultBranchRef,url,description,licenseInfo"], timeout=30)
    commits = _run(["gh", "api", f"repos/{repo}/commits", "--paginate", "-q", f".[0:{limit}] | [.[] | {{sha:.sha, message:.commit.message, author:.commit.author.name, date:.commit.author.date}}]"], timeout=60)
    items: list[dict[str, Any]] = []
    try:
        commit_items = json.loads(commits.stdout) if commits.exit == 0 and commits.stdout.strip() else []
        if isinstance(commit_items, list):
            items = commit_items
    except Exception:
        items = []
    return {
        "schema": "PGGGithubEvolutionDiscoverResult/v1",
        "generated_at": _now(),
        "repo": repo,
        "view_exit": view.exit,
        "repo_view": view.stdout,
        "commits_exit": commits.exit,
        "commit_count": len(items),
        "commits": items,
        "boundary": "Read-only GitHub metadata discovery; no clone, no external code execution, no absorption.",
    }


def build_review_package(*, output_dir: Path = DEFAULT_REVIEW_DIR, repo_root: Path = DEFAULT_REPO) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    status = build_status(repo_root=repo_root)
    disc = discover()
    package = {
        "schema": "PGGGithubEvolutionReviewPackage/v1",
        "generated_at": _now(),
        "status": "READY_FOR_BOT_BRANCH_PR_PROPOSAL" if status["status"] == "PASS_GITHUB_EVOLUTION_PIPELINE_BOUNDED" and disc.get("commits_exit") == 0 else "WATCH_REVIEW_PACKAGE",
        "pipeline_status": status,
        "discovery": disc,
        "proposed_next_steps": [
            "Create bot/evolver branch only after explicit patch scope is selected.",
            "Run tests and commit discipline gate before PR.",
            "Open PR for human/LLM review; keep auto-merge disabled.",
        ],
        "boundary": "Review package only; no branch, no commit, no push, no PR created by default.",
    }
    path = output_dir / "github_evolution_review_package.json"
    path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(path), "status": package["status"], "sha256": _sha_file(path), "blockers": status.get("blockers", [])}


def write_latest(payload: Mapping[str, Any]) -> None:
    DEFAULT_LATEST.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_LATEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    DEFAULT_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def cmd_status(args: argparse.Namespace) -> int:
    result = build_status(repo_root=Path(args.repo_root).expanduser())
    write_latest(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result.get("blockers") else 1


def cmd_discover(args: argparse.Namespace) -> int:
    result = discover(repo=args.repo, limit=args.limit)
    write_latest(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("view_exit") == 0 and result.get("commits_exit") == 0 else 1


def cmd_propose(args: argparse.Namespace) -> int:
    result = build_review_package(output_dir=Path(args.output_dir).expanduser(), repo_root=Path(args.repo_root).expanduser())
    write_latest({"schema": "PGGGithubEvolutionPipelineLatest/v1", "generated_at": _now(), "command": "propose", "result": result})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"READY_FOR_BOT_BRANCH_PR_PROPOSAL", "WATCH_REVIEW_PACKAGE"} else 1


def cmd_run(args: argparse.Namespace) -> int:
    status = build_status(repo_root=Path(args.repo_root).expanduser())
    package = build_review_package(output_dir=Path(args.output_dir).expanduser(), repo_root=Path(args.repo_root).expanduser())
    result = {
        "schema": "PGGGithubEvolutionPipelineRun/v1",
        "generated_at": _now(),
        "mode": "dry_run" if args.dry_run else "bounded_review_only",
        "status": "PASS_EVOLVE_DRY_RUN" if status["status"] == "PASS_GITHUB_EVOLUTION_PIPELINE_BOUNDED" else "WATCH_EVOLVE_DRY_RUN",
        "pipeline_status": status["status"],
        "review_package": package,
        "create_pr_requested": bool(args.create_pr),
        "pr_status": "HOLD_PR_CREATION_NOT_EXECUTED_BY_DEFAULT",
        "boundary": "No auto merge. PR creation requires explicit --create-pr and scoped diff; current command only builds review package.",
    }
    if args.create_pr:
        result["pr_status"] = "BLOCKED_CREATE_PR_NO_SCOPED_PATCH_SELECTED"
        result.setdefault("blockers", []).append("no_scoped_patch_selected")
    write_latest(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"].startswith("PASS") and not args.create_pr else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PGG/Hermes bounded GitHub self-evolution pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    st = sub.add_parser("status", help="Show bounded pipeline status")
    st.add_argument("--repo-root", default=str(DEFAULT_REPO))
    st.set_defaults(func=cmd_status)
    disc = sub.add_parser("discover", help="Read-only GitHub source discovery")
    disc.add_argument("--repo", default="appleoppa/z-dashen")
    disc.add_argument("--limit", type=int, default=5)
    disc.set_defaults(func=cmd_discover)
    prop = sub.add_parser("propose", help="Build review package; no branch/PR")
    prop.add_argument("--repo-root", default=str(DEFAULT_REPO))
    prop.add_argument("--output-dir", default=str(DEFAULT_REVIEW_DIR))
    prop.set_defaults(func=cmd_propose)
    run = sub.add_parser("run", help="Run bounded pipeline dry-run/review package")
    run.add_argument("--repo-root", default=str(DEFAULT_REPO))
    run.add_argument("--output-dir", default=str(DEFAULT_REVIEW_DIR))
    run.add_argument("--dry-run", action="store_true", default=True)
    run.add_argument("--create-pr", action="store_true", help="Request PR creation; still blocked unless scoped patch exists")
    run.set_defaults(func=cmd_run)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    # Cron/operator ergonomics: the installed ``hermes-evolve`` wrapper used by
    # status dashboards is easy to call without a subcommand. Treat a bare
    # invocation as the read-only ``status`` surface instead of failing argparse.
    # Explicit argv=[] in tests/embedders keeps normal argparse validation.
    parsed_argv = ["status"] if argv is None and len(sys.argv) == 1 else (list(argv) if argv is not None else None)
    args = parser.parse_args(parsed_argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
