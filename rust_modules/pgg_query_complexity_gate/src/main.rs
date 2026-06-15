use serde::Serialize;
use std::path::PathBuf;
use std::io::Read;

/// 总纲8 吸收 Phase 1A: Query 复杂度评分门禁
/// 4 维度评分 → Score_Q (0-1) → 建议 Tier_L/M/H
/// Rust native, zero LLM, zero network, shadow mode only

const W1: f64 = 0.25; // L_q: token长度权重
const W2: f64 = 0.30; // N_e: 实体数权重
const W3: f64 = 0.25; // N_t: 主题数权重
const W4: f64 = 0.20; // D_q: 上下文深度权重

// 档位阈值
const THETA1: f64 = 0.35;
const THETA2: f64 = 0.65;

const MAX_TOKENS: f64 = 4096.0;
const MAX_ENTITIES: f64 = 20.0;
const MAX_TOPICS: f64 = 8.0;
const MAX_DEPTH: f64 = 5.0;

#[derive(Serialize)]
struct ComplexityFeatures {
    raw_token_len: usize,
    normalized_token_len: f64,
    entity_count: usize,
    normalized_entities: f64,
    topic_count: usize,
    normalized_topics: f64,
    context_depth: usize,
    normalized_depth: f64,
    has_code: bool,
    has_legal_keywords: bool,
    has_tool_request: bool,
}

#[derive(Serialize)]
struct TierResult {
    score_q: f64,
    tier_raw: String,      // L / M / H
    tier_adjusted: String,  // 经二次修正后
    features: ComplexityFeatures,
    confidence: f64,
}

#[derive(Serialize)]
struct ComplexityReport {
    schema: String,
    timestamp: String,
    query_preview: String,
    result: TierResult,
    boundary: String,
}

fn home_dir() -> PathBuf {
    PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}

fn latest_json_path() -> PathBuf {
    home_dir().join(".hermes/data/query_complexity_latest.json")
}

fn iso_timestamp() -> String {
    std::process::Command::new("date")
        .arg("+%Y-%m-%dT%H:%M:%S%z")
        .output()
        .ok()
        .and_then(|o| if o.status.success() { String::from_utf8(o.stdout).ok() } else { None })
        .unwrap_or_else(|| "unknown".to_string())
        .trim().to_string()
}

/// 估算 Token 数（按中文:英文 ≈ 1.5:1 粗略）
fn estimate_tokens(text: &str) -> usize {
    let chinese_chars = text.chars().filter(|c| ('\u{4e00}'..='\u{9fff}').contains(c)).count();
    let other_chars = text.len().saturating_sub(chinese_chars * 3); // UTF-8 bytes minus Chinese
    // 中文 ~1.5 token/char, 英文 ~0.25 token/char
    (chinese_chars as f64 * 1.5 + other_chars as f64 * 0.25) as usize
}

/// 估算实体数: 数字/日期/金额/组织名/人名 模式
fn estimate_entities(text: &str) -> usize {
    let mut count = 0;
    // 金额: ¥/$/￥+数字
    count += text.split_whitespace().filter(|w| w.contains('¥') || w.contains("￥") || w.contains('$') || w.starts_with("金额")).count();
    // 日期: YYYY年-MM-DD 或 YYYY-MM-DD
    count += text.split_whitespace().filter(|w| w.contains("年") || w.contains('-')).count();
    // 数字提取
    count += text.split_whitespace().filter(|w| w.chars().any(|c| c.is_ascii_digit()) && w.len() >= 4).count();
    // 法律特有: 法/案/号/院
    count += text.split_whitespace().filter(|w| w.contains("法") || w.contains("案") || w.contains("号")).count();
    count
}

/// 估算主题数: 常见法律/技术主题关键词
fn estimate_topics(text: &str) -> usize {
    let topics = [
        "合同", "纠纷", "诉讼", "仲裁", "执行", "赔偿", "违约", "侵权",
        "离婚", "继承", "刑事", "行政", "知识产权", "公司法", "劳动",
        "代码", "bug", "deploy", "config", "API", "数据库",
        "路由", "门禁", "进化", "备份", "恢复",
    ];
    let lower = text.to_lowercase();
    topics.iter().filter(|t| lower.contains(*t)).count()
}

/// 估算上下文深度: 引用的文件/案例/法条数
fn estimate_depth(text: &str) -> usize {
    let mut depth = 0;
    // 引用法条: "第X条" 或 "《》"
    depth += text.matches("第").count();
    depth += text.matches("《").count();
    // 引用文件路径: /
    depth += text.matches('/').count() / 2;
    // 代码块标记
    depth += text.matches("```").count() / 2;
    depth.min(MAX_DEPTH as usize)
}

fn has_code(text: &str) -> bool {
    text.contains("```") || text.contains("fn ") || text.contains("def ") || text.contains("->")
}

fn has_legal_keywords(text: &str) -> bool {
    let keywords = ["合同法", "民法典", "刑法", "诉讼法", "司法解释", "指导案例", "管辖", "上诉", "判决", "合同纠纷", "违约金", "赔偿", "起诉状", "违约", "侵权", "仲裁", "保全", "担保", "债权"];
    keywords.iter().any(|k| text.contains(k))
}

fn has_tool_request(text: &str) -> bool {
    let keywords = ["执行", "运行", "部署", "配置", "安装", "启动", "create", "write", "修改"];
    keywords.iter().any(|k| text.contains(k))
}

fn analyze_query(text: &str) -> TierResult {
    let raw_token_len = estimate_tokens(text);
    let entity_count = estimate_entities(text);
    let topic_count = estimate_topics(text);
    let context_depth = estimate_depth(text);

    let normalized_token_len = (raw_token_len as f64 / MAX_TOKENS).clamp(0.0, 1.0);
    let normalized_entities = (entity_count as f64 / MAX_ENTITIES).clamp(0.0, 1.0);
    let normalized_topics = (topic_count as f64 / MAX_TOPICS).clamp(0.0, 1.0);
    let normalized_depth = (context_depth as f64 / MAX_DEPTH).clamp(0.0, 1.0);

    let score_q = W1 * normalized_token_len + W2 * normalized_entities
        + W3 * normalized_topics + W4 * normalized_depth;

    let tier_raw = if score_q < THETA1 {
        "L".to_string()
    } else if score_q < THETA2 {
        "M".to_string()
    } else {
        "H".to_string()
    };

    // 二次修正: 含代码/法律关键词或工具调用 → 升一档
    let c = has_code(text);
    let l = has_legal_keywords(text);
    let t = has_tool_request(text);
    let boost = (c as i32 + l as i32 + t as i32) as f64 * 0.15;

    let score_adjusted = (score_q + boost).min(1.0);
    let tier_adjusted = if score_adjusted < THETA1 {
        "L".to_string()
    } else if score_adjusted < THETA2 {
        "M".to_string()
    } else {
        "H".to_string()
    };

    // 置信度: 基于特征完整度
    let features_present = (raw_token_len > 0) as u32 + (entity_count > 0) as u32
        + (topic_count > 0) as u32 + (context_depth > 0) as u32;
    let confidence = 0.5 + features_present as f64 * 0.125;

    let features = ComplexityFeatures {
        raw_token_len,
        normalized_token_len,
        entity_count,
        normalized_entities,
        topic_count,
        normalized_topics,
        context_depth,
        normalized_depth,
        has_code: c,
        has_legal_keywords: l,
        has_tool_request: t,
    };

    TierResult {
        score_q,
        tier_raw,
        tier_adjusted,
        features,
        confidence,
    }
}

fn main() {
    // 从 stdin 读取 query
    let mut input = String::new();
    std::io::stdin().read_to_string(&mut input).unwrap_or_default();
    let query = input.trim();

    let (query_text, query_preview) = if query.is_empty() {
        // fallback: 从 args 读
        let args: Vec<String> = std::env::args().skip(1).collect();
        let combined = args.join(" ");
        if combined.is_empty() {
            eprintln!("Usage: echo '<query>' | pgg_query_complexity_gate");
            std::process::exit(1);
        }
        let preview = if combined.len() > 120 {
            format!("{}...", &combined[..120])
        } else {
            combined.clone()
        };
        (combined, preview)
    } else {
        let preview = if query.len() > 120 {
            format!("{}...", &query[..120])
        } else {
            query.to_string()
        };
        (query.to_string(), preview)
    };

    let result = analyze_query(&query_text);
    let report = ComplexityReport {
        schema: "pgg-query-complexity-gate/v1".to_string(),
        timestamp: iso_timestamp(),
        query_preview,
        result,
        boundary: "Local deterministic computation; no LLM, no network; shadow mode - does not alter routing. Not AGI/T5/ASI/external benchmark.".to_string(),
    };

    let json = serde_json::to_string_pretty(&report).unwrap_or_default();
    println!("{}", json);

    // 写入 latest.json
    if let Err(e) = std::fs::write(latest_json_path(), &json) {
        eprintln!("WARN: failed to write latest.json: {}", e);
    }
}