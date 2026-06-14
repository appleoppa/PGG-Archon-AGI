#!/usr/bin/env python3
"""PGG Self-Feed Daemon.

Local-only six-hour self-feed loop:
Collect -> Research -> Activate -> Execute -> Reflect -> Upgrade -> Diagnose -> Iterate.

Boundary: scans ~/.hermes/workspace only; no external network; no LLM calls; no destructive writes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home()
HERMES_HOME = HOME / ".hermes"
WORKSPACE = HERMES_HOME / "workspace"
STATE_PATH = HERMES_HOME / "state" / "pgg_self_feed_daemon_state.json"
INTERVAL_SECONDS = 6 * 60 * 60


@dataclass
class FeedRun:
    schema: str = "PGGSelfFeedRun/v1"
    generated_at: str = ""
    due_before_run: bool = False
    phases: dict[str, Any] = field(default_factory=dict)
    boundary: str = "local-only/workspace-scan-only/no-network/no-external-llm/no-destructive-write"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SelfFeedDaemon:
    """Six-hour local self-feed loop controller."""

    PHASES = ["Collect", "Research", "Activate", "Execute", "Reflect", "Upgrade", "Diagnose", "Iterate"]

    def __init__(self, workspace: Path | str = WORKSPACE, state_path: Path | str = STATE_PATH, interval_seconds: int = INTERVAL_SECONDS) -> None:
        self.workspace = Path(workspace)
        self.state_path = Path(state_path)
        self.interval_seconds = int(interval_seconds)

    @staticmethod
    def _now_dt() -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def _now(cls) -> str:
        return cls._now_dt().isoformat()

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"schema": "PGGSelfFeedDaemonState/v1", "last_run_at": None, "runs": 0, "last_result": None}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            return {"schema": "PGGSelfFeedDaemonState/v1", "state_error": f"{type(exc).__name__}: {exc}", "last_run_at": None, "runs": 0}

    def _save_state(self, data: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def due_info(self) -> dict[str, Any]:
        state = self._load_state()
        last = state.get("last_run_at")
        now = self._now_dt()
        elapsed = None
        due = True
        next_run_at = now
        if last:
            try:
                last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                elapsed = max(0, int((now - last_dt).total_seconds()))
                due = elapsed >= self.interval_seconds
                next_ts = last_dt.timestamp() + self.interval_seconds
                next_run_at = datetime.fromtimestamp(next_ts, tz=timezone.utc)
            except Exception:
                due = True
        return {
            "last_run_at": last,
            "now": now.isoformat(),
            "interval_seconds": self.interval_seconds,
            "elapsed_seconds": elapsed,
            "due": due,
            "next_run_at": next_run_at.isoformat() if not due else now.isoformat(),
            "state_path": str(self.state_path),
            "runs": state.get("runs", 0),
        }

    @staticmethod
    def _safe_text_sample(path: Path, max_bytes: int = 4096) -> str:
        try:
            data = path.read_bytes()[:max_bytes]
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def collect(self, max_files: int = 1200) -> dict[str, Any]:
        """Collect local signals from ~/.hermes/workspace only."""
        if not self.workspace.exists():
            return {"phase": "Collect", "status": "ERROR_WORKSPACE_MISSING", "workspace": str(self.workspace)}
        ext_counts: Counter[str] = Counter()
        dir_counts: Counter[str] = Counter()
        keyword_counts: Counter[str] = Counter()
        recent: list[dict[str, Any]] = []
        files_seen = 0
        total_bytes = 0
        keywords = ["TODO", "WATCH", "FAIL", "ERROR", "PASS", "gate", "门禁", "验证", "边界", "进化", "案件"]
        for root, dirs, files in os.walk(self.workspace):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".venv", "venv"}][:40]
            root_path = Path(root)
            top = root_path.relative_to(self.workspace).parts[0] if root_path != self.workspace and root_path.relative_to(self.workspace).parts else "."
            for name in files:
                path = root_path / name
                try:
                    st = path.stat()
                except OSError:
                    continue
                files_seen += 1
                total_bytes += int(st.st_size)
                ext_counts[path.suffix.lower() or "<none>"] += 1
                dir_counts[top] += 1
                if len(recent) < 80:
                    recent.append({"path": str(path.relative_to(self.workspace)), "mtime": st.st_mtime, "size": st.st_size})
                elif st.st_mtime > min(r["mtime"] for r in recent):
                    idx = min(range(len(recent)), key=lambda i: recent[i]["mtime"])
                    recent[idx] = {"path": str(path.relative_to(self.workspace)), "mtime": st.st_mtime, "size": st.st_size}
                if path.suffix.lower() in {".md", ".txt", ".json", ".yaml", ".yml", ".py"} and st.st_size <= 2_000_000:
                    sample = self._safe_text_sample(path)
                    for kw in keywords:
                        if kw.lower() in sample.lower():
                            keyword_counts[kw] += 1
                if files_seen >= max_files:
                    break
            if files_seen >= max_files:
                break
        recent.sort(key=lambda r: r["mtime"], reverse=True)
        for r in recent:
            r["mtime_iso"] = datetime.fromtimestamp(r.pop("mtime"), tz=timezone.utc).isoformat()
        return {
            "phase": "Collect",
            "status": "PASS_LOCAL_SCAN",
            "workspace": str(self.workspace),
            "files_seen": files_seen,
            "total_bytes_sampled": total_bytes,
            "top_extensions": ext_counts.most_common(20),
            "top_dirs": dir_counts.most_common(20),
            "keyword_hits": keyword_counts.most_common(),
            "recent_files": recent[:25],
            "truncated": files_seen >= max_files,
        }

    def research(self, collect: dict[str, Any]) -> dict[str, Any]:
        hits = dict(collect.get("keyword_hits", []))
        themes = []
        if hits.get("ERROR", 0) or hits.get("FAIL", 0):
            themes.append("failure/diagnostic backlog")
        if hits.get("WATCH", 0):
            themes.append("WATCH gate follow-up")
        if hits.get("门禁", 0) or hits.get("gate", 0):
            themes.append("gate coverage and evidence hardening")
        if hits.get("案件", 0):
            themes.append("case workflow trust evidence")
        if not themes:
            themes.append("workspace hygiene and recent-change review")
        return {"phase": "Research", "status": "PASS_LOCAL_THEMES", "themes": themes, "source": "local workspace keyword/topology scan"}

    def activate(self, research: dict[str, Any]) -> dict[str, Any]:
        actions = []
        for theme in research.get("themes", []):
            actions.append({"theme": theme, "action": "read-only triage; produce next local verification target", "risk": "LOW"})
        return {"phase": "Activate", "status": "PASS_SAFE_ACTIONS_SELECTED", "actions": actions}

    def execute(self, collect: dict[str, Any], activate: dict[str, Any]) -> dict[str, Any]:
        # Read-only execution: compute local health indicators only.
        files_seen = int(collect.get("files_seen", 0) or 0)
        top_ext = dict(collect.get("top_extensions", []))
        doc_ratio = round((top_ext.get(".md", 0) + top_ext.get(".txt", 0)) / max(files_seen, 1), 4)
        code_ratio = round((top_ext.get(".py", 0) + top_ext.get(".rs", 0) + top_ext.get(".ts", 0) + top_ext.get(".js", 0)) / max(files_seen, 1), 4)
        return {
            "phase": "Execute",
            "status": "PASS_READ_ONLY_EXECUTION",
            "indicators": {"doc_ratio": doc_ratio, "code_ratio": code_ratio, "action_count": len(activate.get("actions", []))},
        }

    def reflect(self, execute: dict[str, Any]) -> dict[str, Any]:
        indicators = execute.get("indicators", {})
        observations = []
        if indicators.get("doc_ratio", 0) > 0.35:
            observations.append("documentation-heavy workspace; prioritize index freshness and evidence links")
        if indicators.get("code_ratio", 0) > 0.15:
            observations.append("code-bearing workspace; prioritize import/test gate checks before claims")
        if not observations:
            observations.append("no dominant local modality; continue lightweight periodic scan")
        return {"phase": "Reflect", "status": "PASS_REFLECTION", "observations": observations}

    def upgrade(self, reflect: dict[str, Any]) -> dict[str, Any]:
        proposals = [
            {"proposal": obs, "mode": "recommendation_only", "auto_apply": False}
            for obs in reflect.get("observations", [])
        ]
        return {"phase": "Upgrade", "status": "PASS_RECOMMENDATIONS_ONLY", "proposals": proposals}

    def diagnose(self, collect: dict[str, Any], execute: dict[str, Any]) -> dict[str, Any]:
        issues = []
        if collect.get("status") != "PASS_LOCAL_SCAN":
            issues.append("workspace scan unavailable")
        if collect.get("truncated"):
            issues.append("scan truncated; increase max_files for deeper local exploration")
        if not issues:
            issues.append("no blocking daemon issue detected")
        return {"phase": "Diagnose", "status": "PASS" if len(issues) == 1 and issues[0].startswith("no blocking") else "WATCH", "issues": issues}

    def iterate(self, diagnose: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": "Iterate",
            "status": "SCHEDULE_NEXT_LOCAL_LOOP",
            "next_interval_seconds": self.interval_seconds,
            "due_rule": "run when now - last_run_at >= 6h",
            "diagnose_status": diagnose.get("status"),
        }

    def run_once(self, force: bool = False, max_files: int = 1200) -> dict[str, Any]:
        due = self.due_info()
        run = FeedRun(generated_at=self._now(), due_before_run=bool(due["due"]))
        if not force and not due["due"]:
            run.phases = {"status": "SKIPPED_NOT_DUE", "due_info": due}
            return run.to_dict()
        collect = self.collect(max_files=max_files)
        research = self.research(collect)
        activate = self.activate(research)
        execute = self.execute(collect, activate)
        reflect = self.reflect(execute)
        upgrade = self.upgrade(reflect)
        diagnose = self.diagnose(collect, execute)
        iterate = self.iterate(diagnose)
        run.phases = {
            "Collect": collect,
            "Research": research,
            "Activate": activate,
            "Execute": execute,
            "Reflect": reflect,
            "Upgrade": upgrade,
            "Diagnose": diagnose,
            "Iterate": iterate,
        }
        state = self._load_state()
        state.update({
            "schema": "PGGSelfFeedDaemonState/v1",
            "last_run_at": run.generated_at,
            "runs": int(state.get("runs", 0) or 0) + 1,
            "last_result": {"diagnose_status": diagnose.get("status"), "files_seen": collect.get("files_seen"), "themes": research.get("themes")},
        })
        self._save_state(state)
        return run.to_dict()

    def status(self) -> dict[str, Any]:
        return {
            "schema": "PGGSelfFeedDaemonStatus/v1",
            "generated_at": self._now(),
            "workspace": str(self.workspace),
            "state": self._load_state(),
            "due": self.due_info(),
            "phases": self.PHASES,
            "boundary": "pure local daemon; scans ~/.hermes/workspace only; no web crawl",
        }

    def schedule(self) -> dict[str, Any]:
        return {
            "schema": "PGGSelfFeedDaemonSchedule/v1",
            "generated_at": self._now(),
            "interval_seconds": self.interval_seconds,
            "interval_human": "6h",
            "command": str(HERMES_HOME / "bin" / "pgg-self-feed-daemon") + " run",
            "due": self.due_info(),
            "note": "schedule command reports the local schedule contract; it does not install launchd or access network",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pgg-self-feed-daemon", description="PGG local-only self-feed daemon")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="show due/status")
    p_run = sub.add_parser("run", help="run one local loop if due")
    p_run.add_argument("--force", action="store_true", help="run even when not due")
    p_run.add_argument("--max-files", type=int, default=1200)
    sub.add_parser("schedule", help="show six-hour schedule contract")
    args = parser.parse_args(argv)
    daemon = SelfFeedDaemon()
    if args.command in (None, "status"):
        print(json.dumps(daemon.status(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "run":
        data = daemon.run_once(force=args.force, max_files=args.max_files)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0 if data.get("phases", {}).get("status") != "SKIPPED_NOT_DUE" else 3
    if args.command == "schedule":
        print(json.dumps(daemon.schedule(), ensure_ascii=False, indent=2))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
