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
    let receipt = hermes.join("workspace/pgg-archon-governance/email-memory-sync-20260618-091859/email_send_receipt.json");
    let sync_pkg = hermes.join("workspace/pgg-archon-governance/email-memory-sync-20260618-091859/pgg-memory-governance-email-sync-20260618-091859.zip");
    let config = h.join(".config/himalaya/config.toml");
    let refp = hermes.join("skills/email/himalaya/references/feishu-email-sync-governance-20260618.md");
    let gov = hermes.join("skills/general/agent-operational-governance/SKILL.md");
    let cargo = agent.join("rust_modules/Cargo.toml");
    let gov_txt = read(&gov);
    let ref_txt = read(&refp);
    let receipt_txt = read(&receipt);

    let checks: Vec<(&str, bool, i64)> = vec![
        ("receipt_present", exists(&receipt) && receipt_txt.contains("PASS_SENT_SMTP_SSL"), 12),
        ("sync_package_present", exists(&sync_pkg) && sync_pkg.metadata().map(|m| m.len()).unwrap_or(0) < 50_000, 10),
        ("himalaya_config_present", exists(&config), 8),
        ("governance_reference_present", exists(&refp) && ref_txt.contains("邮箱同步"), 10),
        ("no_periodic_scheduler_claim", has_any(&ref_txt, &["一次性", "不自动", "不新增", "单次"]), 10),
        ("no_secret_in_reference", !has_any(&ref_txt, &["ycbtjizqkmdycbef", "61079425@qq.com密码"]), 8),
        ("email_boundary_present", has_any(&gov_txt, &["外部邮件", "readback", "Boundary"]), 6),
        ("rust_workspace_member_present", read(&cargo).contains("pgg_email_sync_governance_gate"), 10),
        ("existing_keychain_used", receipt_txt.contains("macOS_keychain:hermes-qq-mail-smtp"), 8),
        ("no_memory_user_raw", receipt_txt.contains("no MEMORY_USER raw"), 8),
    ];
    let score: i64 = checks.iter().filter(|(_, ok, _)| *ok).map(|(_, _, w)| *w).sum();
    let status = if score >= 80 { "PASS_EMAIL_SYNC_GOVERNANCE_READY" } else if score >= 60 { "WATCH_EMAIL_SYNC_PARTIAL" } else { "BLOCKED_EMAIL_SYNC_MISSING" };
    let result = json!({
        "schema":"pgg-email-sync-governance-gate/v1",
        "generated_at": Local::now().to_rfc3339_opts(SecondsFormat::Secs, true),
        "status": status,
        "score": score,
        "mode":"read_only_advisory",
        "checks": checks.iter().map(|(n, ok, w)| json!({"name":n,"pass":ok,"weight":w})).collect::<Vec<_>>(),
        "boundary":["read-only scoring", "single-shot external-send only", "no periodic scheduler", "no secret printing", "no MEMORY/USER raw", "no cases/config write"],
        "artifacts":{"receipt":receipt,"sync_package":sync_pkg,"reference":refp}
    });
    let out_dir = hermes.join("workspace/pgg-archon-governance/email-sync-governance-gate");
    fs::create_dir_all(&out_dir).ok();
    let stamp = Local::now().format("%Y%m%d-%H%M%S").to_string();
    let jp = out_dir.join(format!("email-sync-governance-{stamp}.json"));
    let body = serde_json::to_string_pretty(&result).unwrap();
    fs::write(&jp, &body).unwrap();
    fs::write(out_dir.join("latest.json"), &body).unwrap();
    println!("{}", serde_json::to_string(&json!({"ok":true,"status":status,"score":score,"json":jp,"latest":out_dir.join("latest.json")})).unwrap());
}
