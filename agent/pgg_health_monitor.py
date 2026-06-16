"""PGG health monitor for local runtime, launchd services, and GeneDB.

Collects host resource usage, ai.hermes.pgg-* launchd service status, and
PGG evolution gene status counts. Writes a latest JSON report for 15-minute
scheduler style health monitoring and includes a Feishu card payload using
three severity colors (green/yellow/red).

Boundary: local OS commands + local SQLite reads + local JSON report write.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any

DEFAULT_DB = Path("/Users/appleoppa/.hermes/data/pgg_archon.db")
DEFAULT_REPORT_PATH = Path("/Users/appleoppa/.hermes/data/health-monitor/latest.json")
SERVICE_PREFIX = "ai.hermes.pgg"
ENGINE_VERSION = "pgg_health_monitor/v1"
BOUNDARY = "pgg_health_monitor; local metrics/launchd/GeneDB read + health JSON write; no LLM/network"

CPU_ALERT_THRESHOLD = 80.0
DISK_ALERT_THRESHOLD = 90.0

SEVERITY_COLORS = {
    "green": "#22c55e",
    "yellow": "#f59e0b",
    "red": "#ef4444",
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _run(command: list[str], timeout: int = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class HealthMonitor:
    """Collect PGG runtime health and write latest.json.

    Public method:
      - collect_and_report() -> dict
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB,
        report_path: str | Path = DEFAULT_REPORT_PATH,
        service_prefix: str = SERVICE_PREFIX,
    ) -> None:
        self.db_path = Path(db_path)
        self.report_path = Path(report_path)
        self.service_prefix = service_prefix

    def collect_and_report(self) -> dict[str, Any]:
        """Collect host/service/gene health, write latest JSON, and return it."""
        resources = self._collect_resources()
        launchd = self._collect_launchd_services()
        gene_db = self._collect_gene_db_health()
        symlinks = self._collect_bin_symlinks()
        akashic_stats = self._collect_akashic_stats()
        alerts = self._evaluate_alerts(resources, launchd, symlinks)
        level = self._severity_level(alerts)

        report = {
            "schema": ENGINE_VERSION,
            "created_at": _now(),
            "level": level,
            "status": "PASS" if level == "green" else ("WARN" if level == "yellow" else "FAIL"),
            "resources": resources,
            "launchd": launchd,
            "gene_db": gene_db,
            "bin_symlinks": symlinks,
            "akashic_stats": akashic_stats,
            "alerts": alerts,
            "feishu_card": self._build_feishu_card(level, resources, launchd, gene_db, alerts),
            "report_path": str(self.report_path),
            "boundary": BOUNDARY,
        }

        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.report_path.with_suffix(self.report_path.suffix + ".tmp")
        tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.report_path)
        return report

    # ─── Resource collection ──────────────────────────────────────────────

    def _collect_resources(self) -> dict[str, Any]:
        try:
            import psutil  # type: ignore

            cpu_percent = float(psutil.cpu_percent(interval=0.2))
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            load_avg = tuple(round(float(x), 4) for x in (psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0)))
            return {
                "collector": "psutil",
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(float(memory.percent), 2),
                "disk_percent": round(float(disk.percent), 2),
                "load_avg": load_avg,
                "memory_total_bytes": int(memory.total),
                "memory_available_bytes": int(memory.available),
                "disk_total_bytes": int(disk.total),
                "disk_free_bytes": int(disk.free),
            }
        except Exception as exc:
            fallback = self._collect_resources_fallback()
            fallback["psutil_error"] = f"{type(exc).__name__}: {exc}"
            return fallback

    def _collect_resources_fallback(self) -> dict[str, Any]:
        """Fallback resource collection using macOS vm_stat/df/ps commands."""
        cpu_percent = 0.0
        memory_percent = 0.0
        disk_percent = 0.0
        load_avg: tuple[float, float, float] = (0.0, 0.0, 0.0)

        # CPU: sum process %CPU from ps. It can exceed 100 on multi-core systems;
        # normalize by hw.logicalcpu when available.
        try:
            ps = _run(["ps", "-A", "-o", "%cpu"], timeout=10)
            values = [_safe_float(x.strip()) for x in ps.stdout.splitlines()[1:] if x.strip()]
            total_cpu = sum(values)
            cpus_proc = _run(["sysctl", "-n", "hw.logicalcpu"], timeout=5)
            cpu_count = max(int(_safe_float(cpus_proc.stdout.strip(), 1)), 1)
            cpu_percent = max(0.0, min(100.0, total_cpu / cpu_count))
        except Exception:
            cpu_percent = 0.0

        try:
            uptime = _run(["uptime"], timeout=5).stdout
            matches = re.findall(r"load averages?:\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", uptime)
            if matches:
                load_avg = tuple(_safe_float(x) for x in matches[-1])  # type: ignore[assignment]
        except Exception:
            pass

        try:
            vm = _run(["vm_stat"], timeout=10).stdout
            page_size_match = re.search(r"page size of (\d+) bytes", vm)
            page_size = int(page_size_match.group(1)) if page_size_match else 4096
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
            "load_avg": tuple(round(float(x), 4) for x in load_avg),
        }

    # ─── launchd ──────────────────────────────────────────────────────────

    def _collect_launchd_services(self) -> dict[str, Any]:
        """Collect launchd status for labels matching ai.hermes.pgg*."""
        try:
            proc = _run(["launchctl", "list"], timeout=15)
            if proc.returncode != 0:
                return {
                    "collector": "launchctl list",
                    "services": [],
                    "count": 0,
                    "error": proc.stderr.strip() or f"launchctl exited {proc.returncode}",
                }

            services = []
            for line in proc.stdout.splitlines():
                if self.service_prefix not in line:
                    continue
                parsed = self._parse_launchctl_list_line(line)
                if parsed:
                    services.append(parsed)

            return {
                "collector": "launchctl list",
                "prefix": self.service_prefix,
                "count": len(services),
                "services": services,
            }
        except Exception as exc:
            return {
                "collector": "launchctl list",
                "services": [],
                "count": 0,
                "error": f"{type(exc).__name__}: {exc}",
            }

    def _parse_launchctl_list_line(self, line: str) -> dict[str, Any] | None:
        # launchctl list columns: PID Status Label. PID may be '-'.
        parts = line.split(None, 2)
        if len(parts) < 3 or parts[0].lower() == "pid":
            return None
        pid_raw, status_raw, label = parts
        if self.service_prefix not in label:
            return None
        pid = None if pid_raw == "-" else int(_safe_float(pid_raw, 0))
        exit_code = int(_safe_float(status_raw, 0))
        running = pid is not None
        healthy = running or exit_code == 0
        return {
            "label": label.strip(),
            "pid": pid,
            "exit_code": exit_code,
            "running": running,
            "healthy": healthy,
            "raw": line,
        }

    # ─── GeneDB ───────────────────────────────────────────────────────────

    def _collect_gene_db_health(self) -> dict[str, Any]:
        statuses = ["candidate", "promoted", "active", "retired", "rejected"]
        counts = {status: 0 for status in statuses}

        if not self.db_path.exists():
            return {
                "db_path": str(self.db_path),
                "exists": False,
                "counts": counts,
                "total_tracked": 0,
                "error": "GeneDB not found",
            }

        try:
            with sqlite3.connect(str(self.db_path)) as con:
                rows = con.execute(
                    """
                    SELECT state, COUNT(*) AS n
                    FROM evolution_genes
                    WHERE state IN ('candidate', 'verified', 'active', 'retired', 'rejected', 'promoted')
                    GROUP BY state
                    """
                ).fetchall()
            for status, n in rows:
                counts[str(status)] = int(n or 0)
            return {
                "db_path": str(self.db_path),
                "exists": True,
                "counts": counts,
                "total_tracked": sum(counts.values()),
            }
        except Exception as exc:
            return {
                "db_path": str(self.db_path),
                "exists": True,
                "counts": counts,
                "total_tracked": 0,
                "error": f"{type(exc).__name__}: {exc}",
            }

    # ─── Symlink and readable local data checks ────────────────────────────

    def _collect_bin_symlinks(self) -> dict[str, Any]:
        """Check every symlink in ~/.hermes/bin and report broken targets."""
        bin_dir = Path.home() / ".hermes" / "bin"
        symlinks: list[dict[str, Any]] = []
        broken: list[dict[str, Any]] = []
        if not bin_dir.exists():
            return {
                "bin_dir": str(bin_dir),
                "exists": False,
                "total_symlinks": 0,
                "broken_count": 0,
                "broken": [],
                "status": "WATCH_BIN_DIR_MISSING",
            }
        for entry in sorted(bin_dir.iterdir(), key=lambda p: p.name):
            if not entry.is_symlink():
                continue
            try:
                target = entry.readlink()
                resolved = entry.resolve(strict=False)
                valid = entry.exists()
                item = {
                    "name": entry.name,
                    "path": str(entry),
                    "target": str(target),
                    "resolved": str(resolved),
                    "valid": bool(valid),
                }
            except OSError as exc:
                item = {
                    "name": entry.name,
                    "path": str(entry),
                    "target": None,
                    "resolved": None,
                    "valid": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            symlinks.append(item)
            if not item.get("valid"):
                broken.append(item)
        return {
            "bin_dir": str(bin_dir),
            "exists": True,
            "total_symlinks": len(symlinks),
            "broken_count": len(broken),
            "broken": broken,
            "status": "PASS" if not broken else "WARN_BROKEN_SYMLINKS",
        }

    def _collect_akashic_stats(self) -> dict[str, Any]:
        """Read the standalone Akashic stats JSON consumed by health monitor."""
        path = Path.home() / ".hermes" / "data" / "akashic_stats.json"
        if not path.exists():
            return {"path": str(path), "exists": False, "status": "WATCH_MISSING"}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"path": str(path), "exists": True, "status": "ERROR_NON_OBJECT"}
            return {
                "path": str(path),
                "exists": True,
                "status": data.get("status", "UNKNOWN"),
                "schema": data.get("schema"),
                "total_entries": data.get("total_entries"),
                "vector_dim": data.get("vector_dim"),
                "last_updated": data.get("last_updated"),
            }
        except Exception as exc:
            return {
                "path": str(path),
                "exists": True,
                "status": "ERROR",
                "error": f"{type(exc).__name__}: {exc}",
            }

    # ─── Alerts and Feishu card ───────────────────────────────────────────

    def _evaluate_alerts(self, resources: dict[str, Any], launchd: dict[str, Any], symlinks: dict[str, Any]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        cpu_percent = _safe_float(resources.get("cpu_percent"))
        disk_percent = _safe_float(resources.get("disk_percent"))

        if cpu_percent > CPU_ALERT_THRESHOLD:
            alerts.append({
                "level": "red",
                "type": "cpu_high",
                "message": f"CPU usage {cpu_percent:.2f}% > {CPU_ALERT_THRESHOLD:.0f}%",
                "value": cpu_percent,
                "threshold": CPU_ALERT_THRESHOLD,
            })

        if disk_percent > DISK_ALERT_THRESHOLD:
            alerts.append({
                "level": "red",
                "type": "disk_high",
                "message": f"Disk usage {disk_percent:.2f}% > {DISK_ALERT_THRESHOLD:.0f}%",
                "value": disk_percent,
                "threshold": DISK_ALERT_THRESHOLD,
            })

        for service in launchd.get("services", []) or []:
            exit_code = int(_safe_float(service.get("exit_code"), 0))
            if exit_code != 0 and not bool(service.get("healthy")):
                alerts.append({
                    "level": "red",
                    "type": "launchd_exit_nonzero",
                    "message": f"{service.get('label')} exit_code={exit_code}",
                    "label": service.get("label"),
                    "exit_code": exit_code,
                })

        if launchd.get("error"):
            alerts.append({
                "level": "yellow",
                "type": "launchd_collect_error",
                "message": str(launchd.get("error")),
            })

        for item in symlinks.get("broken", []) or []:
            alerts.append({
                "level": "red",
                "type": "broken_symlink",
                "message": f"Broken symlink {item.get('name')} -> {item.get('target')}",
                "path": item.get("path"),
                "target": item.get("target"),
            })

        return alerts

    def _severity_level(self, alerts: list[dict[str, Any]]) -> str:
        if any(a.get("level") == "red" for a in alerts):
            return "red"
        if alerts:
            return "yellow"
        return "green"

    def _build_feishu_card(
        self,
        level: str,
        resources: dict[str, Any],
        launchd: dict[str, Any],
        gene_db: dict[str, Any],
        alerts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        color = SEVERITY_COLORS.get(level, SEVERITY_COLORS["yellow"])
        title = {
            "green": "PGG Health OK",
            "yellow": "PGG Health Warning",
            "red": "PGG Health Alert",
        }.get(level, "PGG Health Warning")

        counts = gene_db.get("counts", {}) or {}
        alert_text = "\n".join(f"- {a.get('message')}" for a in alerts) if alerts else "- No active alerts"
        service_summary = f"{launchd.get('count', 0)} ai.hermes.pgg* services found"
        gene_summary = ", ".join(f"{k}:{counts.get(k, 0)}" for k in ["candidate", "promoted", "active", "retired", "rejected"])

        # This is a Feishu interactive-card compatible structure with explicit
        # three-color CSS-like tokens for downstream renderers/bridges.
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": {"green": "green", "yellow": "orange", "red": "red"}[level],
                "title": {"tag": "plain_text", "content": title},
            },
            "css": {
                "severity": level,
                "color": color,
                "palette": SEVERITY_COLORS,
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**Level:** <font color='{color}'>{level.upper()}</font>\n"
                            f"**CPU:** {resources.get('cpu_percent')}% | "
                            f"**Memory:** {resources.get('memory_percent')}% | "
                            f"**Disk:** {resources.get('disk_percent')}%\n"
                            f"**launchd:** {service_summary}\n"
                            f"**GeneDB:** {gene_summary}\n"
                            f"**Alerts:**\n{alert_text}"
                        ),
                    },
                }
            ],
        }


def main() -> None:
    print(json.dumps(HealthMonitor().collect_and_report(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
