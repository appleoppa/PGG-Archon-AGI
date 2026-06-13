/// PGG Health Monitor — Rust PyO3 native implementation
///
/// Collects host resource usage, ai.hermes.pgg-* launchd service status,
/// and PGG evolution gene status counts. Returns a JSON health report.
///
/// Boundary: local OS commands + SQLite reads + JSON report write.
/// Replaces pgg_health_monitor.py (399 LOC)
use pyo3::prelude::*;
use pyo3::types::PyModule;
use rusqlite::Connection;
use serde::Serialize;
use std::collections::HashMap;
use std::path::PathBuf;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};
use sysinfo::{Disks, System};

// ── Constants ─────────────────────────────────────────────────────

const ENGINE_VERSION: &str = "pgg_health_monitor_rust/v1";
const BOUNDARY: &str = "pgg_health_monitor_rust; local metrics/launchd/GeneDB read + health JSON write; no LLM/network";
const SERVICE_PREFIX: &str = "ai.hermes.pgg";
const CPU_ALERT_THRESHOLD: f64 = 80.0;
const DISK_ALERT_THRESHOLD: f64 = 90.0;
const DEFAULT_DB: &str = "/Users/appleoppa/.hermes/workspace/04_knowledge/开智/02-进化基因/apex_evolution_genes.sqlite3";

// ── Data structures ──────────────────────────────────────────────

#[derive(Debug, Clone, Serialize)]
struct ResourceMetrics {
    collector: String,
    cpu_percent: f64,
    memory_percent: f64,
    disk_percent: f64,
    load_avg: Vec<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    memory_total_bytes: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    memory_available_bytes: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    disk_total_bytes: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    disk_free_bytes: Option<u64>,
}

#[derive(Debug, Clone, Serialize)]
struct LaunchdService {
    label: String,
    pid: Option<u64>,
    exit_code: i32,
    running: bool,
    healthy: bool,
    raw: String,
}

#[derive(Debug, Clone, Serialize)]
struct LaunchdInfo {
    collector: String,
    prefix: String,
    count: usize,
    services: Vec<LaunchdService>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
struct GeneDbHealth {
    db_path: String,
    exists: bool,
    counts: HashMap<String, u64>,
    total_tracked: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
struct Alert {
    level: String,
    r#type: String,
    message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    value: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    threshold: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    label: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    exit_code: Option<i32>,
}

#[derive(Debug, Clone, Serialize)]
struct HealthReport {
    schema: String,
    created_at: String,
    level: String,
    status: String,
    resources: ResourceMetrics,
    launchd: LaunchdInfo,
    gene_db: GeneDbHealth,
    alerts: Vec<Alert>,
    boundary: String,
}

// ── Helpers ──────────────────────────────────────────────────────

fn now_iso() -> String {
    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let secs = duration.as_secs();
    let days = secs / 86400;
    let time_secs = secs % 86400;
    let hours = time_secs / 3600;
    let mins = (time_secs % 3600) / 60;
    let s = time_secs % 60;

    let mut y = 1970i64;
    let mut remaining = days as i64;
    loop {
        let days_in_year = if is_leap(y) { 366 } else { 365 };
        if remaining < days_in_year {
            break;
        }
        remaining -= days_in_year;
        y += 1;
    }
    let month_days = if is_leap(y) {
        [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    } else {
        [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    };
    let mut m = 1;
    for &md in month_days.iter() {
        if remaining < md {
            break;
        }
        remaining -= md;
        m += 1;
    }
    let d = remaining + 1;
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}+0000",
        y, m, d, hours, mins, s
    )
}

fn is_leap(y: i64) -> bool {
    (y % 4 == 0 && y % 100 != 0) || (y % 400 == 0)
}

fn safe_float(val: f64) -> f64 {
    if val.is_nan() || val.is_infinite() {
        0.0
    } else {
        val
    }
}

// ── Resource collection ──────────────────────────────────────────

fn collect_resources() -> ResourceMetrics {
    let mut sys = System::new_all();
    sys.refresh_all();

    let cpu_percent = safe_float(sys.global_cpu_usage() as f64);

    let mem_total = sys.total_memory();
    let mem_used = sys.used_memory();
    let memory_percent = if mem_total > 0 {
        safe_float((mem_used as f64 / mem_total as f64) * 100.0)
    } else {
        0.0
    };

    // Disk — try sysinfo first, then fallback to df for macOS APFS synthetic root
    let disks = Disks::new_with_refreshed_list();
    let (disk_total, disk_available) = {
        // Try root mount (/), then /System/Volumes/Data (macOS APFS data volume)
        let mut total = 1u64;
        let mut avail = 1u64;
        let found = disks.iter().find(|d| d.mount_point() == std::path::Path::new("/"))
            .or_else(|| disks.iter().find(|d| d.mount_point() == std::path::Path::new("/System/Volumes/Data")));
        if let Some(root) = found {
            let t = root.total_space();
            let a = root.available_space();
            if t > 0 {
                total = t;
                avail = a;
            }
        }
        // macOS APFS fallback: sysinfo may report 0 on synthetic root
        if total <= 1 {
            if let Ok(out) = std::process::Command::new("df").args(["-Pk", "/"]).output() {
                let stdout = String::from_utf8_lossy(&out.stdout);
                for line in stdout.lines().skip(1) {
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    if parts.len() >= 4 {
                        if let Ok(blocks) = parts[1].parse::<u64>() {
                            if let Ok(blocks_used) = parts[2].parse::<u64>() {
                                if blocks > 0 {
                                    total = blocks * 1024;
                                    avail = (blocks - blocks_used) * 1024;
                                }
                            }
                        }
                    }
                }
            }
        }
        (total, avail)
    };
    let disk_percent = if disk_total > 0 {
        safe_float(((disk_total - disk_available) as f64 / disk_total as f64) * 100.0)
    } else {
        0.0
    };

    // Load average
    let load_avg = System::load_average();
    let load_vec = vec![
        safe_float(load_avg.one as f64),
        safe_float(load_avg.five as f64),
        safe_float(load_avg.fifteen as f64),
    ];

    ResourceMetrics {
        collector: "sysinfo".to_string(),
        cpu_percent: (cpu_percent * 100.0).round() / 100.0,
        memory_percent: (memory_percent * 100.0).round() / 100.0,
        disk_percent: (disk_percent * 100.0).round() / 100.0,
        load_avg: load_vec.iter().map(|v| (v * 10000.0).round() / 10000.0).collect(),
        memory_total_bytes: Some(mem_total),
        memory_available_bytes: Some(mem_total.saturating_sub(mem_used)),
        disk_total_bytes: Some(disk_total),
        disk_free_bytes: Some(disk_available),
    }
}

// ── launchd collection ───────────────────────────────────────────

fn parse_launchctl_list_line(line: &str, prefix: &str) -> Option<LaunchdService> {
    let parts: Vec<&str> = line.splitn(3, char::is_whitespace).collect();
    if parts.len() < 3 || parts[0].to_lowercase() == "pid" {
        return None;
    }
    let label = parts[2].trim().to_string();
    if !label.contains(prefix) {
        return None;
    }
    let pid: Option<u64> = if parts[0] == "-" {
        None
    } else {
        parts[0].parse::<u64>().ok()
    };
    let exit_code: i32 = parts[1].parse::<i32>().unwrap_or(0);
    let running = pid.is_some() && exit_code == 0;
    Some(LaunchdService {
        label,
        pid,
        exit_code,
        running,
        healthy: exit_code == 0,
        raw: line.to_string(),
    })
}

fn collect_launchd() -> LaunchdInfo {
    let output = Command::new("launchctl").arg("list").output();

    match output {
        Ok(out) => {
            if !out.status.success() {
                let err = String::from_utf8_lossy(&out.stderr).trim().to_string();
                return LaunchdInfo {
                    collector: "launchctl list".to_string(),
                    prefix: SERVICE_PREFIX.to_string(),
                    count: 0,
                    services: vec![],
                    error: Some(if err.is_empty() {
                        format!("launchctl exited {}", out.status.code().unwrap_or(-1))
                    } else {
                        err
                    }),
                };
            }
            let stdout = String::from_utf8_lossy(&out.stdout);
            let services: Vec<LaunchdService> = stdout
                .lines()
                .filter_map(|line| parse_launchctl_list_line(line, SERVICE_PREFIX))
                .collect();
            let count = services.len();
            LaunchdInfo {
                collector: "launchctl list".to_string(),
                prefix: SERVICE_PREFIX.to_string(),
                count,
                services,
                error: None,
            }
        }
        Err(e) => LaunchdInfo {
            collector: "launchctl list".to_string(),
            prefix: SERVICE_PREFIX.to_string(),
            count: 0,
            services: vec![],
            error: Some(format!("{}: {}", std::io::ErrorKind::Other, e)),
        },
    }
}

// ── GeneDB health ────────────────────────────────────────────────

fn collect_gene_db(db_path: &str) -> GeneDbHealth {
    let path = PathBuf::from(db_path);
    let exists = path.exists();
    let mut counts: HashMap<String, u64> = HashMap::new();
    for s in &["candidate", "verified", "active", "retired", "rejected"] {
        counts.insert(s.to_string(), 0);
    }

    if !exists {
        return GeneDbHealth {
            db_path: db_path.to_string(),
            exists: false,
            counts,
            total_tracked: 0,
            error: Some("GeneDB not found".to_string()),
        };
    }

    match Connection::open(db_path) {
        Ok(conn) => {
            let query = "
                SELECT status, COUNT(*) AS n
                FROM evolution_genes
                WHERE status IN ('candidate', 'verified', 'active', 'retired', 'rejected')
                GROUP BY status
            ";
            let mut stmt = match conn.prepare(query) {
                Ok(s) => s,
                Err(e) => {
                    return GeneDbHealth {
                        db_path: db_path.to_string(),
                        exists: true,
                        counts,
                        total_tracked: 0,
                        error: Some(format!("SQL prepare: {}", e)),
                    };
                }
            };
            let rows = match stmt.query_map([], |row| {
                let status: String = row.get(0)?;
                let n: u64 = row.get(1)?;
                Ok((status, n))
            }) {
                Ok(r) => r,
                Err(e) => {
                    return GeneDbHealth {
                        db_path: db_path.to_string(),
                        exists: true,
                        counts,
                        total_tracked: 0,
                        error: Some(format!("SQL query: {}", e)),
                    };
                }
            };
            for row in rows.flatten() {
                counts.insert(row.0.clone(), row.1);
            }
            let total_tracked: u64 = counts.values().sum();
            GeneDbHealth {
                db_path: db_path.to_string(),
                exists: true,
                counts,
                total_tracked,
                error: None,
            }
        }
        Err(e) => GeneDbHealth {
            db_path: db_path.to_string(),
            exists: true,
            counts,
            total_tracked: 0,
            error: Some(format!("{}: {}", std::io::ErrorKind::Other, e)),
        },
    }
}

// ── Alerts ───────────────────────────────────────────────────────

fn evaluate_alerts(resources: &ResourceMetrics, launchd: &LaunchdInfo) -> Vec<Alert> {
    let mut alerts: Vec<Alert> = Vec::new();

    if resources.cpu_percent > CPU_ALERT_THRESHOLD {
        alerts.push(Alert {
            level: "red".to_string(),
            r#type: "cpu_high".to_string(),
            message: format!("CPU usage {:.2}% > {:.0}%", resources.cpu_percent, CPU_ALERT_THRESHOLD),
            value: Some(resources.cpu_percent),
            threshold: Some(CPU_ALERT_THRESHOLD),
            label: None,
            exit_code: None,
        });
    }

    if resources.disk_percent > DISK_ALERT_THRESHOLD {
        alerts.push(Alert {
            level: "red".to_string(),
            r#type: "disk_high".to_string(),
            message: format!("Disk usage {:.2}% > {:.0}%", resources.disk_percent, DISK_ALERT_THRESHOLD),
            value: Some(resources.disk_percent),
            threshold: Some(DISK_ALERT_THRESHOLD),
            label: None,
            exit_code: None,
        });
    }

    for service in &launchd.services {
        if service.exit_code != 0 {
            alerts.push(Alert {
                level: "red".to_string(),
                r#type: "launchd_exit_nonzero".to_string(),
                message: format!("{} exit_code={}", service.label, service.exit_code),
                value: None,
                threshold: None,
                label: Some(service.label.clone()),
                exit_code: Some(service.exit_code),
            });
        }
    }

    if let Some(ref err) = launchd.error {
        alerts.push(Alert {
            level: "yellow".to_string(),
            r#type: "launchd_collect_error".to_string(),
            message: err.clone(),
            value: None,
            threshold: None,
            label: None,
            exit_code: None,
        });
    }

    alerts
}

fn severity_level(alerts: &[Alert]) -> String {
    if alerts.iter().any(|a| a.level == "red") {
        "red".to_string()
    } else if !alerts.is_empty() {
        "yellow".to_string()
    } else {
        "green".to_string()
    }
}

// ── Main collection ──────────────────────────────────────────────

fn collect_health(db_path: &str) -> HealthReport {
    let resources = collect_resources();
    let launchd = collect_launchd();
    let gene_db = collect_gene_db(db_path);
    let alerts = evaluate_alerts(&resources, &launchd);
    let level = severity_level(&alerts);
    let status = match level.as_str() {
        "green" => "PASS",
        "yellow" => "WARN",
        "red" => "FAIL",
        _ => "UNKNOWN",
    };

    HealthReport {
        schema: ENGINE_VERSION.to_string(),
        created_at: now_iso(),
        level,
        status: status.to_string(),
        resources,
        launchd,
        gene_db,
        alerts,
        boundary: BOUNDARY.to_string(),
    }
}

// ── PyO3 exports ─────────────────────────────────────────────────

#[pyfunction]
fn native_collect_health(db_path: Option<String>) -> PyResult<String> {
    let path = db_path.unwrap_or_else(|| DEFAULT_DB.to_string());
    let report = collect_health(&path);
    serde_json::to_string_pretty(&report)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("serialize: {}", e)))
}

#[pyfunction]
fn native_info() -> PyResult<String> {
    Ok(format!(
        r#"{{"engine": "{}", "boundary": "{}", "default_db": "{}"}}"#,
        ENGINE_VERSION, BOUNDARY, DEFAULT_DB
    ))
}

// ── Python module ────────────────────────────────────────────────

#[pymodule]
fn hermes_pgg_health_monitor(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(native_collect_health, m)?)?;
    m.add_function(wrap_pyfunction!(native_info, m)?)?;
    Ok(())
}

// ── Tests (pure Rust only — no PyO3 symbols) ─────────────────────

#[cfg(test)]
mod tests {
    // Selectively import only pure Rust functions — avoid PyO3 symbols
    use super::{
        now_iso, safe_float, parse_launchctl_list_line, severity_level,
        evaluate_alerts, collect_health, collect_resources, collect_launchd,
        collect_gene_db, ResourceMetrics, LaunchdInfo, Alert, LaunchdService,
        BOUNDARY, ENGINE_VERSION, SERVICE_PREFIX,
    };
    use std::collections::HashMap;

    #[test]
    fn test_now_iso_format() {
        let ts = now_iso();
        assert!(ts.len() >= 20, "ISO string too short: {}", ts);
        assert!(ts.contains('T'), "Missing T separator: {}", ts);
    }

    #[test]
    fn test_safe_float_normal() {
        assert!((safe_float(42.5) - 42.5).abs() < 1e-10);
    }

    #[test]
    fn test_safe_float_nan() {
        assert!((safe_float(f64::NAN) - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_safe_float_inf() {
        assert!((safe_float(f64::INFINITY) - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_parse_launchctl_line_running() {
        let line = "12345 0 ai.hermes.pgg-autonomy-default-loop";
        let svc = parse_launchctl_list_line(line, SERVICE_PREFIX).unwrap();
        assert_eq!(svc.label, "ai.hermes.pgg-autonomy-default-loop");
        assert_eq!(svc.pid, Some(12345));
        assert_eq!(svc.exit_code, 0);
        assert!(svc.running);
        assert!(svc.healthy);
    }

    #[test]
    fn test_parse_launchctl_line_not_running() {
        let line = "- 256 ai.hermes.pgg-webui";
        let svc = parse_launchctl_list_line(line, SERVICE_PREFIX).unwrap();
        assert_eq!(svc.label, "ai.hermes.pgg-webui");
        assert!(svc.pid.is_none());
        assert_eq!(svc.exit_code, 256);
        assert!(!svc.running);
        assert!(!svc.healthy);
    }

    #[test]
    fn test_parse_launchctl_line_no_prefix() {
        let line = "123 0 com.apple.mDNSResponder";
        assert!(parse_launchctl_list_line(line, SERVICE_PREFIX).is_none());
    }

    #[test]
    fn test_parse_launchctl_line_header() {
        let line = "PID Status Label";
        assert!(parse_launchctl_list_line(line, SERVICE_PREFIX).is_none());
    }

    #[test]
    fn test_severity_green() {
        assert_eq!(severity_level(&[]), "green");
    }

    #[test]
    fn test_severity_yellow() {
        let alerts = vec![Alert {
            level: "yellow".to_string(),
            r#type: "launchd_collect_error".to_string(),
            message: "test".to_string(),
            value: None,
            threshold: None,
            label: None,
            exit_code: None,
        }];
        assert_eq!(severity_level(&alerts), "yellow");
    }

    #[test]
    fn test_severity_red() {
        let alerts = vec![Alert {
            level: "red".to_string(),
            r#type: "cpu_high".to_string(),
            message: "test".to_string(),
            value: None,
            threshold: None,
            label: None,
            exit_code: None,
        }];
        assert_eq!(severity_level(&alerts), "red");
    }

    #[test]
    fn test_evaluate_alerts_no_alerts() {
        let resources = ResourceMetrics {
            collector: "test".to_string(),
            cpu_percent: 30.0,
            memory_percent: 40.0,
            disk_percent: 50.0,
            load_avg: vec![1.0, 0.5, 0.2],
            memory_total_bytes: None,
            memory_available_bytes: None,
            disk_total_bytes: None,
            disk_free_bytes: None,
        };
        let launchd = LaunchdInfo {
            collector: "test".to_string(),
            prefix: SERVICE_PREFIX.to_string(),
            count: 0,
            services: vec![],
            error: None,
        };
        let alerts = evaluate_alerts(&resources, &launchd);
        assert!(alerts.is_empty());
    }

    #[test]
    fn test_evaluate_alerts_cpu_high() {
        let resources = ResourceMetrics {
            collector: "test".to_string(),
            cpu_percent: 95.0,
            memory_percent: 40.0,
            disk_percent: 50.0,
            load_avg: vec![1.0, 0.5, 0.2],
            memory_total_bytes: None,
            memory_available_bytes: None,
            disk_total_bytes: None,
            disk_free_bytes: None,
        };
        let launchd = LaunchdInfo {
            collector: "test".to_string(),
            prefix: SERVICE_PREFIX.to_string(),
            count: 0,
            services: vec![],
            error: None,
        };
        let alerts = evaluate_alerts(&resources, &launchd);
        assert!(alerts.iter().any(|a| a.r#type == "cpu_high"));
    }

    #[test]
    fn test_evaluate_alerts_disk_high() {
        let resources = ResourceMetrics {
            collector: "test".to_string(),
            cpu_percent: 30.0,
            memory_percent: 40.0,
            disk_percent: 95.0,
            load_avg: vec![1.0, 0.5, 0.2],
            memory_total_bytes: None,
            memory_available_bytes: None,
            disk_total_bytes: None,
            disk_free_bytes: None,
        };
        let launchd = LaunchdInfo {
            collector: "test".to_string(),
            prefix: SERVICE_PREFIX.to_string(),
            count: 0,
            services: vec![],
            error: None,
        };
        let alerts = evaluate_alerts(&resources, &launchd);
        assert!(alerts.iter().any(|a| a.r#type == "disk_high"));
    }

    #[test]
    fn test_collect_gene_db_nonexistent() {
        let result = collect_gene_db("/tmp/nonexistent_db_12345.sqlite3");
        assert!(!result.exists);
        assert!(result.error.is_some());
    }

    #[test]
    fn test_collect_health_report() {
        let report = collect_health("/tmp/nonexistent_db_12345.sqlite3");
        assert_eq!(report.schema, ENGINE_VERSION);
        assert_eq!(report.boundary, BOUNDARY);
        assert!(!report.created_at.is_empty());
        assert!(!report.gene_db.exists);
        assert!(report.gene_db.error.is_some());
    }

    #[test]
    fn test_collect_resources_basic() {
        let r = collect_resources();
        assert_eq!(r.collector, "sysinfo");
        assert!(r.cpu_percent >= 0.0 && r.cpu_percent <= 100.0);
        assert!(r.memory_percent >= 0.0 && r.memory_percent <= 100.0);
        assert!(r.disk_percent >= 0.0 && r.disk_percent <= 100.0);
        assert_eq!(r.load_avg.len(), 3);
    }

    #[test]
    fn test_collect_launchd_basic() {
        let ld = collect_launchd();
        assert_eq!(ld.collector, "launchctl list");
        assert_eq!(ld.prefix, SERVICE_PREFIX);
    }
}