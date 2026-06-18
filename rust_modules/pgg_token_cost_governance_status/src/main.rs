use serde::Serialize;
use sha2::{Digest, Sha256};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Clone, Serialize)]
struct ComponentStatus {
    name: String,
    lane: String,
    status: String,
    mode: String,
    evidence_path: Option<String>,
    command: Option<String>,
    evidence_sha256: Option<String>,
    summary: String,
    legal_no_compress_covered: bool,
    production_mutates_prompt_or_tool_output: bool,
    provider_called_by_gate: bool,
    watch_items: Vec<String>,
    blocked_items: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
struct LegalNoCompressPolicy {
    status: String,
    rule: String,
    enforced_by: Vec<String>,
    keywords: Vec<String>,
    boundary: String,
}

#[derive(Debug, Clone, Serialize)]
struct TokenCostGovernanceReport {
    schema: String,
    version: String,
    generated_at_unix: i64,
    generated_at_iso: String,
    status: String,
    score: i64,
    pass_count: usize,
    watch_count: usize,
    blocked_count: usize,
    components: Vec<ComponentStatus>,
    legal_no_compress_policy: LegalNoCompressPolicy,
    active_boundaries: Vec<String>,
    recommended_next_actions: Vec<String>,
    output_path: String,
    ledger_path: String,
}

fn home_dir() -> PathBuf {
    PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}

fn hermes_home() -> PathBuf {
    home_dir().join(".hermes")
}

fn data_dir() -> PathBuf {
    hermes_home().join("data/token_cost_governance")
}

fn output_path() -> PathBuf {
    data_dir().join("latest.json")
}

fn ledger_path() -> PathBuf {
    data_dir().join("ledger.jsonl")
}

fn iso_timestamp() -> String {
    Command::new("date")
        .arg("+%Y-%m-%dT%H:%M:%S%z")
        .output()
        .ok()
        .and_then(|o| {
            if o.status.success() {
                String::from_utf8(o.stdout).ok()
            } else {
                None
            }
        })
        .unwrap_or_else(|| "unknown".to_string())
        .trim()
        .to_string()
}

fn unix_timestamp() -> i64 {
    Command::new("date")
        .arg("+%s")
        .output()
        .ok()
        .and_then(|o| {
            if o.status.success() {
                String::from_utf8(o.stdout).ok()
            } else {
                None
            }
        })
        .and_then(|s| s.trim().parse::<i64>().ok())
        .unwrap_or(0)
}

fn sha256_hex_bytes(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    digest.iter().map(|b| format!("{:02x}", b)).collect()
}

fn sha256_file(path: &Path) -> Option<String> {
    fs::read(path).ok().map(|bytes| sha256_hex_bytes(&bytes))
}

fn run_command_capture(command: &str, args: &[&str]) -> Option<String> {
    let output = Command::new(command).args(args).output().ok()?;
    let mut joined = Vec::new();
    joined.extend_from_slice(&output.stdout);
    joined.extend_from_slice(&output.stderr);
    Some(String::from_utf8_lossy(&joined).to_string())
}

fn parse_json_status(text: &str) -> Option<String> {
    let v: serde_json::Value = serde_json::from_str(text).ok()?;
    v.get("status")
        .or_else(|| v.get("schema"))
        .and_then(|s| s.as_str())
        .map(|s| s.to_string())
}

fn file_component(
    name: &str,
    lane: &str,
    path: PathBuf,
    summary: &str,
    legal_no_compress_covered: bool,
) -> ComponentStatus {
    let exists = path.exists();
    let evidence_sha256 = if exists { sha256_file(&path) } else { None };
    let status = if exists {
        "PASS_REFERENCE_PRESENT"
    } else {
        "BLOCKED_REFERENCE_MISSING"
    };
    ComponentStatus {
        name: name.to_string(),
        lane: lane.to_string(),
        status: status.to_string(),
        mode: "procedural_reference_readback".to_string(),
        evidence_path: Some(path.to_string_lossy().to_string()),
        command: None,
        evidence_sha256,
        summary: summary.to_string(),
        legal_no_compress_covered,
        production_mutates_prompt_or_tool_output: false,
        provider_called_by_gate: false,
        watch_items: Vec::new(),
        blocked_items: if exists {
            Vec::new()
        } else {
            vec!["reference file missing".to_string()]
        },
    }
}

fn json_file_status_component(
    name: &str,
    lane: &str,
    path: PathBuf,
    expected_status: Option<&str>,
    summary: &str,
    legal_no_compress_covered: bool,
) -> ComponentStatus {
    let exists = path.exists();
    let text = if exists {
        fs::read_to_string(&path).unwrap_or_default()
    } else {
        String::new()
    };
    let parsed_status = if exists {
        parse_json_status(&text)
    } else {
        None
    };
    let mut status = parsed_status
        .clone()
        .unwrap_or_else(|| "BLOCKED_EVIDENCE_MISSING_OR_INVALID".to_string());
    let mut watch_items = Vec::new();
    let mut blocked_items = Vec::new();
    if !exists {
        blocked_items.push("evidence file missing".to_string());
    } else if parsed_status.is_none() {
        blocked_items.push("evidence JSON has no status/schema".to_string());
    } else if let Some(expected) = expected_status {
        if status != expected {
            watch_items.push(format!("expected status {}, got {}", expected, status));
            if !status.starts_with("WATCH") && !status.contains("WATCH") {
                status = format!("WATCH_STATUS_DRIFT_{}", status);
            }
        }
    }
    ComponentStatus {
        name: name.to_string(),
        lane: lane.to_string(),
        status,
        mode: "read_only_file_evidence".to_string(),
        evidence_path: Some(path.to_string_lossy().to_string()),
        command: None,
        evidence_sha256: if exists { sha256_file(&path) } else { None },
        summary: summary.to_string(),
        legal_no_compress_covered,
        production_mutates_prompt_or_tool_output: false,
        provider_called_by_gate: false,
        watch_items,
        blocked_items,
    }
}

fn command_component(
    name: &str,
    lane: &str,
    command: &str,
    args: &[&str],
    expected_status_hint: Option<&str>,
    mode: &str,
    summary: &str,
) -> ComponentStatus {
    let output = run_command_capture(command, args);
    let evidence_sha256 = output.as_ref().map(|s| sha256_hex_bytes(s.as_bytes()));
    let mut status = "BLOCKED_COMMAND_FAILED".to_string();
    let mut watch_items = Vec::new();
    let mut blocked_items = Vec::new();
    match output {
        Some(ref text) => {
            let parsed = parse_json_status(text).unwrap_or_else(|| {
                if text.contains("PASS") {
                    "PASS_TEXT_OUTPUT".to_string()
                } else if text.contains("WATCH") {
                    "WATCH_TEXT_OUTPUT".to_string()
                } else {
                    "WATCH_UNSTRUCTURED_OUTPUT".to_string()
                }
            });
            status = parsed;
            if let Some(expected) = expected_status_hint {
                if !status.contains(expected) && status != expected {
                    watch_items.push(format!("expected hint {}, got {}", expected, status));
                }
            }
        }
        None => blocked_items.push(format!("failed to execute {}", command)),
    }
    ComponentStatus {
        name: name.to_string(),
        lane: lane.to_string(),
        status,
        mode: mode.to_string(),
        evidence_path: None,
        command: Some(format!("{} {}", command, args.join(" "))),
        evidence_sha256,
        summary: summary.to_string(),
        legal_no_compress_covered: false,
        production_mutates_prompt_or_tool_output: false,
        provider_called_by_gate: false,
        watch_items,
        blocked_items,
    }
}

fn reasonix_cache_postcheck_component() -> ComponentStatus {
    let latest_path = hermes_home().join(
        "workspace/pgg-archon-governance/reasonix-cache-github-20260607/pgg_reasonix_cache_audit_latest.json",
    );
    let legacy_path = hermes_home().join("data/reasonix_cache_postcheck_ledger.jsonl");
    let evidence_path = if latest_path.exists() {
        latest_path
    } else {
        legacy_path
    };
    let exists = evidence_path.exists();
    let text = if exists {
        fs::read_to_string(&evidence_path).unwrap_or_default()
    } else {
        String::new()
    };
    let parsed_status = parse_json_status(&text);
    let cache_guard_skipped = text.contains("SKIPPED_CACHE_GUARD_USE_RUN_CACHE_GUARD");
    let hermes_surface_present = text.contains("HERMES_HAS_SESSION_CACHE_TOKEN_SURFACE");

    let mut watch_items = Vec::new();
    let mut blocked_items = Vec::new();
    let status = if !exists {
        blocked_items.push("Reasonix cache audit evidence missing".to_string());
        "BLOCKED_REASONIX_CACHE_AUDIT_EVIDENCE_MISSING".to_string()
    } else if let Some(s) = parsed_status {
        if s.starts_with("PASS") && hermes_surface_present {
            "PASS_REASONIX_CACHE_AUDIT_READONLY_SURFACE".to_string()
        } else if s.starts_with("PASS") && cache_guard_skipped {
            watch_items.push(
                "cache guard skipped and Hermes cache surface not proven in evidence".to_string(),
            );
            "WATCH_REASONIX_CACHE_AUDIT_GUARD_SKIPPED".to_string()
        } else if s.starts_with("WATCH") {
            watch_items.push(format!("latest Reasonix audit is still {}", s));
            "WATCH_REASONIX_CACHE_GOVERNANCE_POSTCHECK_PARTIAL".to_string()
        } else {
            watch_items.push(format!("unexpected Reasonix audit status {}", s));
            format!("WATCH_REASONIX_CACHE_AUDIT_STATUS_DRIFT_{}", s)
        }
    } else {
        blocked_items.push("Reasonix evidence exists but status is not parseable JSON".to_string());
        "BLOCKED_REASONIX_CACHE_AUDIT_JSON_INVALID".to_string()
    };

    ComponentStatus {
        name: "Reasonix cache postcheck".to_string(),
        lane: "reasonix_cache_learning_replay_ledger".to_string(),
        status,
        mode: "latest_readonly_audit_readback".to_string(),
        evidence_path: Some(evidence_path.to_string_lossy().to_string()),
        command: Some("/Users/appleoppa/.hermes/bin/pgg_reasonix_cache_audit --json --write-ledger".to_string()),
        evidence_sha256: if exists { sha256_file(&evidence_path) } else { None },
        summary: "Reasonix cache learning is now judged from the latest read-only audit evidence. PASS means Hermes cache-token surfaces are present and no provider/core mutation was performed; skipped upstream cache-guard remains a boundary, not a blocker.".to_string(),
        legal_no_compress_covered: true,
        production_mutates_prompt_or_tool_output: false,
        provider_called_by_gate: false,
        watch_items,
        blocked_items,
    }
}

fn manifest_component() -> ComponentStatus {
    let path = hermes_home().join("data/EVOLUTION_MANIFEST.json");
    let text = fs::read_to_string(&path).unwrap_or_default();
    let required = [
        "latest_super_evolution_6_token_hygiene_core_fusion_20260606",
        "latest_claude_proxy_prompt_cache_fix_core_fusion_20260615",
        "latest_headroom_shadow_compression_legal_no_compress_20260618",
    ];
    let missing: Vec<String> = required
        .iter()
        .filter(|k| !text.contains(**k))
        .map(|k| k.to_string())
        .collect();
    let status = if missing.is_empty() {
        "PASS_MANIFEST_KEYS_PRESENT"
    } else {
        "WATCH_MANIFEST_KEYS_MISSING"
    };
    ComponentStatus {
        name: "Manifest token/cache settlement keys".to_string(),
        lane: "manifest_readback".to_string(),
        status: status.to_string(),
        mode: "read_only_manifest_scan".to_string(),
        evidence_path: Some(path.to_string_lossy().to_string()),
        command: None,
        evidence_sha256: sha256_file(&path),
        summary: format!(
            "Required keys checked: {}; missing: {}",
            required.join(", "),
            if missing.is_empty() {
                "none".to_string()
            } else {
                missing.join(", ")
            }
        ),
        legal_no_compress_covered: true,
        production_mutates_prompt_or_tool_output: false,
        provider_called_by_gate: false,
        watch_items: if missing.is_empty() {
            Vec::new()
        } else {
            missing.clone()
        },
        blocked_items: Vec::new(),
    }
}

fn build_components() -> Vec<ComponentStatus> {
    let h = hermes_home();
    vec![
        json_file_status_component(
            "Headroom-style reversible shadow compression + legal no-compress",
            "tool_output_shadow_compression",
            h.join("data/headroom_absorption/latest.json"),
            Some("PASS_SHADOW_ABSORBED"),
            "Mechanism-only Rust shadow gate; estimates savings for logs/json/code and hard-bypasses legal case/evidence/doc payloads.",
            true,
        ),
        command_component(
            "Super Evolution 6 token hygiene deterministic gate",
            "token_hygiene_runtime_ledger_governance",
            "/Users/appleoppa/.hermes/bin/pgg-apex-token-gate",
            &[],
            Some("PGGApexTokenGateStatus"),
            "local_gate_observe_only",
            "Local deterministic token gate surface; complements SE6 Rust/PyO3 token hygiene and tool ledger governance.",
        ),
        command_component(
            "OmniRoute UI/provider probe status",
            "routing_probe_cost_governance",
            "/Users/appleoppa/.hermes/bin/omniroute_ui_status",
            &[],
            Some("PASS"),
            "guarded_runtime_status_no_scheduler_security_mutation",
            "Current OmniRoute status including provider probe gate and guarded production boundaries.",
        ),
        command_component(
            "OmniRoute six-provider probe gate",
            "provider_probe_gate",
            "/Users/appleoppa/.hermes/bin/pgg_omniroute_provider_probe_gate",
            &[],
            Some("PASS"),
            "bounded_gate_existing_ledger_readback",
            "Six-provider bounded probe gate; used as evidence for routing/probe-cost governance, not for enabling new provider calls here.",
        ),
        command_component(
            "Provider cost profile",
            "provider_cost_profile",
            "/Users/appleoppa/.hermes/bin/pgg_provider_cost_profile",
            &[],
            Some("pgg-provider-cost-profile"),
            "rust_shadow_cost_profile",
            "General8 Rust provider cost profile: K_res + ΔC_inf resource/cost model, shadow only.",
        ),
        reasonix_cache_postcheck_component(),
        file_component(
            "Hermes LLM provider cache optimization skill",
            "prompt_cache_architecture",
            h.join("skills/hermes/hermes-llm-cache-optimization/SKILL.md"),
            "Provider APC/cache_control/prompt_cache_key architecture, bridge processor cache fix, system prompt layering, probe-to-TCP transition.",
            false,
        ),
        file_component(
            "Token hygiene umbrella skill reference",
            "skill_governance_reference",
            h.join("skills/workflow/token-hygiene-super-evolution-6/SKILL.md"),
            "Umbrella skill now includes Headroom legal no-compress rule and SE6 runtime ledger governance.",
            true,
        ),
        manifest_component(),
    ]
}

fn is_pass(status: &str) -> bool {
    status.starts_with("PASS")
        || status.ends_with("/v1")
        || status == "pgg-provider-cost-profile/v1"
}

fn is_watch(status: &str) -> bool {
    status.starts_with("WATCH") || status.contains("WATCH") || status.contains("PARTIAL")
}

fn build_legal_policy(components: &[ComponentStatus]) -> LegalNoCompressPolicy {
    let covered = components
        .iter()
        .any(|c| c.legal_no_compress_covered && is_pass(&c.status));
    LegalNoCompressPolicy {
        status: if covered {
            "PASS_LEGAL_NO_COMPRESS_COVERED_BY_HEADROOM_AND_SKILL".to_string()
        } else {
            "BLOCKED_LEGAL_NO_COMPRESS_NOT_COVERED".to_string()
        },
        rule: "Legal casework, evidence, client facts, pleadings, judgments, contracts, CMS/trusted workflow payloads must bypass automatic compression; only metadata hash/index is allowed.".to_string(),
        enforced_by: vec!["pgg_headroom_absorption_gate".to_string(), "token-hygiene-super-evolution-6 skill reference".to_string()],
        keywords: vec![
            "法律办案", "案件", "案号", "当事人", "证据", "举证", "质证", "诉状", "判决书", "合同", "管辖", "法院", "律师", "客户", "cms_case", "legal_case", "evidence", "legal_doc", "case_file", "trusted_workflow",
        ].into_iter().map(|s| s.to_string()).collect(),
        boundary: "This unified gate does not compress, mutate, route, call providers, or replace legal originals. It only reads evidence and reports governance status.".to_string(),
    }
}

fn build_report() -> TokenCostGovernanceReport {
    let components = build_components();
    let legal_policy = build_legal_policy(&components);
    let blocked_count = components
        .iter()
        .filter(|c| !c.blocked_items.is_empty() || c.status.starts_with("BLOCKED"))
        .count()
        + if legal_policy.status.starts_with("BLOCKED") {
            1
        } else {
            0
        };
    let watch_count = components
        .iter()
        .filter(|c| {
            c.blocked_items.is_empty() && (is_watch(&c.status) || !c.watch_items.is_empty())
        })
        .count();
    let pass_count = components.len().saturating_sub(blocked_count + watch_count);
    let status = if blocked_count > 0 {
        "BLOCKED"
    } else if watch_count > 0 {
        "WATCH"
    } else {
        "PASS"
    };
    let score = (100_i64 - (watch_count as i64 * 8) - (blocked_count as i64 * 18)).max(0);
    TokenCostGovernanceReport {
        schema: "PGGTokenCostGovernanceStatus/v1".to_string(),
        version: "0.1.0".to_string(),
        generated_at_unix: unix_timestamp(),
        generated_at_iso: iso_timestamp(),
        status: status.to_string(),
        score,
        pass_count,
        watch_count,
        blocked_count,
        components,
        legal_no_compress_policy: legal_policy,
        active_boundaries: vec![
            "Read-only aggregation gate; no provider calls initiated by this binary except existing local status CLIs.".to_string(),
            "Headroom and OmniRoute compression remain shadow/advisory unless separately promoted by explicit gate and authorization.".to_string(),
            "Legal case materials/evidence/docs are no-compress regardless of estimated token savings.".to_string(),
            "PASS here is local governance/readback status, not external benchmark, legal correctness proof, or AGI level claim.".to_string(),
        ],
        recommended_next_actions: vec![
            "Promote this status binary into daily launchd LIGHT after one clean manual run if desired.".to_string(),
            "Extract legal no-compress policy into a shared Rust policy crate before enabling any runtime compression path.".to_string(),
            "Add real provider usage parsers for cache hit ratios where usage ledgers expose cache_read/cache_hit fields.".to_string(),
        ],
        output_path: output_path().to_string_lossy().to_string(),
        ledger_path: ledger_path().to_string_lossy().to_string(),
    }
}

fn write_report(report: &TokenCostGovernanceReport) -> Result<(), Box<dyn std::error::Error>> {
    fs::create_dir_all(data_dir())?;
    let json = serde_json::to_string_pretty(report)?;
    fs::write(output_path(), &json)?;
    let mut ledger = OpenOptions::new()
        .create(true)
        .append(true)
        .open(ledger_path())?;
    writeln!(ledger, "{}", serde_json::to_string(report)?)?;
    println!("{}", json);
    Ok(())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let report = build_report();
    write_report(&report)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pass_watch_blocked_classification_is_stable() {
        assert!(is_pass("PASS_REFERENCE_PRESENT"));
        assert!(is_pass("PGGApexTokenGateStatus/v1"));
        assert!(is_watch(
            "WATCH_REASONIX_CACHE_GOVERNANCE_POSTCHECK_PARTIAL"
        ));
        assert!(!is_watch("PASS_REFERENCE_PRESENT"));
    }

    #[test]
    fn legal_policy_keywords_cover_chinese_and_runtime_terms() {
        let component = ComponentStatus {
            name: "x".into(),
            lane: "x".into(),
            status: "PASS_X".into(),
            mode: "x".into(),
            evidence_path: None,
            command: None,
            evidence_sha256: None,
            summary: "x".into(),
            legal_no_compress_covered: true,
            production_mutates_prompt_or_tool_output: false,
            provider_called_by_gate: false,
            watch_items: vec![],
            blocked_items: vec![],
        };
        let policy = build_legal_policy(&[component]);
        assert!(policy.status.starts_with("PASS"));
        assert!(policy.keywords.contains(&"证据".to_string()));
        assert!(policy.keywords.contains(&"trusted_workflow".to_string()));
    }

    #[test]
    fn score_penalizes_watch_without_blocking() {
        let report = build_report();
        assert_eq!(report.schema, "PGGTokenCostGovernanceStatus/v1");
        assert_eq!(report.blocked_count, 0);
        assert!(report.score >= 70);
        assert!(report
            .legal_no_compress_policy
            .rule
            .contains("bypass automatic compression"));
    }
}
