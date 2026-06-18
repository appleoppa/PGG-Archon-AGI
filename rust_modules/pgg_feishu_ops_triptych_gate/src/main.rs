use chrono::Local;
use serde::Serialize;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Serialize)]
struct Check {
    id: &'static str,
    title: &'static str,
    feishu_requirement: &'static str,
    local_mapping: &'static str,
    status: String,
    evidence: serde_json::Value,
    boundary: &'static str,
}

#[derive(Serialize)]
struct Report {
    schema: &'static str,
    generated_at: String,
    source_doc_token: &'static str,
    source_doc_title: &'static str,
    overall_status: String,
    score: f64,
    checks: Vec<Check>,
    conflicts_require_user_adjudication: Vec<serde_json::Value>,
    boundary: Vec<&'static str>,
}

fn home() -> PathBuf {
    PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}
fn exists(p: &Path) -> bool {
    p.exists()
}
fn run(cmd: &str, args: &[&str]) -> (i32, String) {
    match Command::new(cmd).args(args).output() {
        Ok(o) => {
            let mut s = String::from_utf8_lossy(&o.stdout).to_string();
            if s.trim().is_empty() {
                s = String::from_utf8_lossy(&o.stderr).to_string();
            }
            if s.len() > 1200 {
                s.truncate(1200);
            }
            (o.status.code().unwrap_or(-1), s)
        }
        Err(e) => (-127, e.to_string()),
    }
}
fn json_obj(pairs: Vec<(&str, serde_json::Value)>) -> serde_json::Value {
    let mut m = serde_json::Map::new();
    for (k, v) in pairs {
        m.insert(k.to_string(), v);
    }
    serde_json::Value::Object(m)
}
fn status_pass(b: bool) -> String {
    if b {
        "COVERED".into()
    } else {
        "MISSING".into()
    }
}

fn main() {
    let h = home();
    let hermes = h.join(".hermes");
    let bin = hermes.join("bin");
    let data = hermes.join("data");
    let workspace = hermes.join("workspace");
    let launch_agents = h.join("Library/LaunchAgents");
    let mut checks: Vec<Check> = Vec::new();

    let health_cli = bin.join("pgg-health-monitor");
    let (health_rc, health_out) = if exists(&health_cli) {
        run(health_cli.to_str().unwrap(), &["--json"])
    } else {
        (-127, "missing".into())
    };
    let health_ok = health_rc == 0 && health_out.contains("\"status\": \"PASS\"");
    checks.push(Check {
        id: "inspection.health",
        title: "日常巡检/健康自检",
        feishu_requirement: "全链路健康自检、系统资源、错误日志、状态文件、外部服务连通性",
        local_mapping: "pgg-health-monitor --json + launchd 状态 + Hermes 门禁",
        status: status_pass(health_ok),
        evidence: json_obj(vec![
            ("cli", health_cli.display().to_string().into()),
            ("exit_code", health_rc.into()),
            ("sample", health_out.into()),
        ]),
        boundary: "只读状态面；不把绿色健康等同于全部业务能力完成",
    });

    let memory_cli = "/Users/appleoppa/.local/bin/记忆系统";
    let (mem_rc, mem_out) = run(memory_cli, &["--json"]);
    let mem_ok = mem_rc == 0 && mem_out.contains("PASS");
    checks.push(Check {
        id: "inspection.memory",
        title: "记忆系统巡检",
        feishu_requirement: "MEMORY、知识库同步、ontology/图谱实体、复盘入库",
        local_mapping: "记忆系统 --json + Akashic/curated memory 状态",
        status: status_pass(mem_ok),
        evidence: json_obj(vec![
            ("cli", memory_cli.into()),
            ("exit_code", mem_rc.into()),
            ("sample", mem_out.into()),
        ]),
        boundary: "不自动写 MEMORY/USER；飞书知识库同步只按显式目标与脱敏边界执行",
    });

    let goal_cli = bin.join("hermes-goal");
    let (goal_rc, goal_out) = if exists(&goal_cli) {
        run(goal_cli.to_str().unwrap(), &[])
    } else {
        (-127, "missing".into())
    };
    let goal_ok = goal_rc == 0 && goal_out.contains("overall_status") && goal_out.contains("PASS");
    checks.push(Check {
        id: "inspection.end_to_end",
        title: "端到端门禁巡检",
        feishu_requirement: "用户指令→拆解→执行→复盘→记忆→检索回答的闭环验证",
        local_mapping: "hermes-goal 统一状态面 + 本机 gate 读回",
        status: if goal_ok {
            "PARTIAL_COVERED".into()
        } else {
            "MISSING".into()
        },
        evidence: json_obj(vec![
            ("cli", goal_cli.display().to_string().into()),
            ("exit_code", goal_rc.into()),
            ("sample", goal_out.into()),
        ]),
        boundary: "hermes-goal 是本地有界状态面；不证明法律正确性/full AGI/外部 benchmark",
    });

    let autonomy_plist = launch_agents.join("ai.hermes.pgg-autonomy-default-loop.plist");
    let (launch_rc, launch_out) = run(
        "launchctl",
        &["list", "ai.hermes.pgg-autonomy-default-loop"],
    );
    let launch_ok = exists(&autonomy_plist) && launch_rc == 0;
    checks.push(Check {
        id: "inspection.scheduler",
        title: "调度系统",
        feishu_requirement: "Cron/heartbeat/watchdog 最近运行成功",
        local_mapping: "macOS launchd + Rust/Python runner；不用 Hermes cron 作机器级定时",
        status: status_pass(launch_ok),
        evidence: json_obj(vec![
            ("plist", autonomy_plist.display().to_string().into()),
            ("launchctl_exit", launch_rc.into()),
            ("sample", launch_out.into()),
        ]),
        boundary: "文档 crontab/OpenClaw 命令已映射为 launchd；不新增 cron",
    });

    let ws_exists = exists(&workspace);
    let (du_rc, du_out) = run("du", &["-sh", workspace.to_str().unwrap_or("")]);
    let ws_ok = ws_exists && du_rc == 0;
    checks.push(Check {
        id: "asset.workspace_inventory",
        title: "工作区资产整理基线",
        feishu_requirement: "全量文件扫描、元数据提取、分类标签、索引构建、可用性验证",
        local_mapping: "~/.hermes/workspace 分区 + 归档治理；本 gate 只读统计",
        status: if ws_ok {
            "PARTIAL_COVERED".into()
        } else {
            "MISSING".into()
        },
        evidence: json_obj(vec![
            ("workspace", workspace.display().to_string().into()),
            ("du_exit", du_rc.into()),
            ("du", du_out.into()),
        ]),
        boundary: "不自动删除/移动/去重文件；资产整理需单独 allowlist 和备份",
    });

    let manifest = data.join("EVOLUTION_MANIFEST.json");
    let manifest_ok = exists(&manifest);
    let manifest_size = fs::metadata(&manifest).map(|m| m.len()).unwrap_or(0);
    checks.push(Check {
        id: "diagnosis.manifest",
        title: "诊断与演化总账",
        feishu_requirement: "深度诊断、修复记录、记忆中枢集成、长期索引",
        local_mapping: "EVOLUTION_MANIFEST.json + skills references + latest gates",
        status: status_pass(manifest_ok && manifest_size > 1000),
        evidence: json_obj(vec![
            ("manifest", manifest.display().to_string().into()),
            ("size_bytes", manifest_size.into()),
        ]),
        boundary: "总账是索引，不替代 live gate 读回",
    });

    let email_sync_plist = launch_agents.join("ai.hermes.pgg-email-sync.plist");
    let email_latest = workspace.join("pgg-archon-governance/email-memory-sync-auto/latest.json");
    let email_ok = exists(&email_sync_plist) && exists(&email_latest);
    checks.push(Check {
        id: "diagnosis.feishu_memory_sync",
        title: "外部记忆同步/脱敏备份",
        feishu_requirement: "飞书知识库记忆中枢同步、检索优先级、云端持久化",
        local_mapping: "当前为 QQ 邮箱脱敏治理包 + 飞书 raw 读取；非全量云端记忆镜像",
        status: if email_ok {
            "PARTIAL_COVERED".into()
        } else {
            "MISSING".into()
        },
        evidence: json_obj(vec![
            (
                "email_sync_plist",
                email_sync_plist.display().to_string().into(),
            ),
            ("email_latest", email_latest.display().to_string().into()),
        ]),
        boundary: "禁止自动同步案件、密钥、config、MEMORY/USER 原文；飞书云端中枢属于需裁决项",
    });

    let covered = checks.iter().filter(|c| c.status == "COVERED").count() as f64;
    let partial = checks
        .iter()
        .filter(|c| c.status.starts_with("PARTIAL"))
        .count() as f64;
    let score = ((covered + partial * 0.5) / checks.len() as f64 * 100.0 * 10.0).round() / 10.0;
    let overall = if score >= 85.0 {
        "PASS"
    } else if score >= 60.0 {
        "WATCH"
    } else {
        "BLOCKED"
    };
    let conflicts = vec![
        json_obj(vec![
            ("id", "C1.crontab_vs_launchd".into()),
            (
                "doc_suggests",
                "crontab 定时运行 openclaw doctor/asset aggregate/sync scripts".into(),
            ),
            (
                "local_policy",
                "SOUL #9: 定期任务首选 Rust binary + launchd，Hermes cron 仅临时调试".into(),
            ),
            (
                "recommendation",
                "采用 launchd/Rust；不按文档新增 crontab".into(),
            ),
            ("needs_user", "如你坚持兼容 crontab，请裁决".into()),
        ]),
        json_obj(vec![
            ("id", "C2.cloud_memory_sync".into()),
            (
                "doc_suggests",
                "飞书知识库作为记忆中枢自动同步/检索优先".into(),
            ),
            (
                "local_policy",
                "当前只允许脱敏治理包外发；MEMORY/USER/案件/config/密钥不自动外发".into(),
            ),
            (
                "recommendation",
                "维持 explicit-target sanitized sync；全量云同步需你裁决".into(),
            ),
        ]),
        json_obj(vec![
            ("id", "C3.auto_cleanup_asset_move".into()),
            (
                "doc_suggests",
                "自动去重、无效文件清理、资产移动与标准化封装".into(),
            ),
            (
                "local_policy",
                "文件删除/移动必须 allowlist+backup+readback；不自动清理用户可能主动保留的资产"
                    .into(),
            ),
            (
                "recommendation",
                "先只读索引/候选清单；删除移动另行裁决".into(),
            ),
        ]),
        json_obj(vec![
            ("id", "C4.openclaw_path_commands".into()),
            (
                "doc_suggests",
                "/root/.openclaw、Linux syslog、crontab、openclaw CLI".into(),
            ),
            (
                "local_policy",
                "本机是 macOS/Hermes/PGG，路径和调度体系不同".into(),
            ),
            (
                "recommendation",
                "全部映射到 ~/.hermes、launchd、pgg-* gate；不创建 /root/.openclaw".into(),
            ),
        ]),
    ];
    let report = Report {
        schema: "pgg_feishu_ops_triptych_gate/v1",
        generated_at: Local::now().to_rfc3339(),
        source_doc_token: "sha256:0eece2d8c977b43f2c80a0b1e738e098d82f8ff5a722e4d35b7009ce94390a74",
        source_doc_title: "数字员工运维体系汇编第二阶段：巡检·整理·诊断三部曲",
        overall_status: overall.into(),
        score,
        checks,
        conflicts_require_user_adjudication: conflicts,
        boundary: vec![
            "read-only gate",
            "no cron creation",
            "no credential/config/provider mutation",
            "no file deletion/move",
            "no MEMORY/USER raw sync",
            "not AGI/T5/external benchmark proof",
        ],
    };
    println!("{}", serde_json::to_string_pretty(&report).unwrap());
}
