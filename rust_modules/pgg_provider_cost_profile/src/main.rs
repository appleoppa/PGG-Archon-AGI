use serde::Serialize;
use std::path::PathBuf;

/// 总纲8 吸收 Phase 1B: Provider 成本画像门禁
/// 为6个 provider 挂载 资源类型/K_res/ΔC_inf/付费模式
/// Rust native, zero LLM, zero network, shadow mode only

// 资源类型枚举 (总纲8 §1.5)
#[derive(Serialize)]
#[serde(rename_all = "snake_case")]
enum ResType {
    FreeOpen,    // 开源本地永久免费
    FreeQuota,   // 限时免费额度API（剩余未知）
    PayAsGo,     // 按量付费API
    PayPackage,  // 包年包月/专属实例
    EdgeLocal,   // 边缘离线部署
}

// 推理形态枚举 (总纲8 §1.4)
#[derive(Serialize)]
#[serde(rename_all = "snake_case")]
enum InfType {
    CodeInf,   // 代码/本地算子推理
    TextInf,   // LLM原生文本推理
    FuncInf,   // 函数调用/工具链推理
}

// 成本系数 K_res (总纲8 §2.3)
// k0 < k1 < k4 < k2 < k3
const K_FREE_OPEN: f64 = 0.10;
const K_FREE_QUOTA: f64 = 0.30;
const K_EDGE_LOCAL: f64 = 0.40;
const K_PAY_AS_GO: f64 = 1.00;
const K_PAY_PACKAGE: f64 = 0.85; // 包月 sunk cost, 边际成本低于按量

// 推理形态附加开销 ΔC_inf (总纲8 §2.4)
// δ0 < δ1 < δ2
const D_CODE: f64 = 0.05;
const D_TEXT: f64 = 0.15;
const D_FUNC: f64 = 0.30;

#[derive(Serialize)]
struct ProviderCostProfile {
    provider: String,
    display_name: String,
    res_type: ResType,
    inf_type: InfType,
    k_res: f64,
    delta_c_inf: f64,
    cost_tier_estimate: String, // L / M / H
    notes: String,
}

#[derive(Serialize)]
struct CostProfileReport {
    schema: String,
    timestamp: String,
    profiles: Vec<ProviderCostProfile>,
    global_cost_order: Vec<String>,
    boundary: String,
    recommendations: Vec<String>,
}

fn home_dir() -> PathBuf {
    PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}

fn latest_json_path() -> PathBuf {
    home_dir().join(".hermes/data/provider_cost_profile_latest.json")
}

fn iso_timestamp() -> String {
    std::process::Command::new("date")
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

fn make_profile(
    provider: &str,
    display: &str,
    res_type: ResType,
    inf_type: InfType,
    k_res: f64,
    delta: f64,
    notes: &str,
) -> ProviderCostProfile {
    let cost = k_res + delta;
    let tier = if cost < 0.40 {
        "L".to_string()
    } else if cost < 0.80 {
        "M".to_string()
    } else {
        "H".to_string()
    };

    ProviderCostProfile {
        provider: provider.to_string(),
        display_name: display.to_string(),
        res_type,
        inf_type,
        k_res,
        delta_c_inf: delta,
        cost_tier_estimate: tier,
        notes: notes.to_string(),
    }
}

fn build_profiles() -> Vec<ProviderCostProfile> {
    vec![
        make_profile(
            "ark",
            "Ark (火山引擎)",
            ResType::FreeQuota,
            InfType::TextInf,
            K_FREE_QUOTA,
            D_TEXT,
            "默认主LLM；免费额度API，剩余额度未追踪。建议设置cap监控。",
        ),
        make_profile(
            "gpt55",
            "GPT-5.5",
            ResType::PayAsGo,
            InfType::TextInf,
            K_PAY_AS_GO,
            D_TEXT,
            "高成本主力审计模型；仅用于explicit审计/进化/复杂判断。",
        ),
        make_profile(
            "claude",
            "Claude Opus 4.6",
            ResType::PayAsGo,
            InfType::TextInf,
            K_PAY_AS_GO,
            D_TEXT,
            "高成本合规审计模型；仅用于explicit第三方审计/价值网络。",
        ),
        make_profile(
            "deepseek",
            "DeepSeek V4",
            ResType::PayAsGo,
            InfType::TextInf,
            K_PAY_AS_GO,
            D_TEXT,
            "用户指定贵；仅静态链fallback或explicit criminal/civil。",
        ),
    ]
}

fn order_by_cost(profiles: &[ProviderCostProfile]) -> Vec<String> {
    let mut pairs: Vec<(f64, &str)> = profiles
        .iter()
        .map(|p| (p.k_res + p.delta_c_inf, p.provider.as_str()))
        .collect();
    pairs.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
    pairs.iter().map(|(_, name)| name.to_string()).collect()
}

fn generate_recommendations(profiles: &[ProviderCostProfile], order: &[String]) -> Vec<String> {
    let mut recs = Vec::new();

    let cheapest = &order[0];
    let most_expensive = &order[order.len() - 1];

    recs.push(format!(
        "成本最低: {} (k_res+ΔC_inf={:.2}) — 适合简单/低风险任务",
        cheapest,
        profiles.iter().find(|p| p.provider == *cheapest).map(|p| p.k_res + p.delta_c_inf).unwrap_or(0.0)
    ));
    recs.push(format!(
        "成本最高: {} (k_res+ΔC_inf={:.2}) — 仅用于高风险/复杂/审计任务",
        most_expensive,
        profiles.iter().find(|p| p.provider == *most_expensive).map(|p| p.k_res + p.delta_c_inf).unwrap_or(0.0)
    ));

    // 推荐路由成本优化
    let payg_count = profiles.iter().filter(|p| matches!(p.res_type, ResType::PayAsGo)).count();
    if payg_count > 0 {
        recs.push(format!(
            "有 {} 个PayAsGo provider — 自动降级链中应优先走包月/免费provider",
            payg_count
        ));
    }

    recs.push("当前成本追踪缺失: ResQuota(剩余额度) 全部标记为 unknown — 建议后续接入额度监控".to_string());
    recs.push("边界: shadow mode cost estimate; not production routing; does not replace OmniRoute decisions".to_string());

    recs
}

fn main() {
    let profiles = build_profiles();
    let cost_order = order_by_cost(&profiles);
    let recommendations = generate_recommendations(&profiles, &cost_order);

    let report = CostProfileReport {
        schema: "pgg-provider-cost-profile/v1".to_string(),
        timestamp: iso_timestamp(),
        profiles,
        global_cost_order: cost_order,
        boundary: "Local deterministic metadata; no LLM, no network; shadow mode - does not alter routing. Cost coefficients are user-configured estimates, not real billing data. Not AGI/T5/ASI/external benchmark.".to_string(),
        recommendations,
    };

    let json = serde_json::to_string_pretty(&report).unwrap_or_default();
    println!("{}", json);

    if let Err(e) = std::fs::write(latest_json_path(), &json) {
        eprintln!("WARN: failed to write latest.json: {}", e);
    }
}
