use chrono::Local;
use serde::Serialize;
use serde_json::Value;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Serialize)]
struct Probe {
    id: &'static str,
    title: &'static str,
    status: String,
    evidence: Value,
    boundary: &'static str,
}

#[derive(Serialize)]
struct Report {
    schema: &'static str,
    generated_at: String,
    status: String,
    score: f64,
    source_docs: Vec<&'static str>,
    probes: Vec<Probe>,
    conflicts_require_user_adjudication: Vec<Value>,
    boundary: Vec<&'static str>,
}

fn home() -> PathBuf {
    PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}
fn run(cmd: &str, args: &[&str]) -> (i32, String) {
    match Command::new(cmd).args(args).output() {
        Ok(o) => {
            let mut s = String::from_utf8_lossy(&o.stdout).to_string();
            if s.trim().is_empty() {
                s = String::from_utf8_lossy(&o.stderr).to_string();
            }
            if s.len() > 1600 {
                s.truncate(1600);
            }
            (o.status.code().unwrap_or(-1), s)
        }
        Err(e) => (-127, e.to_string()),
    }
}
fn obj(pairs: Vec<(&str, Value)>) -> Value {
    let mut m = serde_json::Map::new();
    for (k, v) in pairs {
        m.insert(k.to_string(), v);
    }
    Value::Object(m)
}
fn file_age_hours(p: &Path) -> Option<i64> {
    let mt = fs::metadata(p).ok()?.modified().ok()?;
    Some(
        std::time::SystemTime::now()
            .duration_since(mt)
            .ok()?
            .as_secs() as i64
            / 3600,
    )
}
fn main() {
    let h = home();
    let hermes = h.join(".hermes");
    let mem = h.join(".hermes/memories/MEMORY.md");
    let user = h.join(".hermes/memories/USER.md");
    let soul = h.join(".hermes/SOUL.md");
    let data = h.join(".hermes/data");
    let out_dir = h.join(".hermes/workspace/pgg-archon-governance/memory-stability-report-daily");
    let _ = fs::create_dir_all(&out_dir);
    let mut probes = Vec::new();
    let (mem_rc, mem_out) = run("/Users/appleoppa/.local/bin/记忆系统", &["--json"]);
    let mem_ok = mem_rc == 0 && mem_out.contains("PASS") && mem_out.contains("read_only");
    probes.push(Probe {
        id: "queue_health",
        title: "队列/运行健康度",
        status: if mem_ok {
            "COVERED".into()
        } else {
            "WATCH".into()
        },
        evidence: obj(vec![
            ("command", "记忆系统 --json".into()),
            ("exit_code", mem_rc.into()),
            ("sample", mem_out.into()),
        ]),
        boundary: "只读状态；不自动 apply Department/SWR memory",
    });
    let mut sizes = serde_json::Map::new();
    for p in [&mem, &user, &soul] {
        sizes.insert(
            p.display().to_string(),
            fs::metadata(p).map(|m| m.len()).unwrap_or(0).into(),
        );
    }
    let mem_size = fs::metadata(&mem).map(|m| m.len()).unwrap_or(0);
    let user_size = fs::metadata(&user).map(|m| m.len()).unwrap_or(0);
    let core_ok =
        mem.exists() && user.exists() && soul.exists() && mem_size > 1000 && user_size > 1000;
    probes.push(Probe {
        id: "core_memory_integrity",
        title: "核心记忆完整性",
        status: if core_ok {
            "COVERED".into()
        } else {
            "WATCH".into()
        },
        evidence: Value::Object(sizes),
        boundary: "文件存在/大小仅是完整性信号，不代表内容正确或无漂移",
    });
    let archive=h.join(".hermes/workspace/治理/memory-five-tier-compaction-20260610T115131/FULL_CURATED_MEMORY_ARCHIVE.md");
    let backups_dir = h.join(".hermes/workspace/治理");
    let backup_ok = archive.exists() || backups_dir.exists();
    probes.push(Probe {
        id: "backup_recovery",
        title: "备份与恢复就绪度",
        status: if backup_ok {
            "PARTIAL_COVERED".into()
        } else {
            "WATCH".into()
        },
        evidence: obj(vec![
            ("archive", archive.display().to_string().into()),
            ("archive_exists", archive.exists().into()),
            ("governance_dir_exists", backups_dir.exists().into()),
        ]),
        boundary: "不自动恢复/覆盖 MEMORY；恢复需人工裁决和漂移检查",
    });
    let retro = data.join("retrospective_lessons.jsonl");
    let retro_ok = retro.exists() && fs::metadata(&retro).map(|m| m.len()).unwrap_or(0) > 0;
    probes.push(Probe {
        id: "retrospective_lessons",
        title: "自动复盘 lessons 库",
        status: if retro_ok {
            "COVERED".into()
        } else {
            "WATCH_EMPTY".into()
        },
        evidence: obj(vec![
            ("path", retro.display().to_string().into()),
            ("exists", retro.exists().into()),
            (
                "size",
                fs::metadata(&retro).map(|m| m.len()).unwrap_or(0).into(),
            ),
        ]),
        boundary: "pre_llm 注入器只能注入 bounded checklist；不自动写 MEMORY/USER",
    });
    let (auto_rc, auto_out) = run(
        "launchctl",
        &["list", "ai.hermes.pgg-autonomy-default-loop"],
    );
    let (batch_rc, batch_out) = run(
        "launchctl",
        &["list", "ai.hermes.pgg-batch-evolution-scheduler"],
    );
    let launch_ok = auto_rc == 0 && batch_rc == 0;
    probes.push(Probe {
        id: "timed_chain",
        title: "定时链路与交付承诺",
        status: if launch_ok {
            "COVERED".into()
        } else {
            "WATCH".into()
        },
        evidence: obj(vec![
            ("autonomy_exit", auto_rc.into()),
            ("autonomy_sample", auto_out.into()),
            ("batch_exit", batch_rc.into()),
            ("batch_sample", batch_out.into()),
        ]),
        boundary: "launchd loaded 不等于业务完成；需结合 latest/ledger",
    });
    let latest_mem_email =
        hermes.join("workspace/pgg-archon-governance/email-memory-sync-auto/latest.json");
    let email_age = file_age_hours(&latest_mem_email).unwrap_or(999999);
    probes.push(Probe {
        id: "external_sanitized_sync",
        title: "外部脱敏同步状态",
        status: if latest_mem_email.exists() && email_age < 48 {
            "PARTIAL_COVERED".into()
        } else {
            "WATCH".into()
        },
        evidence: obj(vec![
            ("latest", latest_mem_email.display().to_string().into()),
            ("exists", latest_mem_email.exists().into()),
            ("age_hours", email_age.into()),
        ]),
        boundary: "只证明脱敏治理包；不证明飞书/云端全量记忆中枢",
    });
    let covered = probes.iter().filter(|p| p.status == "COVERED").count() as f64;
    let partial = probes
        .iter()
        .filter(|p| p.status.starts_with("PARTIAL"))
        .count() as f64;
    let score = ((covered + partial * 0.5) / probes.len() as f64 * 1000.0).round() / 10.0;
    let status = if score >= 85.0 {
        "PASS"
    } else if score >= 60.0 {
        "WATCH"
    } else {
        "BLOCKED"
    }
    .to_string();
    let conflicts = vec![
        obj(vec![
            ("id", "M1.async_queue_confirm".into()),
            ("adjudication", "ACCEPT_RECOMMENDATION".into()),
            (
                "doc_suggests",
                "记忆写入异步队列 + 即时确认 + 后台写入".into(),
            ),
            (
                "decision",
                "维持候选/分层治理，不启用自动写 MEMORY/USER 的异步写入队列".into(),
            ),
            (
                "implemented_boundary",
                "只读状态报告；记忆写入仍走人审/候选/skill/reference/manifest 分层".into(),
            ),
        ]),
        obj(vec![
            ("id", "M2.midnight_backup_restore".into()),
            ("adjudication", "ACCEPT_RECOMMENDATION".into()),
            (
                "doc_suggests",
                "00:00 每日补全与备份恢复，MD5 自动校验，异常自动恢复".into(),
            ),
            (
                "decision",
                "维持只读健康报告，不启用自动恢复覆盖 MEMORY".into(),
            ),
            (
                "implemented_boundary",
                "每日报告检查备份/归档状态；任何恢复/覆盖需单独裁决".into(),
            ),
        ]),
        obj(vec![
            ("id", "M3.visual_feishu_report".into()),
            ("adjudication", "ACCEPT_RECOMMENDATION".into()),
            ("doc_suggests", "飞书可视化稳定性报告/云端留存".into()),
            (
                "decision",
                "先本地 daily report，不启用飞书自动写入/云端留存".into(),
            ),
            (
                "implemented_boundary",
                "外部同步仅限已授权脱敏邮件治理包".into(),
            ),
        ]),
        obj(vec![
            ("id", "M4.auto_retrospective_trigger".into()),
            ("adjudication", "ACCEPT_RECOMMENDATION".into()),
            (
                "doc_suggests",
                "任务失败/高耗时/反复修改/重要产出后自动复盘".into(),
            ),
            (
                "decision",
                "保留 bounded checklist 注入，不自动生成复盘并写长期记忆".into(),
            ),
            (
                "implemented_boundary",
                "retrospective lessons 空库继续 WATCH；写入 lessons/MEMORY/USER 需单独裁决".into(),
            ),
        ]),
    ];
    let report = Report {
        schema: "pgg_memory_stability_report/v1",
        generated_at: Local::now().to_rfc3339(),
        status,
        score,
        source_docs: vec![
            "UZJP memory runtime spec",
            "V8pB stability report v2.0",
            "ViaW stability report v2.1 visual",
            "PRQE auto retrospective rules",
        ],
        probes,
        conflicts_require_user_adjudication: conflicts,
        boundary: vec![
            "read-only",
            "no MEMORY/USER raw write",
            "no automatic restore overwrite",
            "no Feishu/cloud auto-write",
            "no credential/config/provider mutation",
        ],
    };
    let json = serde_json::to_string_pretty(&report).unwrap();
    fs::write(out_dir.join("latest.json"), &json).unwrap();
    fs::write(
        out_dir.join(format!(
            "memory-stability-{}.json",
            Local::now().format("%Y%m%d-%H%M%S")
        )),
        &json,
    )
    .unwrap();
    println!("{}", json);
}
