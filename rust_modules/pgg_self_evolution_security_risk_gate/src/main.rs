use chrono::{Local, SecondsFormat};
use serde_json::json;
use std::{env, fs, path::{Path, PathBuf}};

fn home() -> PathBuf { PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string())) }
fn read(p: &Path) -> String { fs::read_to_string(p).unwrap_or_default() }
fn exists(p: &Path) -> bool { p.exists() }
fn has_any(s: &str, needles: &[&str]) -> bool { needles.iter().any(|n| s.contains(n)) }

fn main() {
    let h = home();
    let hermes = h.join(".hermes");
    let agent = hermes.join("hermes-agent");
    let raw = hermes.join("workspace/pgg-archon-governance/feishu-doc-comparison-20260618-JcvO/【T0-学习文档-迭代进化】Hermes自进化暗面-四大结构性安全风险与根治方案.raw.md");
    let report = hermes.join("workspace/pgg-archon-governance/feishu-doc-comparison-20260618-JcvO/LOCAL_COMPARISON_REPORT.md");
    let conflict = hermes.join("workspace/pgg-archon-governance/feishu-doc-comparison-20260618-JcvO/CONFLICT_DECISION_PACKET.md");
    let reference = hermes.join("skills/general/agent-operational-governance/references/feishu-self-evolution-darkside-security-risk-20260618.md");
    let gov = hermes.join("skills/general/agent-operational-governance/SKILL.md");
    let eng_gate = hermes.join("bin/pgg-engineering-discipline-gate");
    let claw = hermes.join("skills/clawdefender-1/clawdefender/SKILL.md");
    let skill_vetter = hermes.join("skills/skill-vetter/SKILL.md");
    let auth_cfg = hermes.join("config.yaml");
    let cargo = agent.join("rust_modules/Cargo.toml");
    let raw_txt = read(&raw);
    let gov_txt = read(&gov);
    let ref_txt = read(&reference);
    let cfg_txt = read(&auth_cfg);
    let cargo_txt = read(&cargo);

    let checks: Vec<(&str, bool, i64)> = vec![
        ("source_raw_present", exists(&raw) && raw_txt.contains("四大结构性安全风险"), 8),
        ("comparison_report_present", exists(&report), 8),
        ("conflict_packet_present", exists(&conflict), 8),
        ("governance_reference_present", exists(&reference) && ref_txt.contains("自进化暗面"), 10),
        ("filesystem_symlink_risk_tracked", has_any(&ref_txt, &["符号链接", "文件系统逃逸", "symlink"]), 8),
        ("jwt_auth_risk_tracked", has_any(&ref_txt, &["JWT", "认证绕过", "auth"]), 8),
        ("skill_supply_chain_risk_tracked", has_any(&ref_txt, &["技能供应链", "skill supply", "恶意技能"]), 10),
        ("multimodal_parser_risk_tracked", has_any(&ref_txt, &["多模态", "解析漏洞", "图片", "视频"]), 8),
        ("existing_skill_security_vetter", exists(&skill_vetter) || exists(&claw), 8),
        ("operational_governance_security_boundary", has_any(&gov_txt, &["安全", "credential", "provider/config/scheduler/security", "no fabrication"]), 8),
        ("engineering_gate_present", exists(&eng_gate), 6),
        ("no_runtime_policy_mutation_claimed", ref_txt.contains("不直接改") || ref_txt.contains("只读"), 8),
        ("workspace_member_present", cargo_txt.contains("pgg_self_evolution_security_risk_gate"), 10),
        ("config_exists_but_not_modified_by_gate", exists(&auth_cfg) && !cfg_txt.is_empty(), 4),
    ];
    let score: i64 = checks.iter().filter(|(_, ok, _)| *ok).map(|(_, _, w)| *w).sum();
    let status = if score >= 86 { "PASS_SELF_EVOLUTION_SECURITY_RISK_ADVISORY_READY" } else if score >= 65 { "WATCH_SELF_EVOLUTION_SECURITY_RISK_PARTIAL" } else { "BLOCKED_SELF_EVOLUTION_SECURITY_RISK_MISSING" };
    let result = json!({
        "schema":"pgg-self-evolution-security-risk-gate/v1",
        "generated_at": Local::now().to_rfc3339_opts(SecondsFormat::Secs, true),
        "status": status,
        "score": score,
        "mode":"read_only_advisory",
        "checks": checks.iter().map(|(n, ok, w)| json!({"name":n,"pass":ok,"weight":w})).collect::<Vec<_>>(),
        "risk_classes":["filesystem_symlink_escape","jwt_auth_bypass","skill_supply_chain_poisoning","multimodal_parser_vulnerability"],
        "conflicts_reserved_for_user":["Hard Approval default", "MicroVM default", "Close non-core egress", "Guardrail Model default", "P0/P1 hard rules"],
        "boundary":["read-only scoring", "no scheduler mutation", "no network policy mutation", "no provider/config mutation", "no MicroVM enablement", "no production-chain replacement"],
        "artifacts":{"raw":raw,"comparison":report,"conflict_packet":conflict,"reference":reference}
    });
    let out_dir = hermes.join("workspace/pgg-archon-governance/self-evolution-security-risk-gate");
    fs::create_dir_all(&out_dir).ok();
    let stamp = Local::now().format("%Y%m%d-%H%M%S").to_string();
    let jp = out_dir.join(format!("self-evolution-security-risk-{stamp}.json"));
    let body = serde_json::to_string_pretty(&result).unwrap();
    fs::write(&jp, &body).unwrap();
    fs::write(out_dir.join("latest.json"), &body).unwrap();
    println!("{}", serde_json::to_string(&json!({"ok":true,"status":status,"score":score,"json":jp,"latest":out_dir.join("latest.json")})).unwrap());
}
