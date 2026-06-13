"""PGG health monitor for local runtime, launchd services, and GeneDB.

Collects host resource usage, ai.hermes.pgg-* launchd service status, and
PGG evolution gene status counts. Writes a latest JSON report for 15-minute
scheduler style health monitoring and includes a Feishu card payload using
three severity colors (green/yellow/red).

Boundary: local OS commands + local SQLite reads + local JSON report write.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# ── Rust native bridge ────────────────────────────────────────────
try:
    import hermes_pgg_health_monitor as _native_mod
    _NATIVE = True
except ImportError:
    _NATIVE = False

DEFAULT_DB = Path("/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3")
DEFAULT_REPORT_PATH = Path("/Users/appleoppa/.hermes/data/health-monitor/latest.json")
SERVICE_PREFIX = "ai.hermes.pgg"
ENGINE_VERSION = "pgg_health_monitor_rust/v1" if _NATIVE else "pgg_health_monitor/v1"
BOUNDARY = "pgg_health_monitor; local metrics/launchd/GeneDB read + health JSON write; no LLM/network"

CPU_ALERT_THRESHOLD = 80.0
DISK_ALERT_THRESHOLD = 90.0

SEVERITY_COLORS = {
    "green": "#22c55e",
    "yellow": "#f59e0b",
    "red": "#ef4444",
}


def _now() -> str:
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


class HealthMonitor:
    """Collect PGG runtime health and write latest.json.

    When Rust native is available, delegates core collection to
    native_collect_health() — replaces all subprocess/sysinfo/SQLite logic.
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
        """Collect host/service/gene health → write latest.json → return dict."""
        if _NATIVE:
            # Rust native: one-shot collection, no Python subprocess/sysinfo/sqlite3
            raw = _native_mod.native_collect_health(str(self.db_path))
            report = json.loads(raw)
        else:
            # Python fallback
            resources = self._collect_resources()
            launchd = self._collect_launchd_services()
            gene_db = self._collect_gene_db_health()
            alerts = self._evaluate_alerts(resources, launchd)
            level = self._severity_level(alerts)
            report = {
                "schema": ENGINE_VERSION,
                "created_at": _now(),
                "level": level,
                "status": "PASS" if level == "green" else ("WARN" if level == "yellow" else "FAIL"),
                "resources": resources,
                "launchd": launchd,
                "gene_db": gene_db,
                "alerts": alerts,
                "feishu_card": self._build_feishu_card(level, resources, launchd, gene_db, alerts),
                "report_path": str(self.report_path),
                "boundary": BOUNDARY,
            }

        report["feishu_card"] = self._build_feishu_card(
            report.get("level", "green"),
            report.get("resources", {}),
            report.get("launchd", {}),
            report.get("gene_db", {}),
            report.get("alerts", []),
        )
        report["report_path"] = str(self.report_path)
        report["boundary"] = BOUNDARY

        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.report_path.with_suffix(self.report_path.suffix + ".tmp")
        tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.report_path)
        return report

    # ─── Python fallback resource collection ──────────────────────────────

    def _collect_resources(self) -> dict[str, Any]:
        import psutil
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

    def _collect_launchd_services(self) -> dict[str, Any]:
        import subprocess
        proc = subprocess.run(["launchctl", "list"], text=True, capture_output=True, timeout=15, check=False)
        services = []
        for line in proc.stdout.splitlines():
            if self.service_prefix not in line:
                continue
            parts = line.split(None, 2)
            if len(parts) < 3 or parts[0].lower() == "pid":
                continue
            pid_raw, status_raw, label = parts
            pid = None if pid_raw == "-" else int(float(pid_raw))
            exit_code = int(float(status_raw))
            services.append({
                "label": label.strip(), "pid": pid, "exit_code": exit_code,
                "running": pid is not None and exit_code == 0,
                "healthy": exit_code == 0, "raw": line,
            })
        return {"collector": "launchctl list", "prefix": self.service_prefix,
                "count": len(services), "services": services}

    def _collect_gene_db_health(self) -> dict[str, Any]:
        import sqlite3
        counts = {s: 0 for s in ["candidate", "verified", "active", "retired", "rejected"]}
        if not self.db_path.exists():
            return {"db_path": str(self.db_path), "exists": False, "counts": counts, "total_tracked": 0}
        with sqlite3.connect(str(self.db_path)) as con:
            for status, n in con.execute(
                "SELECT status, COUNT(*) FROM evolution_genes WHERE status IN "
                "('candidate','verified','active','retired','rejected') GROUP BY status"
            ).fetchall():
                counts[str(status)] = int(n)
        return {"db_path": str(self.db_path), "exists": True, "counts": counts,
                "total_tracked": sum(counts.values())}

    def _evaluate_alerts(self, resources: dict[str, Any], launchd: dict[str, Any]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        cpu_pct = float(resources.get("cpu_percent", 0))
        disk_pct = float(resources.get("disk_percent", 0))
        if cpu_pct > CPU_ALERT_THRESHOLD:
            alerts.append({"level": "red", "type": "cpu_high",
                          "message": f"CPU usage {cpu_pct:.2f}% > {CPU_ALERT_THRESHOLD:.0f}%",
                          "value": cpu_pct, "threshold": CPU_ALERT_THRESHOLD})
        if disk_pct > DISK_ALERT_THRESHOLD:
            alerts.append({"level": "red", "type": "disk_high",
                          "message": f"Disk usage {disk_pct:.2f}% > {DISK_ALERT_THRESHOLD:.0f}%",
                          "value": disk_pct, "threshold": DISK_ALERT_THRESHOLD})
        for svc in launchd.get("services", []):
            ec = int(svc.get("exit_code", 0))
            if ec != 0:
                alerts.append({"level": "red", "type": "launchd_exit_nonzero",
                              "message": f"{svc.get('label')} exit_code={ec}",
                              "label": svc.get("label"), "exit_code": ec})
        if launchd.get("error"):
            alerts.append({"level": "yellow", "type": "launchd_collect_error",
                          "message": str(launchd["error"])})
        return alerts

    @staticmethod
    def _severity_level(alerts: list[dict[str, Any]]) -> str:
        if any(a.get("level") == "red" for a in alerts):
            return "red"
        return "yellow" if alerts else "green"

    def _build_feishu_card(self, level: str, resources: dict, launchd: dict,
                          gene_db: dict, alerts: list) -> dict:
        color = SEVERITY_COLORS.get(level, SEVERITY_COLORS["yellow"])
        title = {"green": "PGG Health OK", "yellow": "PGG Health Warning",
                "red": "PGG Health Alert"}.get(level, "PGG Health Warning")
        counts = gene_db.get("counts", {}) or {}
        alert_text = "\n".join(f"- {a.get('message')}" for a in alerts) if alerts else "- No active alerts"
        service_summary = f"{launchd.get('count', 0)} ai.hermes.pgg* services found"
        gene_summary = ", ".join(f"{k}:{counts.get(k, 0)}"
                                for k in ["candidate", "verified", "active", "retired", "rejected"])
        return {
            "config": {"wide_screen_mode": True},
            "header": {"template": {"green": "green", "yellow": "orange", "red": "red"}[level],
                       "title": {"tag": "plain_text", "content": title}},
            "css": {"severity": level, "color": color, "palette": SEVERITY_COLORS},
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content":
                f"**Level:** <font color='{color}'>{level.upper()}</font>\n"
                f"**CPU:** {resources.get('cpu_percent')}% | "
                f"**Memory:** {resources.get('memory_percent')}% | "
                f"**Disk:** {resources.get('disk_percent')}%\n"
                f"**launchd:** {service_summary}\n"
                f"**GeneDB:** {gene_summary}\n"
                f"**Alerts:**\n{alert_text}"}}],
        }


def main() -> None:
    print(json.dumps(HealthMonitor().collect_and_report(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()