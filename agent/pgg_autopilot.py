"""PGG Archon Autopilot — 自驾巡航模式.

Autonomous decision loop that probes system health, analyzes the evolution
engine state, detects saturation, and makes goal-switching recommendations.
Designed to be invoked by cron/launchd every 30 minutes.

Workflow:
  1. Probe system health (CPU/mem/disk/uptime)
  2. Analyze evolution engine state (self-evolution-loop latest.json)
  3. Make goal-switching decision via local scoring heuristics
  4. Generate summary report with decision trail

Boundary: local OS commands + local JSON reads only; no LLM/network calls.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENGINE_VERSION = "PGGArchonAutopilot/v1"
BOUNDARY = (
    "pgg_archon_autopilot; local host metrics + local JSON reads; "
    "pure heuristic scoring; no LLM/network; no AGI/T5/ASI claim"
)

# Default paths — mirror conventions in pgg_health_monitor and pgg_picoapex_saturation
_DEFAULT_SELF_EVOLVE_STATE = Path(
    "/Users/appleoppa/.hermes/data/self-evolution-loop/latest.json"
)
_DEFAULT_HEALTH_REPORT = Path(
    "/Users/appleoppa/.hermes/data/health-monitor/latest.json"
)
_DEFAULT_GENE_DB = Path(
    "/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3"
)

# Heuristic thresholds
CPU_WARN = 70.0
CPU_CRIT = 85.0
MEM_WARN = 75.0
MEM_CRIT = 90.0
DISK_WARN = 80.0
DISK_CRIT = 92.0
VERIFIED_TO_CANDIDATE_MIN = 0.5
AVG_FITNESS_DECLINE_WINDOW = 3  # cycles
SATURATION_THRESHOLD = 0.30

# Possible goal dimensions (mirrors pgg_picoapex_saturation DIMENSION_ORDER)
DIMENSIONS = ["creativity", "reasoning", "planning", "coding", "analysis"]

# Goal lifecycle states
GOAL_PRIORITIES = {
    "intake": "低证据级别基因积累过多 → 需要 intake 审查",
    "fusion": "验证基因比例健康 → 可以推进融合",
    "promote": "活跃基因精英率饱和 → 适合晋升 active",
    "maintenance": "系统资源紧张 → 优先维护/清理",
    "observe": "一切平稳 → 观察等待",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _run(cmd: list[str], timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)


# ─── AutopilotEngine ────────────────────────────────────────────────────────


class AutopilotEngine:
    """Autonomous decision loop for PGG Archon evolution autopilot.

    Reads system health + evolution engine state, applies heuristic scoring
    to recommend a goal switch, and produces a structured summary report.

    Public methods:
      - assess() -> dict        — run one full assessment cycle
      - summary() -> dict       — quick summary (alias for assess)
    """

    def __init__(
        self,
        self_evolve_state: str | Path = _DEFAULT_SELF_EVOLVE_STATE,
        health_report: str | Path = _DEFAULT_HEALTH_REPORT,
        gene_db: str | Path = _DEFAULT_GENE_DB,
        decision_history_size: int = 5,
    ) -> None:
        self.self_evolve_state = Path(self_evolve_state)
        self.health_report = Path(health_report)
        self.gene_db = Path(gene_db)
        self.decision_history_size = max(decision_history_size, 1)

    # ─── Public API ─────────────────────────────────────────────────────────

    def assess(self) -> dict[str, Any]:
        """Run one full autopilot assessment cycle.

        Returns a structured dict with schema ``PGGArchonAutopilot/v1``.
        """
        timestamp = _now()

        # Phase 1: probe system health
        system_health = self._probe_system_health()

        # Phase 2: analyze evolution engine state
        evolution_state = self._analyze_evolution_state()

        # Phase 3: score and decide
        saturation = self._detect_saturation(evolution_state)
        health_score, health_verdict = self._score_health(system_health)
        evolution_health = evolution_state.get("evolution_health", {})
        evolution_score, evolution_verdict = self._score_evolution_health(evolution_health)

        # Phase 4: goal decision
        goal_decision = self._decide_goal(
            saturation=saturation,
            health_verdict=health_verdict,
            evolution_verdict=evolution_verdict,
            evolution_state=evolution_state,
        )

        return {
            "schema": ENGINE_VERSION,
            "created_at": timestamp,
            "boundary": BOUNDARY,
            "cycle": {
                "system_health": system_health,
                "evolution_state": evolution_state,
                "saturation": saturation,
                "health_score": {
                    "value": round(health_score, 4),
                    "verdict": health_verdict,
                },
                "evolution_health_score": {
                    "value": round(evolution_score, 4),
                    "verdict": evolution_verdict,
                },
                "goal_decision": goal_decision,
            },
            "recommendation": goal_decision.get("recommendation"),
            "recommendation_zh": goal_decision.get("recommendation_zh"),
        }

    def summary(self) -> dict[str, Any]:
        """Quick alias for assess()."""
        return self.assess()

    # ─── Phase 1: System health probe ───────────────────────────────────────

    def _probe_system_health(self) -> dict[str, Any]:
        """Collect CPU/memory/disk/uptime via psutil (preferred) or fallback."""
        try:
            return self._probe_psutil()
        except ImportError:
            return self._probe_fallback()

    def _probe_psutil(self) -> dict[str, Any]:
        import psutil  # type: ignore

        cpu = float(psutil.cpu_percent(interval=0.3))
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        load_avg = tuple(
            round(float(x), 4) for x in (psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0))
        )
        boot_time = getattr(psutil, "boot_time", lambda: 0)()
        uptime_seconds = max(0, time.time() - boot_time)

        return {
            "collector": "psutil",
            "cpu_percent": round(cpu, 2),
            "memory_percent": round(float(mem.percent), 2),
            "disk_percent": round(float(disk.percent), 2),
            "load_avg": list(load_avg),
            "uptime_seconds": round(uptime_seconds),
            "uptime_human": self._format_uptime(uptime_seconds),
        }

    def _probe_fallback(self) -> dict[str, Any]:
        """Fallback using macOS system commands."""
        cpu_percent = 0.0
        memory_percent = 0.0
        disk_percent = 0.0
        load_avg: list[float] = [0.0, 0.0, 0.0]
        uptime_seconds = 0.0

        # CPU from ps
        try:
            ps = _run(["ps", "-A", "-o", "%cpu"], timeout=10)
            values = [_safe_float(x.strip()) for x in ps.stdout.splitlines()[1:] if x.strip()]
            total_cpu = sum(values)
            cpus_proc = _run(["sysctl", "-n", "hw.logicalcpu"], timeout=5)
            cpu_count = max(int(_safe_float(cpus_proc.stdout.strip(), 1)), 1)
            cpu_percent = max(0.0, min(100.0, total_cpu / cpu_count))
        except Exception:
            cpu_percent = 0.0

        # Load avg + uptime from sysctl/uptime
        try:
            boot_proc = _run(["sysctl", "-n", "kern.boottime"], timeout=5)
            # kern.boottime: { sec = 1234567890, ... }
            m = re.search(r"sec\s*=\s*(\d+)", boot_proc.stdout)
            if m:
                boot_epoch = float(m.group(1))
                uptime_seconds = max(0.0, time.time() - boot_epoch)
        except Exception:
            uptime_seconds = 0.0

        try:
            ut = _run(["uptime"], timeout=5).stdout
            m = re.findall(r"load averages?:\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", ut)
            if m:
                load_avg = [_safe_float(x) for x in m[-1]]
        except Exception:
            pass

        # Memory from vm_stat
        try:
            vm = _run(["vm_stat"], timeout=10).stdout
            page_size_m = re.search(r"page size of (\d+) bytes", vm)
            page_size = int(page_size_m.group(1)) if page_size_m else 4096
            pages: dict[str, int] = {}
            for line in vm.splitlines():
                if ":" not in line:
                    continue
                key, raw = line.split(":", 1)
                num = re.sub(r"[^0-9]", "", raw)
                if num:
                    pages[key.strip()] = int(num)
            free_pages = pages.get("Pages free", 0) + pages.get("Pages speculative", 0)
            used_pages = sum(v for k, v in pages.items() if k not in {"Pages free", "Pages speculative"})
            total_pages = free_pages + used_pages
            if total_pages > 0:
                memory_percent = used_pages / total_pages * 100.0
        except Exception:
            memory_percent = 0.0

        # Disk from shutil
        try:
            usage = shutil.disk_usage("/")
            disk_percent = (usage.used / usage.total * 100.0) if usage.total else 0.0
        except Exception:
            try:
                df = _run(["df", "-Pk", "/"], timeout=10).stdout.splitlines()
                if len(df) >= 2:
                    parts = df[1].split()
                    disk_percent = _safe_float(parts[4].rstrip("%")) if len(parts) >= 5 else 0.0
            except Exception:
                disk_percent = 0.0

        return {
            "collector": "subprocess_fallback",
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory_percent, 2),
            "disk_percent": round(disk_percent, 2),
            "load_avg": [round(float(x), 4) for x in load_avg],
            "uptime_seconds": round(uptime_seconds),
            "uptime_human": self._format_uptime(uptime_seconds),
        }

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        days, rem = divmod(int(seconds), 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return " ".join(parts)

    # ─── Phase 2: Evolution engine state ────────────────────────────────────

    def _analyze_evolution_state(self) -> dict[str, Any]:
        """Read and parse the self-evolution-loop latest.json state."""
        if not self.self_evolve_state.exists():
            return {
                "state_path": str(self.self_evolve_state),
                "exists": False,
                "error": "Self-evolution state not found",
            }

        try:
            raw = json.loads(self.self_evolve_state.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "state_path": str(self.self_evolve_state),
                "exists": True,
                "error": f"Parse error: {exc}",
            }

        stdout_str = str(raw.get("stdout", ""))

        result: dict[str, Any] = {
            "state_path": str(self.self_evolve_state),
            "exists": True,
            "last_run_label": raw.get("label"),
            "last_run_status": raw.get("status"),
            "last_run_completed": raw.get("completed_epoch"),
            "last_run_age_seconds": max(0, int(time.time()) - int(raw.get("completed_epoch", 0))),
            "raw_stdout_truncated": len(stdout_str) > 500,
        }

        # ── Parse stdout log lines for structured data ──
        lines = stdout_str.split("\n")

        picoapex_dim: str | None = None
        picoapex_ratio = 0.0
        picoapex_saturated = False
        health_level: str | None = None
        health_alerts = 0
        total_genes = 0
        gene_counts: dict[str, int] = {}
        promoted_count = 0
        fused_count = 0
        dream_synth = 0
        duration = 0.0

        for line in lines:
            sline = line.strip()

            # PicoAPEX: "→ 维度=reasoning, 精英率=0.3151, 饱和=True"
            m = re.search(r"维度=(\w+)", sline)
            if m:
                picoapex_dim = m.group(1)
            m = re.search(r"精英率=([\d.]+)", sline)
            if m:
                picoapex_ratio = _safe_float(m.group(1))
            m = re.search(r"饱和=(True|False|true|false)", sline)
            if m:
                picoapex_saturated = m.group(1).lower() == "true"

            # Health: "→ 健康级别=red, 告警=5条"
            m = re.search(r"健康级别=(\w+)", sline)
            if m:
                health_level = m.group(1)
            m = re.search(r"告警=(\d+)", sline)
            if m:
                health_alerts = int(m.group(1))

            # Total genes: "总基因数: 2293"
            m = re.search(r"总基因数:\s*(\d+)", sline)
            if m:
                total_genes = int(m.group(1))

            # Status distribution: "status 分布: {'active': 146, ...}"
            m = re.search(r"status\s+分布:\s*(\{.*\})", sline)
            if m:
                try:
                    gene_counts = json.loads(m.group(1).replace("'", '"'))
                except (json.JSONDecodeError, ValueError):
                    gene_counts = {}

            # Phase activity counts
            m = re.search(r"promoted:\s*(\d+)", sline)
            if m:
                promoted_count = int(m.group(1))
            m = re.search(r"fused:\s*(\d+)", sline)
            if m:
                fused_count = int(m.group(1))
            m = re.search(r"合成\s*(\d+)\s*个新基因", sline)
            if m:
                dream_synth = int(m.group(1))

            # Duration: "=== PGG 自主演化闭环完成 (0.46s) ==="
            m = re.search(r"完成\s*\(([\d.]+)s\)", sline)
            if m:
                duration = _safe_float(m.group(1))

        result["picoapex"] = {
            "current_dim": picoapex_dim or "unknown",
            "elite_ratio": round(picoapex_ratio, 6),
            "saturated": picoapex_saturated,
        }

        # Infer saturation state from stdout data
        result["saturation_detected"] = picoapex_saturated
        result["saturation_elite_ratio"] = round(picoapex_ratio, 6)
        result["saturation_dimension"] = picoapex_dim or "unknown"

        # Evolution health inferred from stdout
        result["evolution_health"] = {
            "health_level": health_level or "unknown",
            "health_alerts": health_alerts,
            "total_genes": total_genes,
        }

        # Gene status counts
        result["gene_counts"] = gene_counts

        # Phase activity
        result["phases"] = {
            "promote_count": promoted_count,
            "fusion_count": fused_count,
            "dream_synth_count": dream_synth,
            "health_status": health_level or "unknown",
        }

        # Duration
        result["duration_seconds"] = duration
        result["total_genes"] = total_genes

        return result

    # ─── Phase 3: Scoring heuristics ────────────────────────────────────────

    def _detect_saturation(self, evolution_state: dict[str, Any]) -> dict[str, Any]:
        """Detect current saturation from picoapex data in evolution state."""
        picoapex = evolution_state.get("picoapex", {}) or {}
        current_dim = picoapex.get("current_dim")
        elite_ratio = _safe_float(picoapex.get("elite_ratio"))
        saturated = bool(picoapex.get("saturated", False))

        # Also do a lightweight check: if elite_ratio > threshold, consider saturated
        heuristic_saturated = elite_ratio > SATURATION_THRESHOLD

        # Compute a reasonable next_dim by cycling through dimensions
        next_dim = current_dim or DIMENSIONS[0]
        try:
            idx = DIMENSIONS.index(next_dim)
            next_dim = DIMENSIONS[(idx + 1) % len(DIMENSIONS)]
        except ValueError:
            next_dim = DIMENSIONS[0]

        return {
            "current_dim": current_dim,
            "next_dim": next_dim,
            "elite_ratio": round(elite_ratio, 6),
            "saturated_state": saturated,
            "heuristic_saturated": heuristic_saturated,
            "saturation_detected": saturated or heuristic_saturated,
            "active_count": int(picoapex.get("active_count", 0)),
            "elite_count": int(picoapex.get("elite_count", 0)),
        }

    def _score_health(self, system_health: dict[str, Any]) -> tuple[float, str]:
        """Score system health 0.0 (critical) → 1.0 (perfect)."""
        cpu = _safe_float(system_health.get("cpu_percent"))
        mem = _safe_float(system_health.get("memory_percent"))
        disk = _safe_float(system_health.get("disk_percent"))

        penalties = 0.0
        alerts: list[str] = []

        if cpu >= CPU_CRIT:
            penalties += 0.35
            alerts.append(f"cpu_critical:{cpu}%")
        elif cpu >= CPU_WARN:
            penalties += 0.15
            alerts.append(f"cpu_warn:{cpu}%")

        if mem >= MEM_CRIT:
            penalties += 0.35
            alerts.append(f"mem_critical:{mem}%")
        elif mem >= MEM_WARN:
            penalties += 0.15
            alerts.append(f"mem_warn:{mem}%")

        if disk >= DISK_CRIT:
            penalties += 0.30
            alerts.append(f"disk_critical:{disk}%")
        elif disk >= DISK_WARN:
            penalties += 0.10
            alerts.append(f"disk_warn:{disk}%")

        score = max(0.0, 1.0 - penalties)

        if score >= 0.90:
            verdict = "green"
        elif score >= 0.60:
            verdict = "yellow"
        else:
            verdict = "red"

        return score, verdict

    def _score_evolution_health(self, evolution_health: dict[str, Any]) -> tuple[float, str]:
        """Score evolution health 0.0 (critical) → 1.0 (perfect).

        Uses data parsed from stdout: health_level (red/yellow/green),
        health_alerts count, total_genes.
        """
        health_level = str(evolution_health.get("health_level", "unknown")).lower()
        health_alerts = int(evolution_health.get("health_alerts", 0))
        total_genes = int(evolution_health.get("total_genes", 0))

        penalties = 0.0

        # Health level from the self-evolution loop's own health check
        if health_level == "red":
            penalties += 0.40
        elif health_level == "yellow":
            penalties += 0.15
        elif health_level == "unknown":
            penalties += 0.30  # no data is a yellow flag

        # Alert count penalty
        if health_alerts >= 5:
            penalties += 0.30
        elif health_alerts >= 2:
            penalties += 0.15
        elif health_alerts >= 1:
            penalties += 0.05

        # Total genes — very low counts suggest the engine is idle
        if total_genes == 0:
            penalties += 0.20
        elif total_genes < 100:
            penalties += 0.10

        score = max(0.0, 1.0 - penalties)

        if score >= 0.85:
            verdict = "green"
        elif score >= 0.55:
            verdict = "yellow"
        else:
            verdict = "red"

        return score, verdict

    # ─── Phase 4: Goal decision ─────────────────────────────────────────────

    def _decide_goal(
        self,
        saturation: dict[str, Any],
        health_verdict: str,
        evolution_verdict: str,
        evolution_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Determine the appropriate goal/action based on heuristics.

        Decision matrix:

        +------------------------+--------+----------+----------+-----------+
        | Saturated | Health    | Evol   | Goal     | Rationale            |
        +------------------------+--------+----------+----------+-----------+
        | yes       | green     | green  | fusion   | 精英饱和→融合创新    |
        | yes       | green     | yellow | promote  | 精英饱和+进化需提升  |
        | yes       | yellow    | *      | maintain | 系统资源受限→维护    |
        | yes       | red       | *      | maintain | 系统紧张→紧急维护    |
        | no        | green     | green  | observe  | 一切平稳→观察        |
        | no        | green     | yellow | intake   | 非饱和+进化待改善→审查|
        | no        | yellow    | *      | intake   | 资源预警→审查+清理   |
        | no        | red       | *      | maintain | 系统危机→维护        |
        +------------------------+--------+----------+----------+-----------+
        """
        sat = bool(saturation.get("saturation_detected", False))
        current_dim = saturation.get("current_dim") or DIMENSIONS[0]
        next_dim = saturation.get("next_dim") or DIMENSIONS[0]
        elite_ratio = _safe_float(saturation.get("elite_ratio"))

        # Read phase counts for richer decision context
        phases = evolution_state.get("phases", {}) or {}
        promote_count = int(phases.get("promote_count", 0))
        fusion_count = int(phases.get("fusion_count", 0))

        # Decision matrix
        if health_verdict == "red":
            goal = "maintenance"
            rationale = "system_health_critical"
        elif health_verdict == "yellow" and sat:
            goal = "maintenance"
            rationale = "system_health_warn_saturated"
        elif health_verdict == "yellow" and not sat:
            goal = "intake"
            rationale = "system_health_warn_not_saturated"
        elif sat and evolution_verdict == "green":
            # Saturated + healthy → fusion is the right next step
            # unless we just fused with low promote activity, then try promote
            if fusion_count > 0 and promote_count == 0:
                goal = "promote"
                rationale = "saturated_healthy_post_fusion"
            else:
                goal = "fusion"
                rationale = "saturated_healthy"
        elif sat and evolution_verdict != "green":
            goal = "promote"
            rationale = "saturated_evolution_needs_boost"
        elif not sat and evolution_verdict == "green":
            goal = "observe"
            rationale = "not_saturated_healthy"
        else:
            # not saturated + evolution not green
            goal = "intake"
            rationale = "not_saturated_evolution_needs_work"

        recommendation_zh = GOAL_PRIORITIES.get(goal, goal)
        if goal == "fusion":
            recommendation_zh += (
                f" | 当前维度={current_dim}, 精英率={elite_ratio:.1%}"
            )
        elif goal == "promote":
            recommendation_zh += (
                f" | 建议切换到维度={next_dim}"
            )

        return {
            "goal": goal,
            "rationale": rationale,
            "current_dimension": current_dim,
            "suggested_dimension": next_dim if sat else current_dim,
            "switch_dimension": sat,
            "recommendation": f"{goal}: {rationale}",
            "recommendation_zh": recommendation_zh,
            "context": {
                "saturated": sat,
                "health_verdict": health_verdict,
                "evolution_verdict": evolution_verdict,
                "elite_ratio": round(elite_ratio, 6),
                "active_count": int(saturation.get("active_count", 0)),
                "elite_count": int(saturation.get("elite_count", 0)),
            },
        }


# ─── CLI entry point ────────────────────────────────────────────────────────


def main() -> None:
    """CLI entry: run one autopilot assessment and print JSON to stdout."""
    import argparse

    parser = argparse.ArgumentParser(
        description="PGG Archon Autopilot — 自驾巡航模式. Assess system health, "
        "evolution state, and recommend goal switch.",
    )
    parser.add_argument(
        "--state",
        default=str(_DEFAULT_SELF_EVOLVE_STATE),
        help="Path to self-evolution-loop latest.json",
    )
    parser.add_argument(
        "--health",
        default=str(_DEFAULT_HEALTH_REPORT),
        help="Path to health monitor latest.json",
    )
    parser.add_argument(
        "--gene-db",
        default=str(_DEFAULT_GENE_DB),
        help="Path to evolution GeneDB SQLite",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=True,
        help="Pretty-print JSON output (default: true)",
    )
    parser.add_argument(
        "--compact",
        action="store_false",
        dest="pretty",
        help="Compact JSON output (no indent)",
    )

    args = parser.parse_args()

    engine = AutopilotEngine(
        self_evolve_state=args.state,
        health_report=args.health,
        gene_db=args.gene_db,
    )
    result = engine.assess()

    indent = 2 if args.pretty else None
    print(json.dumps(result, ensure_ascii=False, indent=indent))


if __name__ == "__main__":
    main()
