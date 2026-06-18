use chrono::Local;
use serde::Serialize;
use serde_json::Value;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Serialize)]
struct Check {
    id: &'static str,
    title: &'static str,
    status: String,
    mapping: &'static str,
    evidence: Value,
    boundary: &'static str,
}
#[derive(Serialize)]
struct Report {
    schema: &'static str,
    generated_at: String,
    status: String,
    score: f64,
    source_doc: &'static str,
    mapping_note: &'static str,
    checks: Vec<Check>,
    adopted_recommendations: Vec<Value>,
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
            if s.len() > 1200 {
                s.truncate(1200);
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
fn count_files(root: &Path, pred: &dyn Fn(&Path) -> bool, max: usize) -> usize {
    fn walk(p: &Path, pred: &dyn Fn(&Path) -> bool, n: &mut usize, max: usize) {
        if *n >= max {
            return;
        }
        let rd = match fs::read_dir(p) {
            Ok(r) => r,
            Err(_) => return,
        };
        for e in rd.flatten() {
            let q = e.path();
            if q.is_dir() {
                let s = q.to_string_lossy();
                if s.contains("node_modules")
                    || s.contains("/.git")
                    || s.contains("/target")
                    || s.contains("/.venv")
                    || s.contains("/venv")
                {
                    continue;
                }
                walk(&q, pred, n, max);
            } else if pred(&q) {
                *n += 1;
                if *n >= max {
                    return;
                }
            }
        }
    }
    let mut n = 0;
    walk(root, pred, &mut n, max);
    n
}
fn main() {
    let h = home();
    let hermes = h.join(".hermes");
    let agent = hermes.join("hermes-agent");
    let bin = hermes.join("bin");
    let skills = hermes.join("skills");
    let mut checks = Vec::new();
    let skill_count = count_files(
        &skills,
        &|p| p.file_name().and_then(|s| s.to_str()) == Some("SKILL.md"),
        10000,
    );
    checks.push(Check {
        id: "script.skill_first",
        title: "脚本创建前 skill-first 评估",
        status: if skill_count > 50 {
            "COVERED".into()
        } else {
            "WATCH".into()
        },
        mapping: "文档 find-skills/openclaw → Hermes skill_view/skills_list + 已有 skill 架构",
        evidence: obj(vec![
            ("skills_root", skills.display().to_string().into()),
            ("skill_md_count", skill_count.into()),
        ]),
        boundary: "本 gate 只提示 skill-first；不自动删除/合并技能",
    });
    let pgg_bin = count_files(
        &bin,
        &|p| {
            p.file_name()
                .and_then(|s| s.to_str())
                .map(|x| x.starts_with("pgg-"))
                .unwrap_or(false)
        },
        10000,
    );
    checks.push(Check{id:"script.index",title:"脚本/CLI 索引",status:if pgg_bin>20{"PARTIAL_COVERED".into()}else{"WATCH".into()},mapping:"文档 scripts_lib/MANIFEST.yaml → Hermes ~/.hermes/bin + rust_modules/Cargo.toml + workspace reports",evidence:obj(vec![("bin",bin.display().to_string().into()),("pgg_cli_count",pgg_bin.into())]),boundary:"未创建独立 MANIFEST.yaml；以 Cargo workspace/CLI/skill reference 作索引"});
    let (goal_rc, goal_out) = run(bin.join("hermes-goal").to_str().unwrap_or(""), &[]);
    checks.push(Check{id:"selfcheck.e2e",title:"全链路自检",status:if goal_rc==0 && goal_out.contains("overall_status"){"COVERED".into()}else{"WATCH".into()},mapping:"文档 heartbeat/cron/debt/graph → Hermes hermes-goal + pgg-health-monitor + launchd gates",evidence:obj(vec![("exit",goal_rc.into()),("sample",goal_out.into())]),boundary:"hermes-goal 是本地状态面，不证明法律正确性/full AGI"});
    let (health_rc, health_out) = run(
        bin.join("pgg-health-monitor").to_str().unwrap_or(""),
        &["--json"],
    );
    checks.push(Check {
        id: "selfcheck.health",
        title: "健康/防空转/防幻觉状态",
        status: if health_rc == 0 && health_out.contains("PASS") {
            "COVERED".into()
        } else {
            "WATCH".into()
        },
        mapping: "文档 health_check.sh → Hermes pgg-health-monitor",
        evidence: obj(vec![
            ("exit", health_rc.into()),
            ("sample", health_out.into()),
        ]),
        boundary: "绿色健康不等于业务任务完成",
    });
    let (ws_rc, ws_out) = run(
        bin.join("pgg-workspace-candidate-report")
            .to_str()
            .unwrap_or(""),
        &[],
    );
    checks.push(Check {
        id: "script.cleanup",
        title: "清扫战场/候选清理",
        status: if ws_rc == 0 && ws_out.contains("PASS_READ_ONLY_CANDIDATES") {
            "COVERED".into()
        } else {
            "WATCH".into()
        },
        mapping: "文档清理临时文件 → Hermes 每日只读候选清单；删除/移动需 allowlist",
        evidence: obj(vec![("exit", ws_rc.into()), ("sample", ws_out.into())]),
        boundary: "只读候选，不自动删除移动",
    });
    let cargo = agent.join("rust_modules/Cargo.toml");
    let cargo_ok = cargo.exists()
        && fs::read_to_string(&cargo)
            .unwrap_or_default()
            .contains("pgg_ops_lifecycle_gate");
    checks.push(Check {
        id: "skill.lifecycle",
        title: "技能/模块生命周期",
        status: if cargo_ok {
            "PARTIAL_COVERED".into()
        } else {
            "WATCH".into()
        },
        mapping:
            "文档技能安装/测试/启用/退役 → Hermes skill governance + Rust workspace onboarding",
        evidence: obj(vec![
            ("cargo_workspace", cargo.display().to_string().into()),
            ("registered", cargo_ok.into()),
        ]),
        boundary: "技能删除/退役仍需引用扫描和授权",
    });
    let covered = checks.iter().filter(|c| c.status == "COVERED").count() as f64;
    let partial = checks
        .iter()
        .filter(|c| c.status.starts_with("PARTIAL"))
        .count() as f64;
    let score = ((covered + 0.5 * partial) / checks.len() as f64 * 1000.0).round() / 10.0;
    let status = if score >= 85.0 {
        "PASS"
    } else if score >= 80.0 {
        "PASS_WITH_BOUNDARIES"
    } else if score >= 60.0 {
        "WATCH"
    } else {
        "BLOCKED"
    }
    .to_string();
    let adopted = vec![
        obj(vec![
            ("id", "L1.openclaw_paths".into()),
            (
                "doc_suggests",
                "/root/.openclaw、scripts_lib、MANIFEST.yaml、openclaw 命令".into(),
            ),
            (
                "adopted_boundary",
                "只做 OpenClaw→Hermes 映射；不创建 /root/.openclaw；不照搬 openclaw CLI；不新增独立 scripts_lib 作为主索引".into(),
            ),
            ("decision", "ADOPT_ASSISTANT_RECOMMENDATION".into()),
        ]),
        obj(vec![
            ("id", "L2.cron_vs_launchd".into()),
            ("doc_suggests", "Cron/crontab/health_check.sh".into()),
            (
                "adopted_boundary",
                "维持 Rust binary + launchd + pgg-health-monitor；不新增 crontab".into(),
            ),
            ("decision", "ADOPT_ASSISTANT_RECOMMENDATION".into()),
        ]),
        obj(vec![
            ("id", "L3.auto_skill_install_retire".into()),
            ("doc_suggests", "技能安装、升级、退役自动化".into()),
            (
                "adopted_boundary",
                "默认只读评估；自动安装/删除/退役技能仍需引用扫描、备份、质量门禁和单独授权".into(),
            ),
            ("decision", "ADOPT_ASSISTANT_RECOMMENDATION".into()),
        ]),
        obj(vec![
            ("id", "L4.script_cleanup_delete".into()),
            ("doc_suggests", "清扫测试和临时文件".into()),
            (
                "adopted_boundary",
                "维持 pgg-workspace-candidate-report 只读候选；删除/移动必须 allowlist + backup + readback".into(),
            ),
            ("decision", "ADOPT_ASSISTANT_RECOMMENDATION".into()),
        ]),
    ];
    let report = Report {
        schema: "pgg_ops_lifecycle_gate/v1",
        generated_at: Local::now().to_rfc3339(),
        status,
        score,
        source_doc: "RoVi 脚本·自检·技能三部曲",
        mapping_note:
            "亦菲=外部智能体名；OpenClaw 映射为 Hermes/PGG，不照搬；用户已裁决采用苹果妹建议",
        checks,
        adopted_recommendations: adopted,
        conflicts_require_user_adjudication: Vec::new(),
        boundary: vec![
            "read-only",
            "OpenClaw→Hermes mapping only",
            "no crontab",
            "no auto skill deletion/install",
            "no file deletion/move",
            "no config/provider/credential mutation",
        ],
    };
    let out = hermes.join("workspace/pgg-archon-governance/ops-lifecycle-gate");
    let _ = fs::create_dir_all(&out);
    let json = serde_json::to_string_pretty(&report).unwrap();
    fs::write(out.join("latest.json"), &json).unwrap();
    println!("{}", json);
}
