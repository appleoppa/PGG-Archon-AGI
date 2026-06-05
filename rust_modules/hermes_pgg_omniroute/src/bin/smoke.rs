use hermes_pgg_omniroute::*;
use serde_json::{json, Value};
use std::env;
use std::fs;
use std::time::{SystemTime, UNIX_EPOCH};

fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}

fn sample_providers(now: u64) -> Vec<ProviderState> {
    vec![
        ProviderState {
            id: "deepseek".into(),
            kind: ProviderKind::DeepSeekChat,
            health: 0.95,
            quality: 0.82,
            schema_reliability: 0.80,
            cost_efficiency: 0.95,
            latency_score: 0.80,
            compliance: 0.78,
            recent_failure_debt: 0.05,
            cooldown_until_epoch_ms: None,
            model_lock: None,
            supports_responses: false,
            supports_legal: true,
            supports_coding: true,
            supports_evolution: false,
        },
        ProviderState {
            id: "gpt55".into(),
            kind: ProviderKind::GptResponses,
            health: 0.80,
            quality: 0.94,
            schema_reliability: 0.92,
            cost_efficiency: 0.55,
            latency_score: 0.62,
            compliance: 0.92,
            recent_failure_debt: 0.10,
            cooldown_until_epoch_ms: None,
            model_lock: None,
            supports_responses: true,
            supports_legal: true,
            supports_coding: true,
            supports_evolution: true,
        },
        ProviderState {
            id: "minimax".into(),
            kind: ProviderKind::MiniMaxChat,
            health: 0.88,
            quality: 0.74,
            schema_reliability: 0.60,
            cost_efficiency: 0.90,
            latency_score: 0.76,
            compliance: 0.68,
            recent_failure_debt: 0.20,
            cooldown_until_epoch_ms: Some(now.saturating_add(3_600_000)),
            model_lock: None,
            supports_responses: false,
            supports_legal: false,
            supports_coding: true,
            supports_evolution: false,
        },
    ]
}

fn providers_from_health_snapshot(snapshot: &Value, now: u64) -> Vec<ProviderState> {
    let mut out = Vec::new();
    if let Some(items) = snapshot.get("providers").and_then(|v| v.as_array()) {
        for item in items {
            let name = item
                .get("provider")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown");
            let healthy = item
                .get("healthy")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            let visible = item
                .get("visible_chars")
                .and_then(|v| v.as_u64())
                .unwrap_or(0) as f64;
            let http_status = item
                .get("http_status")
                .and_then(|v| v.as_u64())
                .unwrap_or(0);
            let api_mode = item.get("api_mode").and_then(|v| v.as_str()).unwrap_or("");
            let supports = item.get("supports").unwrap_or(&Value::Null);
            let visible_score = (visible / 16.0).max(0.0).min(1.0);
            let health = if healthy {
                0.75 + visible_score * 0.25
            } else {
                0.10
            };
            let schema_reliability = if healthy
                && item.get("json_validity").and_then(|v| v.as_str()) == Some("visible_text")
            {
                0.90
            } else {
                0.25
            };
            let quality = if healthy {
                0.70 + visible_score * 0.20
            } else {
                0.20
            };
            let recent_failure_debt = if healthy { 0.0 } else { 0.75 };
            let cooldown = if healthy {
                None
            } else {
                Some(now.saturating_add(3_600_000))
            };
            let kind = match name {
                "deepseek" => ProviderKind::DeepSeekChat,
                "mimo" => ProviderKind::MimoChat,
                "gpt55" => ProviderKind::GptResponses,
                "minimax" => ProviderKind::MiniMaxChat,
                _ if api_mode == "codex_responses" => ProviderKind::GptResponses,
                _ => ProviderKind::Compatible,
            };
            out.push(ProviderState {
                id: name.to_string(),
                kind,
                health,
                quality,
                schema_reliability,
                cost_efficiency: match name {
                    "deepseek" => 0.95,
                    "mimo" => 0.82,
                    "gpt55" => 0.55,
                    _ => 0.70,
                },
                latency_score: if healthy { 0.75 } else { 0.20 },
                compliance: if healthy { 0.78 } else { 0.25 },
                recent_failure_debt,
                cooldown_until_epoch_ms: cooldown,
                model_lock: None,
                supports_responses: supports
                    .get("responses")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(api_mode == "codex_responses"),
                supports_legal: supports
                    .get("legal")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(false),
                supports_coding: supports
                    .get("coding")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(true),
                supports_evolution: supports
                    .get("evolution")
                    .and_then(|v| v.as_bool())
                    .unwrap_or(false),
            });
            let _ = http_status;
        }
    }
    if out.is_empty() {
        sample_providers(now)
    } else {
        out
    }
}

fn sample_order_factors() -> OrderFactors {
    OrderFactors {
        tao_te_ching: 0.95,
        i_ching: 0.92,
        huang_di: 0.90,
        he_tu_luo_shu: 0.96,
        gan_zhi: 0.88,
        wu_xing: 0.91,
        bagua: 0.89,
        defect_rate: 0.08,
    }
}

fn clamp01(v: f64) -> f64 {
    if !v.is_finite() {
        return 0.0;
    }
    v.max(0.0).min(1.0)
}

fn evm_order_factors(report: &Value) -> OrderFactors {
    let first = report
        .get("results")
        .and_then(|v| v.as_array())
        .and_then(|arr| arr.first())
        .unwrap_or(&Value::Null);
    let ancient_product = first
        .get("ancient_product")
        .and_then(|v| v.as_f64())
        .unwrap_or(1.0);
    let defect_rate = first
        .get("defect_rate")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.0);
    let evm_score = first
        .get("evm_score")
        .and_then(|v| v.as_f64())
        .or_else(|| report.get("final_score").and_then(|v| v.as_f64()))
        .unwrap_or(0.75);
    // If the Python report only exposes aggregate ancient_product, distribute it
    // as a geometric mean across the seven ancient factors. HeTuLuoShu receives
    // a bounded lift from final EVM score so the dashboard reflects live EVM state.
    let geometric = clamp01(ancient_product).powf(1.0 / 7.0);
    let hetu = (geometric * 0.70 + clamp01(evm_score) * 0.30)
        .max(0.0)
        .min(1.0);
    OrderFactors {
        tao_te_ching: geometric,
        i_ching: geometric,
        huang_di: geometric,
        he_tu_luo_shu: hetu,
        gan_zhi: geometric,
        wu_xing: geometric,
        bagua: geometric,
        defect_rate: clamp01(defect_rate),
    }
}

fn request_for(text: &str, mode: &str, now: u64) -> RouteRequest {
    let task = classify_task(text);
    RouteRequest {
        task,
        now_epoch_ms: now,
        preferred_model: Some("gpt-5.5".into()),
        require_responses_api: matches!(mode, "smoke" | "dashboard" | "dashboard-from-evm")
            || text.to_lowercase().contains("gpt"),
        require_legal_gate: matches!(task, TaskClass::Legal),
        require_evolution_gate: matches!(task, TaskClass::Evolution),
    }
}

fn sample_tool_output() -> &'static str {
    "diff --git a/src/lib.rs b/src/lib.rs\n@@ -1 +1 @@\n- old\n+ new\n《民法典》第五百七十七条 证据A /Users/appleoppa/demo.rs:7 ERROR\n"
}

fn emit_smoke() {
    let now = now_ms();
    let providers = sample_providers(now);
    let req = request_for("用 Rust 实现 9router 功能并融合 PGG 量子路由", "smoke", now);
    let order = sample_order_factors();
    let influence = order_influence(&order);
    let decision = decide_route_with_order(&req, &providers, &order);
    let (_compressed, rtk) = evidence_preserving_rtk(sample_tool_output());
    let ledger = ledger_entry(&decision, &req, Some(128), None);
    println!(
        "{}",
        to_pretty_json(&json!({
            "schema": "PGGArchonOmniRouteSmoke/v1",
            "decision": decision,
            "order_influence": influence,
            "rtk": rtk,
            "ledger": ledger,
            "boundary": "smoke only; no upstream provider call"
        }))
    );
}

fn emit_decide(text: &str) {
    let now = now_ms();
    let providers = sample_providers(now);
    let req = request_for(text, "decide", now);
    let decision = decide_route(&req, &providers);
    let ledger = ledger_entry(&decision, &req, None, None);
    println!(
        "{}",
        to_pretty_json(&json!({
            "schema": "PGGArchonOmniRouteCliDecision/v1",
            "input": text,
            "request": req,
            "decision": decision,
            "ledger": ledger,
            "boundary": "decision only; no upstream provider call"
        }))
    );
}

fn dashboard_payload(
    order: OrderFactors,
    evm_report: Option<Value>,
    health_snapshot: Option<Value>,
    order_source: &str,
) -> Value {
    let now = now_ms();
    let providers = health_snapshot
        .as_ref()
        .map(|h| providers_from_health_snapshot(h, now))
        .unwrap_or_else(|| sample_providers(now));
    let req = request_for("PGG Archon 进化任务 dashboard route", order_source, now);
    let influence = order_influence(&order);
    let decision = decide_route_with_order(&req, &providers, &order);
    let (_compressed, rtk) = evidence_preserving_rtk(sample_tool_output());
    let provider_cards: Vec<_> = providers
        .iter()
        .map(|p| {
            let availability = is_available(p, &req)
                .map(|_| "available".to_string())
                .unwrap_or_else(|e| format!("blocked:{e}"));
            json!({
                "id": p.id,
                "kind": p.kind,
                "availability": availability,
                "score": route_score_with_order(p, &req, &order),
                "health": p.health,
                "quality": p.quality,
                "schema_reliability": p.schema_reliability,
                "cost_efficiency": p.cost_efficiency,
                "latency_score": p.latency_score,
                "compliance": p.compliance,
                "recent_failure_debt": p.recent_failure_debt,
                "supports": {
                    "responses": p.supports_responses,
                    "legal": p.supports_legal,
                    "coding": p.supports_coding,
                    "evolution": p.supports_evolution
                }
            })
        })
        .collect();
    json!({
        "schema": "PGGArchonOmniRouteDashboard/v1",
        "learned_from_9router_dashboard": [
            "provider_cards",
            "fallback_chain",
            "blocked_reasons",
            "rtk_token_saver_stats",
            "route_evidence_ledger",
            "truth_boundary"
        ],
        "generated_at_epoch_ms": now,
        "order_source": order_source,
        "evm_report": evm_report,
        "provider_health_snapshot": health_snapshot,
        "request": req,
        "order_factors": order,
        "order_influence": influence,
        "summary": {
            "selected_provider": decision.selected_provider,
            "status": decision.status,
            "score": decision.score,
            "fallback_count": decision.fallback_chain.len(),
            "blocked_count": decision.blocked.len(),
            "rtk_filter": rtk.filter,
            "rtk_bytes_before": rtk.bytes_before,
            "rtk_bytes_after": rtk.bytes_after,
            "rtk_preserved_anchor_count": rtk.preserved_anchors.len(),
            "order_status": influence.status,
            "he_tu_luo_shu": influence.he_tu_luo_shu,
            "order_route_multiplier": influence.route_multiplier
        },
        "provider_cards": provider_cards,
        "decision": decision,
        "rtk": rtk,
        "panels": {
            "routing": "selected provider, score, fallback and blocked reasons",
            "providers": "health/quality/schema/cost/latency/compliance cards",
            "token_saver": "RTK filter, byte delta, preserved anchors",
            "evidence": "ledger-compatible proof fields; no fake provider participation",
            "evm_order": "live Python EvomasterEngine score can feed bounded Rust OrderFactors",
            "boundary": "dashboard data surface, not proof of upstream call or full AGI"
        },
        "boundary": "Rust dashboard data surface inspired by 9router; EVM/HeTuLuoShu is bounded governance input; no OAuth/free-provider bypass; no upstream provider call."
    })
}

fn emit_dashboard() {
    println!(
        "{}",
        to_pretty_json(&dashboard_payload(
            sample_order_factors(),
            None,
            None,
            "sample"
        ))
    );
}

fn emit_dashboard_from_evm(path: &str) {
    let raw = fs::read_to_string(path).unwrap_or_else(|e| {
        eprintln!("failed to read evm report {path}: {e}");
        std::process::exit(3);
    });
    let report: Value = serde_json::from_str(&raw).unwrap_or_else(|e| {
        eprintln!("failed to parse evm report {path}: {e}");
        std::process::exit(4);
    });
    let order = evm_order_factors(&report);
    println!(
        "{}",
        to_pretty_json(&dashboard_payload(
            order,
            Some(report),
            None,
            "python_evm_engine"
        ))
    );
}

fn emit_dashboard_from_live(evm_path: &str, health_path: &str) {
    let evm_raw = fs::read_to_string(evm_path).unwrap_or_else(|e| {
        eprintln!("failed to read evm report {evm_path}: {e}");
        std::process::exit(3);
    });
    let health_raw = fs::read_to_string(health_path).unwrap_or_else(|e| {
        eprintln!("failed to read provider health {health_path}: {e}");
        std::process::exit(5);
    });
    let evm_report: Value = serde_json::from_str(&evm_raw).unwrap_or_else(|e| {
        eprintln!("failed to parse evm report {evm_path}: {e}");
        std::process::exit(4);
    });
    let health_snapshot: Value = serde_json::from_str(&health_raw).unwrap_or_else(|e| {
        eprintln!("failed to parse provider health {health_path}: {e}");
        std::process::exit(6);
    });
    let order = evm_order_factors(&evm_report);
    println!(
        "{}",
        to_pretty_json(&dashboard_payload(
            order,
            Some(evm_report),
            Some(health_snapshot),
            "python_evm_engine+live_provider_health"
        ))
    );
}

fn main() {
    let mut args = env::args().skip(1);
    match args.next().as_deref() {
        Some("decide") => emit_decide(&args.collect::<Vec<_>>().join(" ")),
        Some("dashboard") => emit_dashboard(),
        Some("dashboard-from-evm") => {
            let path = args.next().unwrap_or_else(|| {
                eprintln!("dashboard-from-evm requires <evm_report.json>");
                std::process::exit(2);
            });
            emit_dashboard_from_evm(&path)
        }
        Some("dashboard-from-live") => {
            let evm_path = args.next().unwrap_or_else(|| {
                eprintln!("dashboard-from-live requires <evm_report.json> <provider_health.json>");
                std::process::exit(2);
            });
            let health_path = args.next().unwrap_or_else(|| {
                eprintln!("dashboard-from-live requires <evm_report.json> <provider_health.json>");
                std::process::exit(2);
            });
            emit_dashboard_from_live(&evm_path, &health_path)
        }
        Some("smoke") | None => emit_smoke(),
        Some(other) => {
            eprintln!("unknown mode: {other}; use smoke | decide <text> | dashboard | dashboard-from-evm <evm_report.json> | dashboard-from-live <evm_report.json> <provider_health.json>");
            std::process::exit(2);
        }
    }
}
