//! PGG Archon OmniRoute v0.1
//!
//! Rust-native, evidence-preserving router core inspired by the safe structural
//! patterns observed in decolua/9router: universal ingress, fallback, cooldown,
//! RTK-style tool-result compression, and route evidence. This crate is bounded:
//! it does not call providers, bypass quotas, manage OAuth tokens, or prove AGI.

use serde::{Deserialize, Serialize};
use std::cmp::Ordering;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TaskClass {
    Legal,
    Coding,
    Evolution,
    Audit,
    Document,
    General,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ProviderKind {
    GptResponses,
    ClaudeResponses,
    DeepSeekChat,
    MimoChat,
    AgnesChat,
    MiniMaxChat,
    Local,
    Compatible,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderState {
    pub id: String,
    pub kind: ProviderKind,
    pub health: f64,
    pub quality: f64,
    pub schema_reliability: f64,
    pub cost_efficiency: f64,
    pub latency_score: f64,
    pub compliance: f64,
    pub recent_failure_debt: f64,
    pub cooldown_until_epoch_ms: Option<u64>,
    pub model_lock: Option<String>,
    pub supports_responses: bool,
    pub supports_legal: bool,
    pub supports_coding: bool,
    pub supports_evolution: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouteRequest {
    pub task: TaskClass,
    pub now_epoch_ms: u64,
    pub preferred_model: Option<String>,
    pub require_responses_api: bool,
    pub require_legal_gate: bool,
    pub require_evolution_gate: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderFactors {
    pub tao_te_ching: f64,
    pub i_ching: f64,
    pub huang_di: f64,
    pub he_tu_luo_shu: f64,
    pub gan_zhi: f64,
    pub wu_xing: f64,
    pub bagua: f64,
    pub defect_rate: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderInfluence {
    pub schema: String,
    pub ancient_product: f64,
    pub order_strength: f64,
    pub he_tu_luo_shu: f64,
    pub defect_rate: f64,
    pub route_multiplier: f64,
    pub task_fit_boost: f64,
    pub compliance_boost: f64,
    pub status: String,
    pub boundary: String,
}

impl Default for OrderFactors {
    fn default() -> Self {
        Self {
            tao_te_ching: 1.0,
            i_ching: 1.0,
            huang_di: 1.0,
            he_tu_luo_shu: 1.0,
            gan_zhi: 1.0,
            wu_xing: 1.0,
            bagua: 1.0,
            defect_rate: 0.0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouteDecision {
    pub schema: String,
    pub status: String,
    pub selected_provider: Option<String>,
    pub selected_kind: Option<ProviderKind>,
    pub score: f64,
    pub fallback_chain: Vec<String>,
    pub blocked: Vec<String>,
    pub rationale: Vec<String>,
    pub boundary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RtkStats {
    pub filter: String,
    pub bytes_before: usize,
    pub bytes_after: usize,
    pub preserved_anchors: Vec<String>,
    pub compressed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvidenceLedgerEntry {
    pub schema: String,
    pub provider_id: String,
    pub model: Option<String>,
    pub task: TaskClass,
    pub status: String,
    pub score: f64,
    pub visible_output_chars: Option<usize>,
    pub fallback_reason: Option<String>,
    pub boundary: String,
}

fn clamp01(v: f64) -> f64 {
    if !v.is_finite() {
        return 0.0;
    }
    v.max(0.0).min(1.0)
}

fn round6(v: f64) -> f64 {
    (v * 1_000_000.0).round() / 1_000_000.0
}

pub fn order_influence(order: &OrderFactors) -> OrderInfluence {
    let ancient_product = clamp01(order.tao_te_ching)
        * clamp01(order.i_ching)
        * clamp01(order.huang_di)
        * clamp01(order.he_tu_luo_shu)
        * clamp01(order.gan_zhi)
        * clamp01(order.wu_xing)
        * clamp01(order.bagua);
    let defect_rate = clamp01(order.defect_rate);
    // Keep raw product for EVM evidence, but use geometric mean for routing influence.
    // Directly multiplying seven ~0.9 factors over-penalizes a healthy but imperfect state.
    let order_strength = ancient_product.powf(1.0 / 7.0);
    // Bounded route multiplier: strong order can add up to +10%, defects can subtract up to -20%.
    // This keeps HeTuLuoShu/EVM as governance influence, not a fake provider-quality substitute.
    let route_multiplier = (0.90 + order_strength * 0.10 - defect_rate * 0.20)
        .max(0.70)
        .min(1.05);
    let task_fit_boost = (clamp01(order.he_tu_luo_shu) - 0.5) * 0.08;
    let compliance_boost = (order_strength - 0.5) * 0.10 - defect_rate * 0.10;
    let governed_strength = order_strength * (1.0 - defect_rate);
    let status = if governed_strength >= 0.75 {
        "PASS"
    } else if governed_strength >= 0.60 {
        "WATCH"
    } else {
        "BLOCK"
    };
    OrderInfluence {
        schema: "PGGArchonOrderInfluence/v1".to_string(),
        ancient_product: round6(ancient_product),
        order_strength: round6(order_strength),
        he_tu_luo_shu: round6(clamp01(order.he_tu_luo_shu)),
        defect_rate: round6(defect_rate),
        route_multiplier: round6(route_multiplier),
        task_fit_boost: round6(task_fit_boost),
        compliance_boost: round6(compliance_boost),
        status: status.to_string(),
        boundary: "EVM/HeTuLuoShu order influence is bounded governance signal; not mystical proof, not provider call evidence.".to_string(),
    }
}

pub fn classify_task(text: &str) -> TaskClass {
    let t = text.to_lowercase();
    let legal_hits = [
        "法", "案件", "起诉", "判决", "合同", "证据", "律师", "legal", "court",
    ];
    let evolution_hits = ["进化", "agi", "apex", "pgg", "manifest", "evolve", "gene"];
    let audit_hits = ["审计", "核查", "verify", "audit", "redteam", "红队"];
    let coding_hits = [
        "rust", "python", "代码", "编译", "测试", "cargo", "github", "repo",
    ];
    let doc_hits = ["文书", "报告", "润色", "markdown", "pdf", "ppt"];
    if legal_hits.iter().any(|k| t.contains(k)) {
        TaskClass::Legal
    } else if evolution_hits.iter().any(|k| t.contains(k)) {
        TaskClass::Evolution
    } else if audit_hits.iter().any(|k| t.contains(k)) {
        TaskClass::Audit
    } else if coding_hits.iter().any(|k| t.contains(k)) {
        TaskClass::Coding
    } else if doc_hits.iter().any(|k| t.contains(k)) {
        TaskClass::Document
    } else {
        TaskClass::General
    }
}

pub fn task_fit(p: &ProviderState, req: &RouteRequest) -> f64 {
    match req.task {
        TaskClass::Legal => {
            if p.supports_legal {
                1.0
            } else {
                0.35
            }
        }
        TaskClass::Coding => {
            if p.supports_coding {
                1.0
            } else {
                0.55
            }
        }
        TaskClass::Evolution => {
            if p.supports_evolution {
                1.0
            } else {
                0.45
            }
        }
        TaskClass::Audit => (clamp01(p.schema_reliability) + clamp01(p.compliance)) / 2.0,
        TaskClass::Document => 0.75 + clamp01(p.quality) * 0.25,
        TaskClass::General => 0.70 + clamp01(p.quality) * 0.30,
    }
}

pub fn is_available(p: &ProviderState, req: &RouteRequest) -> Result<(), String> {
    if let Some(until) = p.cooldown_until_epoch_ms {
        if until > req.now_epoch_ms {
            return Err(format!("cooldown_until={until}"));
        }
    }
    if req.require_responses_api && !p.supports_responses {
        return Err("responses_required_but_not_supported".to_string());
    }
    if req.require_legal_gate && !p.supports_legal {
        return Err("legal_gate_required_but_provider_not_legal_capable".to_string());
    }
    if req.require_evolution_gate && !p.supports_evolution {
        return Err("evolution_gate_required_but_provider_not_evolution_capable".to_string());
    }
    if let (Some(lock), Some(pref)) = (&p.model_lock, &req.preferred_model) {
        if lock != pref {
            return Err(format!("model_locked_to={lock}"));
        }
    }
    Ok(())
}

pub fn route_score(p: &ProviderState, req: &RouteRequest) -> f64 {
    let score = task_fit(p, req) * 0.22
        + clamp01(p.health) * 0.18
        + clamp01(p.quality) * 0.18
        + clamp01(p.schema_reliability) * 0.14
        + clamp01(p.cost_efficiency) * 0.10
        + clamp01(p.latency_score) * 0.08
        + clamp01(p.compliance) * 0.20
        - clamp01(p.recent_failure_debt) * 0.25;
    let bounded = score.max(0.0).min(1.0);
    (bounded * 1_000_000.0).round() / 1_000_000.0
}

pub fn route_score_with_order(p: &ProviderState, req: &RouteRequest, order: &OrderFactors) -> f64 {
    let influence = order_influence(order);
    let base_task_fit = (task_fit(p, req) + influence.task_fit_boost)
        .max(0.0)
        .min(1.0);
    let governed_compliance = (clamp01(p.compliance) + influence.compliance_boost)
        .max(0.0)
        .min(1.0);
    let score = base_task_fit * 0.22
        + clamp01(p.health) * 0.18
        + clamp01(p.quality) * 0.18
        + clamp01(p.schema_reliability) * 0.14
        + clamp01(p.cost_efficiency) * 0.10
        + clamp01(p.latency_score) * 0.08
        + governed_compliance * 0.20
        - clamp01(p.recent_failure_debt) * 0.25;
    round6((score * influence.route_multiplier).max(0.0).min(1.0))
}

pub fn decide_route_with_order(
    req: &RouteRequest,
    providers: &[ProviderState],
    order: &OrderFactors,
) -> RouteDecision {
    let mut candidates: Vec<(&ProviderState, f64)> = vec![];
    let mut blocked = vec![];
    for p in providers {
        match is_available(p, req) {
            Ok(()) => candidates.push((p, route_score_with_order(p, req, order))),
            Err(reason) => blocked.push(format!("{}:{reason}", p.id)),
        }
    }
    candidates.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(Ordering::Equal));
    let fallback_chain = candidates
        .iter()
        .map(|(p, _)| p.id.clone())
        .collect::<Vec<_>>();
    if let Some((p, score)) = candidates.first() {
        RouteDecision {
            schema: "PGGArchonOmniRouteDecision/v1".to_string(),
            status: if *score >= 0.75 { "PASS" } else { "WATCH" }.to_string(),
            selected_provider: Some(p.id.clone()),
            selected_kind: Some(p.kind),
            score: *score,
            fallback_chain,
            blocked,
            rationale: vec![
                format!("task={:?}", req.task),
                format!("order_influence={}", order_influence(order).status),
                "score=base_route_score_with_bounded_evm_hetu_luoshu_multiplier".to_string(),
                "bounded_router_no_provider_call".to_string(),
            ],
            boundary: "Rust routing decision with bounded EVM/HeTuLuoShu influence; not proof provider participated, not full AGI.".to_string(),
        }
    } else {
        RouteDecision {
            schema: "PGGArchonOmniRouteDecision/v1".to_string(),
            status: "BLOCKED".to_string(),
            selected_provider: None,
            selected_kind: None,
            score: 0.0,
            fallback_chain,
            blocked,
            rationale: vec![format!("task={:?}; no available provider", req.task)],
            boundary: "No provider selected; route decision blocked.".to_string(),
        }
    }
}

pub fn decide_route(req: &RouteRequest, providers: &[ProviderState]) -> RouteDecision {
    let mut candidates: Vec<(&ProviderState, f64)> = vec![];
    let mut blocked = vec![];
    for p in providers {
        match is_available(p, req) {
            Ok(()) => candidates.push((p, route_score(p, req))),
            Err(reason) => blocked.push(format!("{}:{reason}", p.id)),
        }
    }
    candidates.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(Ordering::Equal));
    let fallback_chain = candidates
        .iter()
        .map(|(p, _)| p.id.clone())
        .collect::<Vec<_>>();
    if let Some((p, score)) = candidates.first() {
        RouteDecision {
            schema: "PGGArchonOmniRouteDecision/v1".to_string(),
            status: if *score >= 0.75 { "PASS" } else { "WATCH" }.to_string(),
            selected_provider: Some(p.id.clone()),
            selected_kind: Some(p.kind),
            score: *score,
            fallback_chain,
            blocked,
            rationale: vec![
                format!("task={:?}", req.task),
                "score=task_fit*0.22+health*0.18+quality*0.18+schema*0.14+cost*0.10+latency*0.08+compliance*0.20-failure_debt*0.25".to_string(),
                "bounded_router_no_provider_call".to_string(),
            ],
            boundary: "Rust routing decision only; not proof provider participated, not full AGI.".to_string(),
        }
    } else {
        RouteDecision {
            schema: "PGGArchonOmniRouteDecision/v1".to_string(),
            status: "BLOCKED".to_string(),
            selected_provider: None,
            selected_kind: None,
            score: 0.0,
            fallback_chain,
            blocked,
            rationale: vec![format!("task={:?}; no available provider", req.task)],
            boundary: "No provider selected; route decision blocked.".to_string(),
        }
    }
}

pub fn evidence_preserving_rtk(input: &str) -> (String, RtkStats) {
    let bytes_before = input.len();
    let filter = detect_filter(input);
    let anchors = collect_anchors(input);
    let output = match filter.as_str() {
        "git_diff" => compress_git_diff(input),
        "build_output" => compress_build_output(input),
        "grep" => compress_keep_head_tail(input, 80),
        "find" | "ls" | "tree" => compress_keep_head_tail(input, 60),
        "dedup_log" => dedup_lines(input),
        _ => compress_keep_head_tail(input, 100),
    };
    let output = ensure_anchors(&output, &anchors);
    let stats = RtkStats {
        filter,
        bytes_before,
        bytes_after: output.len(),
        preserved_anchors: anchors,
        compressed: output.len() < bytes_before,
    };
    (output, stats)
}

pub fn detect_filter(input: &str) -> String {
    let head: String = input.chars().take(4096).collect();
    if head.contains("diff --git ") || head.lines().any(|l| l.starts_with("@@ ")) {
        "git_diff".into()
    } else if head.lines().any(|l| {
        l.contains("ERROR")
            || l.contains("[ERROR]")
            || l.contains("Compiling")
            || l.contains("Finished ")
    }) {
        "build_output".into()
    } else if head.lines().take(5).any(|l| looks_like_grep(l)) {
        "grep".into()
    } else if head
        .lines()
        .filter(|l| !l.trim().is_empty())
        .take(4)
        .all(|l| l.contains('/') && !l.contains(':'))
    {
        "find".into()
    } else if head
        .lines()
        .any(|l| l.starts_with("total ") || l.starts_with("drwx") || l.starts_with("-rw"))
    {
        "ls".into()
    } else if head.contains("├──") || head.contains("└──") {
        "tree".into()
    } else if head.lines().count() > 8 {
        "dedup_log".into()
    } else {
        "none".into()
    }
}

fn looks_like_grep(line: &str) -> bool {
    let mut parts = line.splitn(3, ':');
    matches!((parts.next(), parts.next(), parts.next()), (Some(_), Some(n), Some(_)) if n.parse::<usize>().is_ok())
}

fn collect_anchors(input: &str) -> Vec<String> {
    let mut anchors = Vec::new();
    for line in input.lines() {
        let l = line.trim();
        let is_anchor = l.contains("ERROR")
            || l.contains("panic")
            || l.contains("diff --git")
            || l.starts_with("@@ ")
            || l.contains('第') && l.contains('条')
            || l.contains("法")
            || l.contains("案号")
            || l.contains("证据")
            || l.contains("/Users/")
            || l.contains(".rs:")
            || l.contains(".py:");
        if is_anchor && !anchors.iter().any(|x| x == l) {
            anchors.push(l.to_string());
        }
        if anchors.len() >= 24 {
            break;
        }
    }
    anchors
}

fn ensure_anchors(output: &str, anchors: &[String]) -> String {
    let mut out = output.to_string();
    let mut missing = Vec::new();
    for a in anchors {
        if !out.contains(a) {
            missing.push(a.clone());
        }
    }
    if !missing.is_empty() {
        out.push_str("\n\n[PGG_RTK_PRESERVED_ANCHORS]\n");
        for a in missing {
            out.push_str(&a);
            out.push('\n');
        }
    }
    out
}

fn compress_keep_head_tail(input: &str, max_lines: usize) -> String {
    let lines: Vec<&str> = input.lines().collect();
    if lines.len() <= max_lines {
        return input.to_string();
    }
    let head_n = max_lines / 2;
    let tail_n = max_lines - head_n;
    let mut out = Vec::new();
    out.extend_from_slice(&lines[..head_n]);
    out.push("...[PGG_RTK_TRUNCATED]...");
    out.extend_from_slice(&lines[lines.len() - tail_n..]);
    out.join("\n")
}

fn dedup_lines(input: &str) -> String {
    let mut out = Vec::new();
    let mut last = "";
    let mut repeats = 0usize;
    for line in input.lines() {
        if line == last {
            repeats += 1;
            continue;
        }
        if repeats > 0 {
            out.push(format!(
                "[PGG_RTK_DEDUP repeated_previous_line x{}]",
                repeats
            ));
            repeats = 0;
        }
        out.push(line.to_string());
        last = line;
    }
    if repeats > 0 {
        out.push(format!(
            "[PGG_RTK_DEDUP repeated_previous_line x{}]",
            repeats
        ));
    }
    out.join("\n")
}

fn compress_git_diff(input: &str) -> String {
    let mut out = Vec::new();
    for line in input.lines() {
        if line.starts_with("diff --git")
            || line.starts_with("@@ ")
            || line.starts_with("+++")
            || line.starts_with("---")
            || line.starts_with('+')
            || line.starts_with('-')
        {
            out.push(line);
        }
    }
    if out.is_empty() {
        compress_keep_head_tail(input, 100)
    } else {
        compress_keep_head_tail(&out.join("\n"), 140)
    }
}

fn compress_build_output(input: &str) -> String {
    let mut out = Vec::new();
    for line in input.lines() {
        let keep = line.contains("ERROR")
            || line.contains("error[")
            || line.contains("panic")
            || line.contains("FAILED")
            || line.contains("Finished")
            || line.contains("Compiling")
            || line.contains("warning");
        if keep {
            out.push(line);
        }
    }
    if out.is_empty() {
        compress_keep_head_tail(input, 80)
    } else {
        compress_keep_head_tail(&out.join("\n"), 120)
    }
}

pub fn ledger_entry(
    decision: &RouteDecision,
    req: &RouteRequest,
    visible_output_chars: Option<usize>,
    fallback_reason: Option<String>,
) -> EvidenceLedgerEntry {
    EvidenceLedgerEntry {
        schema: "PGGArchonRouteEvidence/v1".to_string(),
        provider_id: decision.selected_provider.clone().unwrap_or_else(|| "NONE".to_string()),
        model: req.preferred_model.clone(),
        task: req.task,
        status: decision.status.clone(),
        score: decision.score,
        visible_output_chars,
        fallback_reason,
        boundary: "Evidence ledger entry; provider participation requires actual upstream call evidence outside this crate.".to_string(),
    }
}

pub fn to_pretty_json<T: Serialize>(value: &T) -> String {
    serde_json::to_string_pretty(value).unwrap_or_else(|e| format!(r#"{{"error":"{}"}}"#, e))
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GapResolutionKind {
    ActiveGap,
    Superseded,
    PolicyBoundary,
    Closed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestGapSignal {
    pub key: String,
    pub status: String,
    pub boundary: String,
    pub lifecycle_hint: Option<GapResolutionKind>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManifestGapClassification {
    pub schema: String,
    pub active_gap_count: usize,
    pub resolved_or_policy_count: usize,
    pub active_keys: Vec<String>,
    pub resolved_or_policy_keys: Vec<String>,
    pub status: String,
    pub boundary: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FallbackOutcomeKind {
    PrimarySuccess,
    SameClassSubstitutionSuccess,
    CrossClassFallbackParticipation,
    ProviderError,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FallbackOutcome {
    pub primary_provider: String,
    pub fallback_provider: Option<String>,
    pub kind: FallbackOutcomeKind,
    pub counts_as_primary: bool,
    pub counts_as_same_class_substitution: bool,
    pub boundary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouteEnforcePolicy {
    pub enabled: bool,
    pub mode: String,
    pub operator_toggle_enabled: bool,
    pub operator_scope: String,
    pub hard_denied_intents: Vec<String>,
    pub allowed_intents: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouteEnforceDecisionCore {
    pub schema: String,
    pub would_execute: bool,
    pub reason: String,
    pub rollback_required: bool,
    pub boundary: String,
}

pub fn classify_manifest_gaps(signals: &[ManifestGapSignal]) -> ManifestGapClassification {
    let mut active_keys = Vec::new();
    let mut resolved_or_policy_keys = Vec::new();
    for s in signals {
        let text = format!("{} {} {}", s.key, s.status, s.boundary).to_uppercase();
        let pass_family = s.status == "PASS" || s.status.starts_with("PASS_");
        let active_marker = [
            "PARTIAL",
            "BLOCK",
            "FAIL",
            "502",
            "EXECUTION_BLOCKED",
            "NO PROVIDER SUBSTITUTION",
        ]
        .iter()
        .any(|m| text.contains(m));
        let policy_marker = pass_family
            && [
                "DEFAULT_OFF",
                "DEFAULT-OFF",
                "OPTIONAL",
                "MANUAL RUN",
                "ROLLBACK",
                "NOT GLOBAL ROUTE-ENFORCE",
                "ERROR_RECORDED",
                "POLICY BOUNDARY",
            ]
            .iter()
            .any(|m| text.contains(m));
        match s.lifecycle_hint {
            Some(
                GapResolutionKind::Superseded
                | GapResolutionKind::PolicyBoundary
                | GapResolutionKind::Closed,
            ) => resolved_or_policy_keys.push(s.key.clone()),
            _ if active_marker && !policy_marker => active_keys.push(s.key.clone()),
            _ if policy_marker => resolved_or_policy_keys.push(s.key.clone()),
            _ => {}
        }
    }
    let status = if active_keys.is_empty() {
        "PASS"
    } else {
        "WATCH"
    };
    ManifestGapClassification {
        schema: "PGGArchonManifestGapClassification/v1".to_string(),
        active_gap_count: active_keys.len(),
        resolved_or_policy_count: resolved_or_policy_keys.len(),
        active_keys,
        resolved_or_policy_keys,
        status: status.to_string(),
        boundary: "Rust classifier separates active gaps from superseded/policy-boundary PASS-family entries; it does not mutate Manifest history or prove AGI.".to_string(),
    }
}

pub fn classify_fallback_outcome(
    primary_provider: &str,
    fallback_provider: Option<&str>,
    primary_success: bool,
    fallback_success: bool,
    same_class: bool,
) -> FallbackOutcome {
    let kind = if primary_success {
        FallbackOutcomeKind::PrimarySuccess
    } else if fallback_success && same_class {
        FallbackOutcomeKind::SameClassSubstitutionSuccess
    } else if fallback_success {
        FallbackOutcomeKind::CrossClassFallbackParticipation
    } else {
        FallbackOutcomeKind::ProviderError
    };
    FallbackOutcome {
        primary_provider: primary_provider.to_string(),
        fallback_provider: fallback_provider.map(str::to_string),
        kind,
        counts_as_primary: primary_success,
        counts_as_same_class_substitution: matches!(kind, FallbackOutcomeKind::SameClassSubstitutionSuccess),
        boundary: "Fallback classification only; cross-class fallback participation is not primary success or same-class substitution proof.".to_string(),
    }
}

pub fn evaluate_route_enforce_core(
    policy: &RouteEnforcePolicy,
    intent: &str,
) -> RouteEnforceDecisionCore {
    let normalized = intent.to_lowercase();
    let hard_denied = policy
        .hard_denied_intents
        .iter()
        .any(|x| x.to_lowercase() == normalized);
    let allowed = policy
        .allowed_intents
        .iter()
        .any(|x| x.to_lowercase() == normalized);
    let operator_ready = policy.enabled
        && policy.operator_toggle_enabled
        && policy.mode == "operator"
        && policy.operator_scope == "exact_general_gpt55_same_class_only";
    let would_execute = operator_ready && allowed && !hard_denied;
    let reason = if hard_denied {
        "hard_denied_intent"
    } else if !operator_ready {
        "operator_disabled_or_scope_invalid"
    } else if !allowed {
        "intent_not_allowed"
    } else {
        "operator_exact_general_allowed"
    };
    RouteEnforceDecisionCore {
        schema: "PGGArchonRouteEnforceDecisionCore/v1".to_string(),
        would_execute,
        reason: reason.to_string(),
        rollback_required: would_execute,
        boundary: "Rust policy evaluator is additive and provider-free; legal/audit/AGI hard-deny must remain enforced outside this crate too.".to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    #[test]
    fn manifest_gap_lifecycle_separates_active_from_policy_boundary() {
        let signals = vec![
            ManifestGapSignal {
                key: "latest_partial".into(),
                status: "PARTIAL_SCAFFOLD_PLAN_PASS_EXECUTION_BLOCKED_BY_GPT55_502".into(),
                boundary: "active execution blocked".into(),
                lifecycle_hint: None,
            },
            ManifestGapSignal {
                key: "latest_optional".into(),
                status: "PASS_OPTIONAL_GATE_REGISTERED_DEFAULT_OFF".into(),
                boundary: "Optional default-off policy boundary; not runtime takeover.".into(),
                lifecycle_hint: None,
            },
            ManifestGapSignal {
                key: "latest_old".into(),
                status: "PARTIAL_OLD".into(),
                boundary: "superseded by newer evidence".into(),
                lifecycle_hint: Some(GapResolutionKind::Superseded),
            },
        ];
        let c = classify_manifest_gaps(&signals);
        assert_eq!(c.status, "WATCH");
        assert_eq!(c.active_keys, vec!["latest_partial"]);
        assert_eq!(c.resolved_or_policy_count, 2);
        assert!(c.boundary.contains("does not mutate Manifest"));
    }

    #[test]
    fn manifest_gap_lifecycle_passes_when_only_boundaries_remain() {
        let signals = vec![
            ManifestGapSignal {
                key: "latest_batch".into(),
                status: "PASS_BATCH_CANARY_10_EXACT_GENERAL_DENY_3_ROLLBACK".into(),
                boundary: "Batch canary only; not global route-enforce.".into(),
                lifecycle_hint: None,
            },
            ManifestGapSignal {
                key: "latest_promptfoo".into(),
                status: "PASS_DISCOVERY_AND_MANUAL_RUN_DEFAULT_OFF".into(),
                boundary: "Manual run only; policy boundary.".into(),
                lifecycle_hint: Some(GapResolutionKind::PolicyBoundary),
            },
        ];
        let c = classify_manifest_gaps(&signals);
        assert_eq!(c.status, "PASS");
        assert_eq!(c.active_gap_count, 0);
        assert_eq!(c.resolved_or_policy_count, 2);
    }

    #[test]
    fn fallback_taxonomy_never_counts_cross_class_as_same_class() {
        let cross = classify_fallback_outcome("gpt55", Some("deepseek"), false, true, false);
        assert_eq!(
            cross.kind,
            FallbackOutcomeKind::CrossClassFallbackParticipation
        );
        assert!(!cross.counts_as_primary);
        assert!(!cross.counts_as_same_class_substitution);
        let same = classify_fallback_outcome("gpt55", Some("gpt55_backup"), false, true, true);
        assert_eq!(same.kind, FallbackOutcomeKind::SameClassSubstitutionSuccess);
        assert!(same.counts_as_same_class_substitution);
    }

    #[test]
    fn route_enforce_core_hard_denies_agi_even_when_operator_on() {
        let policy = RouteEnforcePolicy {
            enabled: true,
            mode: "operator".into(),
            operator_toggle_enabled: true,
            operator_scope: "exact_general_gpt55_same_class_only".into(),
            hard_denied_intents: vec!["legal".into(), "audit".into(), "agi".into()],
            allowed_intents: vec!["exact".into(), "general".into(), "agi".into()],
        };
        let denied = evaluate_route_enforce_core(&policy, "agi");
        assert!(!denied.would_execute);
        assert_eq!(denied.reason, "hard_denied_intent");
        let allowed = evaluate_route_enforce_core(&policy, "exact");
        assert!(allowed.would_execute);
        assert!(allowed.rollback_required);
    }

    fn providers() -> Vec<ProviderState> {
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
                health: 0.85,
                quality: 0.74,
                schema_reliability: 0.60,
                cost_efficiency: 0.90,
                latency_score: 0.76,
                compliance: 0.68,
                recent_failure_debt: 0.20,
                cooldown_until_epoch_ms: Some(9_999),
                model_lock: None,
                supports_responses: false,
                supports_legal: false,
                supports_coding: true,
                supports_evolution: false,
            },
        ]
    }

    #[test]
    fn legal_responses_route_selects_gpt() {
        let req = RouteRequest {
            task: TaskClass::Legal,
            now_epoch_ms: 1,
            preferred_model: None,
            require_responses_api: true,
            require_legal_gate: true,
            require_evolution_gate: false,
        };
        let d = decide_route(&req, &providers());
        assert_eq!(d.selected_provider.as_deref(), Some("gpt55"));
        assert!(d
            .blocked
            .iter()
            .any(|b| b.contains("deepseek:responses_required")));
    }

    #[test]
    fn coding_route_avoids_cooldown_and_sorts_chain() {
        let req = RouteRequest {
            task: TaskClass::Coding,
            now_epoch_ms: 1,
            preferred_model: None,
            require_responses_api: false,
            require_legal_gate: false,
            require_evolution_gate: false,
        };
        let d = decide_route(&req, &providers());
        assert_ne!(d.selected_provider.as_deref(), Some("minimax"));
        assert!(d.blocked.iter().any(|b| b.contains("minimax:cooldown")));
        assert!(!d.fallback_chain.is_empty());
    }

    #[test]
    fn rtk_preserves_legal_and_error_anchors() {
        let mut input =
            String::from("《民法典》第五百七十七条 证据A /Users/appleoppa/x.rs:12 ERROR panic\n");
        for i in 0..300 {
            input.push_str(&format!("noise line {i}\n"));
        }
        let (out, stats) = evidence_preserving_rtk(&input);
        assert!(out.contains("第五百七十七条"));
        assert!(out.contains("ERROR"));
        assert!(!stats.preserved_anchors.is_empty());
    }

    #[test]
    fn order_influence_bounds_route_score() {
        let req = RouteRequest {
            task: TaskClass::Evolution,
            now_epoch_ms: 1,
            preferred_model: None,
            require_responses_api: true,
            require_legal_gate: false,
            require_evolution_gate: true,
        };
        let order = OrderFactors {
            he_tu_luo_shu: 0.96,
            tao_te_ching: 0.95,
            i_ching: 0.92,
            huang_di: 0.90,
            gan_zhi: 0.88,
            wu_xing: 0.91,
            bagua: 0.89,
            defect_rate: 0.08,
        };
        let d = decide_route_with_order(&req, &providers(), &order);
        assert_eq!(d.selected_provider.as_deref(), Some("gpt55"));
        assert!(d.score >= 0.0 && d.score <= 1.0);
        let influence = order_influence(&order);
        assert_eq!(influence.schema, "PGGArchonOrderInfluence/v1");
        assert!(influence.he_tu_luo_shu > 0.9);
        assert!(influence.route_multiplier > 0.0 && influence.route_multiplier <= 1.05);
    }

    proptest! {
        #[test]
        fn score_is_bounded_for_any_finite_inputs(v in proptest::collection::vec(-10.0f64..10.0, 8)) {
            let p = ProviderState { id: "p".into(), kind: ProviderKind::Compatible, health: v[0], quality: v[1], schema_reliability: v[2], cost_efficiency: v[3], latency_score: v[4], compliance: v[5], recent_failure_debt: v[6], cooldown_until_epoch_ms: None, model_lock: None, supports_responses: true, supports_legal: true, supports_coding: true, supports_evolution: true };
            let req = RouteRequest { task: TaskClass::General, now_epoch_ms: 0, preferred_model: None, require_responses_api: false, require_legal_gate: false, require_evolution_gate: false };
            let s = route_score(&p, &req);
            prop_assert!(s >= -0.25 && s <= 1.0);
        }
    }
}
