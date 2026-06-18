use chrono::{DateTime, Duration, Local, SecondsFormat, Utc};
use serde_json::{json, Value};
use std::{
    collections::BTreeMap,
    env, fs,
    io::{BufRead, BufReader},
    path::{Path, PathBuf},
};

fn home() -> PathBuf {
    PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}
fn read_json(path: &Path) -> Option<Value> {
    fs::read_to_string(path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
}
fn parse_time(s: &str) -> Option<DateTime<Utc>> {
    DateTime::parse_from_rfc3339(s)
        .ok()
        .map(|d| d.with_timezone(&Utc))
}
fn read_subagents(h: &Path) -> Value {
    let index = h.join(".hermes/logs/subagents/index.jsonl");
    let now = Utc::now();
    let cutoff = now - Duration::hours(24);
    let mut total = 0usize;
    let mut last24 = 0usize;
    let mut completed = 0usize;
    let mut failed = 0usize;
    let mut timeout = 0usize;
    let mut interrupted = 0usize;
    let mut models: BTreeMap<String, usize> = BTreeMap::new();
    let mut model_completed: BTreeMap<String, usize> = BTreeMap::new();
    let mut evidence: BTreeMap<String, usize> = BTreeMap::new();
    let mut files_written = 0usize;
    let mut recent = Vec::new();
    if let Ok(f) = fs::File::open(&index) {
        for line in BufReader::new(f).lines().flatten() {
            if line.trim().is_empty() {
                continue;
            }
            total += 1;
            let Ok(v) = serde_json::from_str::<Value>(&line) else {
                continue;
            };
            let ts = v
                .get("recorded_at")
                .and_then(|x| x.as_str())
                .and_then(parse_time);
            if ts.map(|t| t >= cutoff).unwrap_or(false) {
                last24 += 1;
            }
            let st = v
                .get("status")
                .and_then(|x| x.as_str())
                .unwrap_or("unknown");
            match st {
                "completed" => completed += 1,
                "timeout" => timeout += 1,
                "interrupted" => interrupted += 1,
                "failed" | "error" => failed += 1,
                _ => {}
            }
            if let Some(m) = v.get("model").and_then(|x| x.as_str()) {
                *models.entry(m.to_string()).or_insert(0) += 1;
                if st == "completed" {
                    *model_completed.entry(m.to_string()).or_insert(0) += 1;
                }
            }
            if let Some(e) = v.get("evidence_level").and_then(|x| x.as_str()) {
                *evidence.entry(e.to_string()).or_insert(0) += 1;
            }
            files_written += v
                .get("files_written_count")
                .and_then(|x| x.as_u64())
                .unwrap_or(0) as usize;
            if recent.len() < 5 {
                recent.push(v);
            } else {
                recent.remove(0);
                recent.push(v);
            }
        }
    }
    let success_rate = if total > 0 {
        completed as f64 / total as f64
    } else {
        0.0
    };
    let mut model_stats: BTreeMap<String, Value> = BTreeMap::new();
    for (model, count) in models.iter() {
        let ok = *model_completed.get(model).unwrap_or(&0);
        let rate = if *count > 0 {
            ok as f64 / *count as f64
        } else {
            0.0
        };
        model_stats.insert(
            model.clone(),
            json!({"total":count,"completed":ok,"success_rate":rate}),
        );
    }
    json!({"source":index,"total":total,"last24":last24,"completed":completed,"failed":failed,"timeout":timeout,"interrupted":interrupted,"success_rate_all":success_rate,"models":models,"model_stats":model_stats,"evidence_levels":evidence,"files_written_count":files_written,"recent_sample_count":recent.len(),"recent":recent})
}
fn read_legal_ops(h: &Path) -> Value {
    let base = h.join(".hermes/workspace/pgg-archon-governance/legal-multiagent-ops");
    let d1 = read_json(&base.join("latest.json"));
    let q = read_json(&base.join("receipt-queue/latest.json"));
    let t = read_json(&base.join("receipt-packages/latest.json"));
    json!({"d1":d1,"queue":q,"templates":t})
}
fn read_provider_cost(h: &Path) -> Value {
    let p = h.join(".hermes/data/provider_cost_profile_latest.json");
    read_json(&p).unwrap_or_else(|| json!({"missing":true,"path":p}))
}

fn success_semantics() -> Value {
    json!({
        "decision": "PROVISIONAL_SUCCESS_ONLY",
        "rule": "low_risk_non_legal_non_system_tasks_may_be_marked_PROVISIONAL_SUCCESS_after_24h_no_objection",
        "excluded_lanes": ["legal", "security", "credential", "provider_config", "scheduler", "production_route", "memory_write", "github_merge"],
        "truth_boundary": "silence is never final success; no-feedback remains UNKNOWN unless this narrow provisional rule applies"
    })
}

fn shadow_dispatch(sub: &Value) -> Value {
    let mut rows: Vec<(String, f64, u64, u64)> = Vec::new();
    if let Some(obj) = sub.get("model_stats").and_then(|x| x.as_object()) {
        for (model, v) in obj {
            let rate = v
                .get("success_rate")
                .and_then(|x| x.as_f64())
                .unwrap_or(0.0);
            let total = v.get("total").and_then(|x| x.as_u64()).unwrap_or(0);
            let ok = v.get("completed").and_then(|x| x.as_u64()).unwrap_or(0);
            rows.push((model.clone(), rate, total, ok));
        }
    }
    rows.sort_by(|a, b| {
        b.1.partial_cmp(&a.1)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| b.2.cmp(&a.2))
    });
    let ranked: Vec<Value> = rows
        .into_iter()
        .map(|(model, success_rate, total, completed)| json!({"model":model,"success_rate":success_rate,"total":total,"completed":completed,"shadow_only":true}))
        .collect();
    json!({
        "mode": "SHADOW_ONLY_NO_DISPATCH_MUTATION",
        "would_rank_models_by": ["success_rate", "sample_count"],
        "ranked_models": ranked,
        "applied_to_runtime": false
    })
}

fn shadow_circuit_breaker(sub: &Value) -> Value {
    let mut consecutive_non_success = 0usize;
    if let Some(arr) = sub.get("recent").and_then(|x| x.as_array()) {
        for v in arr.iter().rev() {
            let st = v
                .get("status")
                .and_then(|x| x.as_str())
                .unwrap_or("unknown");
            if st == "completed" {
                break;
            }
            consecutive_non_success += 1;
        }
    }
    let observe = consecutive_non_success >= 3;
    json!({
        "mode": "SHADOW_CIRCUIT_BREAKER_NO_BLOCK",
        "threshold": "3_consecutive_non_success",
        "consecutive_non_success_recent": consecutive_non_success,
        "decision": if observe {"WATCH_OBSERVE_ONLY"} else {"PASS_NO_SHADOW_BREAKER_TRIGGER"},
        "legal_six_roles_policy": "WATCH_ONLY_NEVER_AUTO_BREAK",
        "applied_to_runtime": false
    })
}

fn feishu_bitable_policy(h: &Path) -> Value {
    let schema_path = h.join(
        ".hermes/workspace/pgg-archon-governance/daa-governance/feishu_bitable_schema_dry_run.json",
    );
    json!({
        "mode": "DESENSITIZED_SCHEMA_DRY_RUN_FIRST",
        "allowed_fields": ["agent_id", "lane", "status", "score", "success_rate", "cost_tier", "updated_at", "boundary"],
        "forbidden_fields": ["case_name", "client_name", "party_name", "evidence_content", "legal_document_text", "credential", "token", "secret"],
        "schema_dry_run_path": schema_path,
        "bitable_created": false,
        "truth_boundary": "do not write sensitive case/task contents to Feishu"
    })
}

fn write_md(result: &Value, path: &Path) {
    let mut s = String::new();
    s.push_str("# PGG DAA Governance Gate\n\n");
    s.push_str(&format!(
        "- Generated: `{}`\n- Status: `{}`\n- Score: `{}`\n\n",
        result["generated_at"].as_str().unwrap_or(""),
        result["status"].as_str().unwrap_or(""),
        result["score"].as_i64().unwrap_or(0)
    ));
    s.push_str("## Subagents\n\n");
    let sub = &result["subagents"];
    s.push_str(&format!("- total: `{}`\n- last24: `{}`\n- completed: `{}`\n- timeout: `{}`\n- success_rate_all: `{:.3}`\n\n", sub["total"].as_u64().unwrap_or(0), sub["last24"].as_u64().unwrap_or(0), sub["completed"].as_u64().unwrap_or(0), sub["timeout"].as_u64().unwrap_or(0), sub["success_rate_all"].as_f64().unwrap_or(0.0)));
    s.push_str("## Legal multiagent ops\n\n");
    let ops = &result["legal_multiagent_ops"];
    s.push_str(&format!(
        "- D1: `{}`\n- Queue: `{}` items `{}`\n- Templates: `{}` count `{}`\n\n",
        ops["d1"]["status"].as_str().unwrap_or("missing"),
        ops["queue"]["status"].as_str().unwrap_or("missing"),
        ops["queue"]["item_count"].as_i64().unwrap_or(-1),
        ops["templates"]["status"].as_str().unwrap_or("missing"),
        ops["templates"]["template_count"].as_i64().unwrap_or(-1)
    ));
    s.push_str("## B-mode decisions\n\n");
    s.push_str("- C1: `PROVISIONAL_SUCCESS_ONLY` for narrow low-risk non-legal/non-system tasks; silence is not final success.\n");
    s.push_str("- C2: `SHADOW_ONLY_NO_DISPATCH_MUTATION`; advisory ranking only.\n");
    s.push_str("- C3: `SHADOW_CIRCUIT_BREAKER_NO_BLOCK`; WATCH only, no runtime block.\n");
    s.push_str("- C4: desensitized Feishu Bitable schema dry-run first; no sensitive fields.\n");
    s.push_str("- C5: autonomy loop read-only probe integration.\n\n");
    s.push_str("## Boundary\n\nThis is a read-only DAA evidence gate. It does not change orchestrator dispatch, does not auto-circuit-break agents, and does not write sensitive Feishu Bitable data.\n");
    fs::write(path, s).unwrap();
}
fn main() {
    let h = home();
    let out_dir = h.join(".hermes/workspace/pgg-archon-governance/daa-governance");
    fs::create_dir_all(&out_dir).unwrap();
    let sub = read_subagents(&h);
    let legal = read_legal_ops(&h);
    let cost = read_provider_cost(&h);
    let mut checks = BTreeMap::new();
    checks.insert(
        "subagent_ledger_present",
        sub["total"].as_u64().unwrap_or(0) > 0,
    );
    checks.insert(
        "legal_queue_clear",
        legal["queue"]["status"].as_str() == Some("PASS_NO_PENDING_RECEIPTS"),
    );
    checks.insert(
        "legal_templates_clear",
        legal["templates"]["status"].as_str() == Some("PASS_NO_TEMPLATES_NEEDED"),
    );
    checks.insert(
        "provider_cost_profile_present",
        !cost
            .get("missing")
            .and_then(|x| x.as_bool())
            .unwrap_or(false),
    );
    checks.insert("no_auto_dispatch_mutation", true);
    checks.insert("no_auto_circuit_breaker_mutation", true);
    let pass = checks.values().filter(|x| **x).count() as i64;
    let total = checks.len() as i64;
    let score = (pass * 100 / total) as i64;
    let status = if score >= 80 {
        "PASS_READ_ONLY_DAA_GOVERNANCE_READY"
    } else {
        "WATCH_DAA_GOVERNANCE_GAPS"
    };
    let result = json!({"schema":"pgg-daa-governance-gate/v2","generated_at":Local::now().to_rfc3339_opts(SecondsFormat::Secs,true),"status":status,"score":score,"checks":checks,"success_semantics":success_semantics(),"shadow_dispatch":shadow_dispatch(&sub),"shadow_circuit_breaker":shadow_circuit_breaker(&sub),"feishu_bitable_policy":feishu_bitable_policy(&h),"subagents":sub,"legal_multiagent_ops":legal,"provider_cost_profile":cost,"boundary":["read-only evidence gate","no orchestrator scheduling mutation","no automatic circuit breaker runtime block","no sensitive Feishu Bitable write"]});
    let date = Local::now().format("%Y%m%d-%H%M%S").to_string();
    let jp = out_dir.join(format!("daa-governance-{date}.json"));
    let mp = out_dir.join(format!("daa-governance-{date}.md"));
    fs::write(&jp, serde_json::to_string_pretty(&result).unwrap()).unwrap();
    write_md(&result, &mp);
    fs::write(
        out_dir.join("latest.json"),
        serde_json::to_string_pretty(&result).unwrap(),
    )
    .unwrap();
    fs::write(out_dir.join("latest.md"), fs::read_to_string(&mp).unwrap()).unwrap();
    println!(
        "{}",
        json!({"ok":true,"status":status,"score":score,"json":jp,"md":mp})
    );
}
