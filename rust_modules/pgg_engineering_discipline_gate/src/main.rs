use chrono::{Local, SecondsFormat};
use serde_json::json;
use std::{
    env, fs,
    path::{Path, PathBuf},
};

fn home() -> PathBuf {
    PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}
fn exists(p: &Path) -> bool {
    p.exists()
}
fn read(p: &Path) -> String {
    fs::read_to_string(p).unwrap_or_default()
}
fn has_any(s: &str, needles: &[&str]) -> bool {
    needles.iter().any(|n| s.contains(n))
}

fn main() {
    let h = home();
    let hermes = h.join(".hermes");
    let agent = hermes.join("hermes-agent");
    let gov = hermes.join("skills/general/agent-operational-governance/SKILL.md");
    let report = hermes.join("workspace/pgg-archon-governance/feishu-doc-comparison-20260618-CwbG/LOCAL_COMPARISON_REPORT.md");
    let conflict = hermes.join("workspace/pgg-archon-governance/feishu-doc-comparison-20260618-CwbG/CONFLICT_DECISION_PACKET.md");
    let refp = hermes.join("skills/general/agent-operational-governance/references/feishu-engineering-discipline-absorption-20260618.md");
    let prd_gate = hermes.join("bin/pgg-prd-quality-gate");
    let agents = agent.join("AGENTS.md");
    let cargo = agent.join("rust_modules/Cargo.toml");
    let gov_txt = read(&gov);
    let agents_txt = read(&agents);
    let ref_txt = read(&refp);

    let checks: Vec<(&str, bool, i64)> = vec![
        ("source_report_present", exists(&report), 8),
        ("conflict_packet_present", exists(&conflict), 8),
        (
            "governance_reference_present",
            exists(&refp) && ref_txt.contains("工程纪律"),
            10,
        ),
        (
            "skill_first_rule_present",
            gov_txt.contains("先查") || gov_txt.contains("Local-resource-first"),
            8,
        ),
        ("spec_or_prd_gate_present", exists(&prd_gate), 10),
        (
            "backup_rule_present",
            gov_txt.contains("备份") || gov_txt.contains("backup"),
            8,
        ),
        (
            "test_verification_rule_present",
            has_any(&gov_txt, &["测试", "verify", "验证", "TDD"]),
            10,
        ),
        (
            "cleanup_rule_present",
            has_any(&gov_txt, &["清理", "cleanup", "workspace", "打扫"]),
            6,
        ),
        (
            "skill_settle_rule_present",
            has_any(&gov_txt, &["skill_manage", "沉淀", "reference"]),
            8,
        ),
        (
            "three_quality_layers_present",
            has_any(&ref_txt, &["语法/风格", "静态类型", "测试"]),
            8,
        ),
        (
            "rust_workspace_member_present",
            read(&cargo).contains("pgg_engineering_discipline_gate"),
            8,
        ),
        (
            "agents_partial_coverage_present",
            has_any(&agents_txt, &["lint", "test", "backup"]),
            6,
        ),
    ];
    let score: i64 = checks
        .iter()
        .filter(|(_, ok, _)| *ok)
        .map(|(_, _, w)| *w)
        .sum();
    let status = if score >= 85 {
        "PASS_ENGINEERING_DISCIPLINE_LOCAL_READY"
    } else if score >= 65 {
        "WATCH_ENGINEERING_DISCIPLINE_PARTIAL"
    } else {
        "BLOCKED_ENGINEERING_DISCIPLINE_MISSING"
    };
    let result = json!({
        "schema":"pgg-engineering-discipline-gate/v1",
        "generated_at": Local::now().to_rfc3339_opts(SecondsFormat::Secs,true),
        "status": status,
        "score": score,
        "checks": checks.iter().map(|(n,ok,w)| json!({"name":n,"pass":ok,"weight":w})).collect::<Vec<_>>(),
        "decisions_pending_user_adjudication":[
            "C1 append AGENTS.md hard enforcement",
            "C2 >50 lines hard Spec requirement",
            "C3 >3 files mandatory split",
            "C4 immediate atomic commit after every success",
            "C5 120-line hard limit",
            "C6 automatic temp deletion",
            "C7 automatic create-skill vs patch existing reference"
        ],
        "boundary":[
            "read-only scoring",
            "no AGENTS.md mutation",
            "no git commit/push",
            "no file deletion",
            "thresholds are WATCH/advisory unless user adjudicates otherwise"
        ],
        "artifacts": {"report":report,"conflict_packet":conflict,"reference":refp}
    });
    let out_dir = hermes.join("workspace/pgg-archon-governance/engineering-discipline-gate");
    fs::create_dir_all(&out_dir).ok();
    let stamp = Local::now().format("%Y%m%d-%H%M%S").to_string();
    let jp = out_dir.join(format!("engineering-discipline-{stamp}.json"));
    fs::write(&jp, serde_json::to_string_pretty(&result).unwrap()).unwrap();
    fs::write(
        out_dir.join("latest.json"),
        serde_json::to_string_pretty(&result).unwrap(),
    )
    .unwrap();
    println!("{}", serde_json::to_string(&json!({"ok":true,"status":status,"score":score,"json":jp,"latest":out_dir.join("latest.json")})).unwrap());
}
