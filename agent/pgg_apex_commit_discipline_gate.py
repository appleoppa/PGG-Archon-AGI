"""Observe-first APEX commit discipline gate.

Boundary: read-only checker for commit-message entropy-reduction keywords,
SKILL.md frontmatter, and optional Python hash sidecars. It does not install or
modify git hooks, does not block commits, and does not claim runtime capability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

KEYWORD_RE = re.compile(r"收敛|纪律|协同|熵减|闭环|自省|自愈|吞噬|归一|规范")
DEFAULT_REQUIRED_SKILL_FIELDS = ("name", "description")


@dataclass
class CommitDisciplineResult:
    schema: str
    generated_at: str
    status: str
    score: float
    commit_message_check: dict[str, Any]
    skill_frontmatter_check: dict[str, Any]
    python_hash_check: dict[str, Any]
    checks: list[str]
    gaps: list[str]
    boundary: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_messages(repo: Path, limit: int = 20) -> list[str]:
    try:
        p = subprocess.run(
            ["git", "-C", str(repo), "log", f"--max-count={limit}", "--pretty=%s"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return [line.strip() for line in p.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def check_commit_messages(messages: Iterable[str]) -> dict[str, Any]:
    rows = []
    passed = 0
    total = 0
    for msg in messages:
        total += 1
        ok = bool(KEYWORD_RE.search(msg))
        passed += int(ok)
        rows.append({"message": msg, "entropy_keyword_present": ok})
    ratio = passed / total if total else 0.0
    return {
        "total": total,
        "passed": passed,
        "ratio": round(ratio, 4),
        "status": "PASS" if total and ratio >= 0.8 else ("WATCH" if total else "NO_MESSAGES"),
        "keywords": KEYWORD_RE.pattern,
        "rows": rows,
        "boundary": "Keyword presence is a commit-discipline signal only; it does not prove runtime APEX capability.",
    }


def _frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    data: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        data[k.strip()] = v.strip().strip('"')
    return data


def check_skill_frontmatter(root: Path, required_fields: tuple[str, ...] = DEFAULT_REQUIRED_SKILL_FIELDS, limit: int = 200) -> dict[str, Any]:
    skills = sorted(root.glob("**/SKILL.md"))[:limit] if root.exists() else []
    rows = []
    passed = 0
    for p in skills:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            text = ""
        fm = _frontmatter(text)
        missing = [] if fm else list(required_fields)
        if fm:
            missing = [f for f in required_fields if not fm.get(f)]
        ok = fm is not None and not missing
        passed += int(ok)
        rows.append({"path": str(p), "ok": ok, "missing": missing})
    total = len(rows)
    ratio = passed / total if total else 0.0
    return {
        "root": str(root),
        "total": total,
        "passed": passed,
        "ratio": round(ratio, 4),
        "status": "PASS" if total and ratio >= 0.95 else ("WATCH" if total else "NO_SKILLS"),
        "required_fields": list(required_fields),
        "sample_failures": [r for r in rows if not r["ok"]][:10],
        "boundary": "SKILL.md frontmatter validity is a procedural quality signal, not proof that a skill works.",
    }


def check_python_hash_sidecars(root: Path, limit: int = 200) -> dict[str, Any]:
    py_files = [p for p in sorted(root.glob("**/*.py")) if "__pycache__" not in str(p) and "/venv/" not in str(p)][:limit] if root.exists() else []
    rows = []
    sidecar_count = 0
    verified = 0
    for p in py_files:
        sidecar = p.with_suffix(p.suffix + ".sha256")
        has_sidecar = sidecar.exists()
        sidecar_count += int(has_sidecar)
        ok = False
        expected = ""
        actual = ""
        if has_sidecar:
            actual = _sha256(p)
            expected = sidecar.read_text(encoding="utf-8", errors="replace").strip().split()[0] if sidecar.read_text(encoding="utf-8", errors="replace").strip() else ""
            ok = bool(expected) and expected == actual
            verified += int(ok)
        rows.append({"path": str(p), "sidecar": str(sidecar), "sidecar_present": has_sidecar, "verified": ok, "expected": expected[:16], "actual": actual[:16]})
    total = len(rows)
    ratio = verified / total if total else 0.0
    coverage = sidecar_count / total if total else 0.0
    # Observe-first: sidecars are optional. PASS only if coverage exists and all sidecars are valid; otherwise WATCH.
    status = "PASS" if total and sidecar_count and verified == sidecar_count else ("WATCH" if total else "NO_PYTHON")
    return {
        "root": str(root),
        "total_python_checked": total,
        "sidecar_count": sidecar_count,
        "verified_sidecars": verified,
        "coverage": round(coverage, 4),
        "verified_ratio_all_python": round(ratio, 4),
        "status": status,
        "sample_missing_or_failed": [r for r in rows if not r["verified"]][:10],
        "boundary": "Hash sidecars are optional observe-first integrity hints; missing sidecars do not prove failure unless a policy requires them.",
    }


def evaluate(repo: str | Path, *, messages: list[str] | None = None, skill_root: str | Path | None = None, python_root: str | Path | None = None) -> dict[str, Any]:
    repo_path = Path(repo).expanduser()
    msg_rows = messages if messages is not None else _git_messages(repo_path)
    commit = check_commit_messages(msg_rows)
    skills = check_skill_frontmatter(Path(skill_root).expanduser() if skill_root else Path.home() / ".hermes/skills")
    pyhash = check_python_hash_sidecars(Path(python_root).expanduser() if python_root else repo_path / "agent")
    checks: list[str] = []
    gaps: list[str] = []
    if commit["status"] == "PASS": checks.append("commit_entropy_keywords_present")
    else: gaps.append("commit_entropy_keywords_insufficient")
    if skills["status"] == "PASS": checks.append("skill_frontmatter_valid")
    else: gaps.append("skill_frontmatter_watch")
    if pyhash["status"] == "PASS": checks.append("python_hash_sidecars_valid")
    else: gaps.append("python_hash_sidecars_observe_only")
    # Weight sidecars lightly because they are optional observe-first.
    score = round(commit["ratio"] * 35 + skills["ratio"] * 45 + min(pyhash["coverage"], 1.0) * 10 + (10 if pyhash["status"] == "PASS" else 0), 2)
    status = "PASS_COMMIT_DISCIPLINE_OBSERVE_GATE" if score >= 85 and len(gaps) <= 1 else ("WATCH_COMMIT_DISCIPLINE_OBSERVE_GATE" if score >= 50 else "BLOCKED_COMMIT_DISCIPLINE_INSUFFICIENT")
    return asdict(CommitDisciplineResult(
        schema="PGGApexCommitDisciplineGate/v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        score=score,
        commit_message_check=commit,
        skill_frontmatter_check=skills,
        python_hash_check=pyhash,
        checks=checks,
        gaps=gaps,
        boundary="Observe-first commit discipline gate; no hook install, no commit blocking, no runtime capability claim, not T5/full AGI.",
    ))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Observe-first APEX commit discipline gate")
    parser.add_argument("--repo", default=str(Path.home() / ".hermes/hermes-agent"))
    parser.add_argument("--skill-root")
    parser.add_argument("--python-root")
    parser.add_argument("--message", action="append", help="Commit message to evaluate; may be passed multiple times")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    result = evaluate(args.repo, messages=args.message, skill_root=args.skill_root, python_root=args.python_root)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).expanduser().write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["status"].startswith(("PASS", "WATCH")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
