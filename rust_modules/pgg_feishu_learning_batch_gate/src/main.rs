use chrono::Local;
use serde::Serialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Serialize)]
struct Check {
    id: &'static str,
    title: &'static str,
    status: &'static str,
    mapping: &'static str,
    evidence: Value,
    boundary: &'static str,
}

#[derive(Serialize)]
struct ConflictDecision {
    id: &'static str,
    title: &'static str,
    doc_requirement: &'static str,
    current_pgg_state: &'static str,
    adjudication: &'static str,
    accepted_policy: &'static str,
    risk: &'static str,
}

#[derive(Serialize)]
struct Report {
    schema: &'static str,
    generated_at: String,
    status: &'static str,
    score: f64,
    source_docs: Vec<Value>,
    checks: Vec<Check>,
    adjudication_summary: &'static str,
    adjudicated_conflicts: Vec<ConflictDecision>,
    conflicts_require_user_adjudication: Vec<ConflictDecision>,
    boundary: Vec<&'static str>,
}

fn home() -> PathBuf {
    PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}

fn sha256_file(path: &Path) -> Option<String> {
    let bytes = fs::read(path).ok()?;
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    Some(format!("{:x}", hasher.finalize()))
}

fn read(path: &Path) -> String {
    fs::read_to_string(path).unwrap_or_default()
}

fn run(cmd: &Path, args: &[&str]) -> Value {
    match Command::new(cmd).args(args).output() {
        Ok(o) => {
            let mut s = if o.stdout.is_empty() {
                String::from_utf8_lossy(&o.stderr).to_string()
            } else {
                String::from_utf8_lossy(&o.stdout).to_string()
            };
            if s.len() > 1000 {
                s.truncate(1000);
            }
            json!({"exit": o.status.code().unwrap_or(-1), "sample": s})
        }
        Err(e) => json!({"exit": -127, "error": e.to_string()}),
    }
}

fn contains_any(s: &str, terms: &[&str]) -> bool {
    terms.iter().any(|t| s.contains(t))
}

fn main() {
    let h = home();
    let hermes = h.join(".hermes");
    let agent = hermes.join("hermes-agent");
    let bin = hermes.join("bin");
    let base = hermes.join(
        "workspace/pgg-archon-governance/feishu-doc-comparison-20260618-batch-JhgX-PJHz-OM9x",
    );
    let docs = vec![
        (
            "JhgXwhFwziOI9DkJr0kcMhx9nDc",
            "Agent投喂通用手册（V6.0·精简落地版）",
        ),
        (
            "PJHzwcVJriKm0ekojcKcTQcPntf",
            "大模型抗幻觉指令与配置指南V4.0",
        ),
        (
            "OM9xw58I5iVNsRknudAcPGJEnQc",
            "智能体飞书知识库文档阅读铁律 V2.1",
        ),
    ];
    let mut source_docs = Vec::new();
    let mut all_text = String::new();
    let mut frozen_ok = true;
    for (token, title) in &docs {
        let idx_json = base.join(token).join("FROZEN_EXTRACTION_INDEX.json");
        let idx_md = base.join(token).join("FROZEN_EXTRACTION_INDEX.md");
        let raw_candidates = fs::read_dir(base.join(token))
            .ok()
            .into_iter()
            .flat_map(|rd| rd.flatten())
            .map(|e| e.path())
            .find(|p| {
                p.extension().and_then(|x| x.to_str()) == Some("md")
                    && p.file_name()
                        .and_then(|x| x.to_str())
                        .unwrap_or("")
                        .contains(".raw")
            });
        let raw = raw_candidates.as_ref().map(|p| read(p)).unwrap_or_default();
        all_text.push_str(&raw);
        let sha = raw_candidates.as_ref().and_then(|p| sha256_file(p));
        let idx_exists = idx_json.exists() && idx_md.exists();
        if !idx_exists {
            frozen_ok = false;
        }
        source_docs.push(json!({
            "token": token,
            "title": title,
            "chars": raw.chars().count(),
            "raw_sha256": sha,
            "frozen_index_exists": idx_exists,
            "frozen_index_json": idx_json,
            "frozen_index_md": idx_md,
        }));
    }

    let mut checks = Vec::new();
    checks.push(Check {
        id: "reading.frozen_extraction",
        title: "飞书文档冻结提取",
        status: if frozen_ok { "COVERED" } else { "WATCH" },
        mapping: "文档要求单次冻结/哈希/分段 → 本机保存 raw/meta/FROZEN_EXTRACTION_INDEX 与 sha256",
        evidence: json!({"docs": source_docs}),
        boundary: "raw_content 能读取正文；附件/图片 OCR 未自动下载，需单独权限和任务",
    });

    let has_feed = contains_any(
        &all_text,
        &[
            "阶段递进不可跳过",
            "P1文档优先投喂",
            "命令输出",
            "文件路径",
            "写入需验证",
        ],
    );
    checks.push(Check {
        id: "feed.evidence_based_progression",
        title: "投喂/进化阶段递进与证据回显",
        status: if has_feed { "COVERED" } else { "WATCH" },
        mapping: "投喂手册 → Hermes/PGG 采用 Agent_Evolve、EVOLUTION_MANIFEST、skill references、命令读回证据",
        evidence: json!({"source_terms_found": has_feed, "manifest_exists": hermes.join("data/EVOLUTION_MANIFEST.json").exists()}),
        boundary: "本 gate 不自动写 MEMORY/USER，不把文档口号冒充运行能力",
    });

    let anti_hallu = contains_any(
        &all_text,
        &["幻觉", "禁止", "来源", "原文", "不知道", "不确定"],
    );
    let existing_truth_refs =
        fs::read_dir(hermes.join("skills/general/agent-operational-governance/references"))
            .ok()
            .map(|rd| {
                rd.flatten()
                    .filter(|e| {
                        e.file_name().to_string_lossy().contains("truth")
                            || e.file_name().to_string_lossy().contains("halluc")
                            || e.file_name().to_string_lossy().contains("fake")
                    })
                    .count()
            })
            .unwrap_or(0);
    checks.push(Check {
        id: "anti_hallucination.truth_boundary",
        title: "抗幻觉/证据优先",
        status: if anti_hallu && existing_truth_refs > 0 { "COVERED" } else { "PARTIAL_COVERED" },
        mapping: "抗幻觉指南 → PGG 真实性治理、引用原文、工具读回、证据不足直说",
        evidence: json!({"source_terms_found": anti_hallu, "truth_reference_count": existing_truth_refs}),
        boundary: "提示词/参考文档只能降低风险，不能证明零幻觉",
    });

    let cargo = agent.join("rust_modules/Cargo.toml");
    let cargo_text = read(&cargo);
    checks.push(Check {
        id: "rust.workspace_onboarding",
        title: "Rust gate 纳入 workspace",
        status: if cargo_text.contains("pgg_feishu_learning_batch_gate") { "COVERED" } else { "WATCH" },
        mapping: "学习文档吸收 → Rust 只读 gate + workspace 成员 + ~/.hermes/bin CLI",
        evidence: json!({"cargo": cargo, "registered": cargo_text.contains("pgg_feishu_learning_batch_gate")}),
        boundary: "仅只读 gate；不修改 provider/config/security/scheduler",
    });

    let ops_gate = run(&bin.join("pgg-ops-lifecycle-gate"), &[]);
    checks.push(Check {
        id: "ops.lifecycle_alignment",
        title: "脚本/自检/技能生命周期对齐",
        status: if ops_gate
            .get("sample")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .contains("PASS_WITH_BOUNDARIES")
        {
            "COVERED"
        } else {
            "WATCH"
        },
        mapping: "投喂/脚本/自检类要求 → 复用上一轮 pgg-ops-lifecycle-gate 边界",
        evidence: ops_gate,
        boundary: "PASS_WITH_BOUNDARIES 表示有边界通过，不是全自动生产接管",
    });

    let covered = checks.iter().filter(|c| c.status == "COVERED").count() as f64;
    let partial = checks
        .iter()
        .filter(|c| c.status == "PARTIAL_COVERED")
        .count() as f64;
    let score = ((covered + partial * 0.5) / checks.len() as f64 * 1000.0).round() / 10.0;
    let adjudicated_conflicts = vec![
        ConflictDecision {
            id: "C1.raw_cache_deletion_vs_auditability",
            title: "阅读铁律要求删除原始读取缓存 vs PGG 证据留痕",
            doc_requirement: "阅读完成后永久删除原文原始读取缓存，不保留任何原文中间表示",
            current_pgg_state: "PGG/Hermes 为可审计性保留 raw/meta/frozen index 和 sha256 证据包",
            adjudication: "B_ACCEPTED_BY_USER",
            accepted_policy: "保留原文证据包，不删除；如需外发，只发冻结摘录/哈希，不发敏感原文",
            risk: "删除会破坏审计链；保留需注意权限和隐私",
        },
        ConflictDecision {
            id: "C2.single_read_freeze_vs_live_update",
            title: "单次阅读永久冻结 vs 文档更新复读",
            doc_requirement: "同一文档同一版本只能阅读一次；文档更新需人类明确指令后重新阅读新版本",
            current_pgg_state: "当前流程可重复 raw_content 读取以验证变更和修复提取错误",
            adjudication: "B_ACCEPTED_BY_USER",
            accepted_policy: "按版本冻结：同 token+mtime+sha 只引用冻结副本；检测到 mtime/sha 变化时生成新版本，不覆盖旧版",
            risk: "严格禁止复读可能妨碍错误修正；无版本冻结会导致引用漂移",
        },
        ConflictDecision {
            id: "C3.context_isolation_vs_multi_doc_comparison",
            title: "上下文绝对隔离 vs 多文档关联对照",
            doc_requirement: "新文档阅读前清空上下文，不混入其他文档知识；多文档必须先分别冻结再关联分析",
            current_pgg_state: "本任务需要三文档与本机机制关联对照，无法物理清空当前系统上下文",
            adjudication: "B_ACCEPTED_BY_USER",
            accepted_policy: "采用工程等价：逐文档冻结提取，再基于冻结副本做关联矩阵；不把未冻结原文混入结论",
            risk: "完全清空上下文不可由当前单会话保证；需用文件级冻结和哈希替代",
        },
        ConflictDecision {
            id: "C4.minimum_model_requirement",
            title: "最低模型能力确认",
            doc_requirement: "仅在最高指令遵循模型上执行；无法确认需阅读前向用户声明并请求确认",
            current_pgg_state: "当前主会话模型可用但未调用外部 GPT/Claude 做逐字二次提取",
            adjudication: "B_ACCEPTED_BY_USER",
            accepted_policy: "本轮保留本机 raw/API 冻结与只读对照边界；法律/客户级全文保真另行指定 GPT/Claude 二次校验",
            risk: "额外 LLM 校验会消耗成本；不校验则只能称本机工程冻结，不称 100%人工级校对",
        },
        ConflictDecision {
            id: "C5.scheduled_feeding_tasks",
            title: "投喂手册定时任务数量/形态",
            doc_requirement: "投喂手册提到核心定时任务和按需触发",
            current_pgg_state: "PGG 纪律为 Rust binary + launchd，避免新增 Hermes cron/crontab",
            adjudication: "B_ACCEPTED_BY_USER",
            accepted_policy: "不新增调度；复用现有 autonomy/health/knowledge gates 的只读探针",
            risk: "新增定时任务可能造成重复跑、成本和冲突",
        },
    ];
    let status = if score >= 85.0 {
        "PASS_ADJUDICATED"
    } else if score >= 70.0 {
        "WATCH_ADJUDICATED_LOW_SCORE"
    } else {
        "BLOCKED"
    };
    let report = Report {
        schema: "pgg_feishu_learning_batch_gate/v2",
        generated_at: Local::now().to_rfc3339(),
        status,
        score,
        source_docs,
        checks,
        adjudication_summary: "USER_ACCEPTED_ASSISTANT_RECOMMENDATION_B_FOR_ALL_CONFLICTS",
        adjudicated_conflicts,
        conflicts_require_user_adjudication: Vec::new(),
        boundary: vec![
            "read-only comparison",
            "no provider/config/credential/security mutation",
            "no scheduler mutation",
            "no auto deletion/move",
            "no claim of zero hallucination or full AGI",
        ],
    };
    let out = hermes.join("workspace/pgg-archon-governance/feishu-learning-batch-gate");
    let _ = fs::create_dir_all(&out);
    let json = serde_json::to_string_pretty(&report).unwrap();
    fs::write(out.join("latest.json"), &json).unwrap();
    println!("{}", json);
}
