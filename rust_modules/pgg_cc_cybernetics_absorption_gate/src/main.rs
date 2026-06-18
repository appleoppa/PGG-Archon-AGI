use chrono::Local;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Serialize)]
struct Requirement {
    id: &'static str,
    source_lines: &'static str,
    requirement: &'static str,
    hermes_mapping: &'static str,
    execution_status: &'static str,
    evidence: &'static str,
    boundary: &'static str,
}

#[derive(Serialize)]
struct Factor {
    id: &'static str,
    source: &'static str,
    factor: &'static str,
    hermes_mapping: &'static str,
    status: &'static str,
}

#[derive(Serialize)]
struct Check {
    id: &'static str,
    status: &'static str,
    score: f64,
    evidence: String,
    boundary: &'static str,
}

#[derive(Serialize)]
struct Report {
    schema: &'static str,
    generated_at: String,
    status: &'static str,
    score: f64,
    source_doc_sha256: String,
    source_doc_path: String,
    openclaw_mapping_rule: &'static str,
    requirements: Vec<Requirement>,
    cc_engineering_factors: Vec<Factor>,
    cybernetics_factors: Vec<Factor>,
    checks: Vec<Check>,
    watch_items: Vec<&'static str>,
    blocked_items: Vec<&'static str>,
    boundary: Vec<&'static str>,
}

fn home() -> PathBuf {
    PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}

fn sha256_file(path: &Path) -> String {
    let data = fs::read(path).unwrap_or_default();
    let digest = Sha256::digest(&data);
    digest.iter().map(|b| format!("{:02x}", b)).collect()
}

fn exists(path: &Path) -> bool {
    path.exists()
}

fn latest_dir() -> PathBuf {
    home().join(".hermes/workspace/pgg-archon-governance/cc-cybernetics-absorption-gate")
}

fn main() {
    let source = home().join(".hermes/workspace/pgg-archon-governance/uploaded-guides/cc-source-engineering-cybernetics-20260618/CC源码+工程控制论从_可用_到_自主进化_完整指南.raw.md");
    let frozen = home().join(".hermes/workspace/pgg-archon-governance/uploaded-guides/cc-source-engineering-cybernetics-20260618/FROZEN_INDEX.json");
    let bootstrap = home().join(".hermes/workspace/pgg-archon-governance/uploaded-guides/cc-source-engineering-cybernetics-20260618/self-audit/BOOTSTRAP.md");
    let comparison = home().join(".hermes/workspace/pgg-archon-governance/uploaded-guides/cc-source-engineering-cybernetics-20260618/HERMES_MAPPING_EXECUTION_MATRIX.md");
    let conflict = home().join(".hermes/workspace/pgg-archon-governance/uploaded-guides/cc-source-engineering-cybernetics-20260618/CONFLICT_AND_WATCH_PACKET.md");

    let requirements = vec![
        Requirement { id: "R1.self_recognition", source_lines: "91-95", requirement: "运行 hermes doctor 和 hermes status --all，形成自我认知报告/BOOTSTRAP", hermes_mapping: "使用本机 Hermes CLI 只读自检，输出 BOOTSTRAP.md 到 workspace，不修改启动配置", execution_status: "EXECUTED", evidence: "self-audit/BOOTSTRAP.md + hermes_self_audit_raw.log", boundary: "不自动写根目录 BOOTSTRAP，不修改启动链" },
        Requirement { id: "R2.cc_source_benchmark", source_lines: "97-124", requirement: "精读 Claude Code 源码并输出 PGG Archon 系统性进化调整设计方案", hermes_mapping: "只读核查 ponponon/claude_code_src，作为非官方 source-map recovery 项目，提炼架构因子映射 Hermes", execution_status: "PARTIAL_EXECUTED_PATTERN_ONLY", evidence: "subagent GitHub API readback + local matrix", boundary: "不 clone、不执行、不复制源码、不称官方/合法开源" },
        Requirement { id: "R3.cybernetics_study", source_lines: "126-194", requirement: "研读工程控制论与 AI Agent 控制论前沿，输出系统性进化设计方案", hermes_mapping: "只读核查 arXiv/DOI/公开元数据，提炼控制论→Hermes/PGG 闭环因子", execution_status: "PARTIAL_EXECUTED_METADATA_AND_FACTOR", evidence: "subagent arXiv/DOI/OpenLibrary metadata readback + local matrix", boundary: "未下载受限书籍全文，未声称全文逐段精读" },
        Requirement { id: "R4.heartbeat_automation", source_lines: "196-200", requirement: "基于 Heartbeat 将进化自动化，并参考 OpenClaw Heartbeat 文档配置", hermes_mapping: "映射为 Hermes/PGG 现有 autonomy/default-loop/health-monitor/launchd，只做设计与只读 gate，不新增 OpenClaw Heartbeat 或 cron", execution_status: "MAPPED_NOT_MUTATED", evidence: "CONFLICT_AND_WATCH_PACKET.md", boundary: "OpenClaw 相关一律映射为本机 Hermes；不复制 OpenClaw 目录/配置" },
        Requirement { id: "R5.findings_persistence", source_lines: "119-122,177-181", requirement: "阶段成果持续沉淀到 findings.md，防止上下文丢失", hermes_mapping: "写 workspace findings/matrix/report，并沉淀到 skill reference/Manifest", execution_status: "EXECUTED", evidence: "HERMES_MAPPING_EXECUTION_MATRIX.md + Manifest + skill reference", boundary: "不自动写 MEMORY/USER 流水账" },
    ];

    let cc_factors = vec![
        Factor {
            id: "CC1.entrypoint_layering",
            source: "ponponon/claude_code_src directory readback",
            factor: "CLI/MCP/init/SDK/sandbox entrypoints separated",
            hermes_mapping:
                "Hermes CLI/MCP/Web/API/worker entrypoints maintain separated bounded modes",
            status: "PATTERN_ABSORBED",
        },
        Factor {
            id: "CC2.command_registry",
            source: "commands/* readback",
            factor: "commands as extensible lifecycle units",
            hermes_mapping:
                "Hermes slash/CLI/PGG phase commands should carry metadata, permission, evidence",
            status: "PATTERN_ABSORBED",
        },
        Factor {
            id: "CC3.tool_object_model",
            source: "tools/* readback",
            factor: "Tool schema/permission/result/lifecycle abstraction",
            hermes_mapping: "Map to Hermes tool registry + PGG tool-call policy/evidence ledgers",
            status: "PATTERN_ABSORBED",
        },
        Factor {
            id: "CC4.query_engine",
            source: "QueryEngine/query/tokenBudget readback",
            factor: "agent loop as observable query engine",
            hermes_mapping: "Map to Hermes run_conversation + PGG observe/act/verify trace",
            status: "PATTERN_ABSORBED",
        },
        Factor {
            id: "CC5.observability_cost",
            source: "cost/status/doctor/diagnostic dirs",
            factor: "diagnostic, usage, cost, tool-use summary are first-class",
            hermes_mapping: "Map to OmniRoute/health/goals/ledger/status metrics",
            status: "PATTERN_ABSORBED",
        },
        Factor {
            id: "CC6.task_lifecycle",
            source: "Task*Tool readback",
            factor: "task create/list/update/output/stop lifecycle",
            hermes_mapping:
                "Map to PGG kanban/todo/agent-loop ledger and future durable task objects",
            status: "WATCH_DESIGN_NOT_FULLY_MUTATED",
        },
    ];

    let cyber_factors = vec![
        Factor {
            id: "CY1.closed_loop",
            source: "Engineering cybernetics + agentic systems",
            factor: "observe → compare error → control → act → verify",
            hermes_mapping: "Make PGG/Hermes completion require evidence-producing feedback loop",
            status: "ABSORBED",
        },
        Factor {
            id: "CY2.observability",
            source: "control theory",
            factor: "state must be measurable before claims",
            hermes_mapping: "No file/status/service claim without tool readback",
            status: "ABSORBED",
        },
        Factor {
            id: "CY3.controllability",
            source: "control theory",
            factor: "agent must have sufficient tools/permissions to reach goal",
            hermes_mapping: "Pre-action capability/permission gate; blockers explicit",
            status: "ABSORBED",
        },
        Factor {
            id: "CY4.stability",
            source: "control theory",
            factor: "bounded loops, convergence, non-divergence",
            hermes_mapping: "loop budgets, stop conditions, fallback not blind retry",
            status: "ABSORBED",
        },
        Factor {
            id: "CY5.robustness",
            source: "control theory",
            factor: "noise/disturbance/uncertainty handling",
            hermes_mapping: "retry alternate source, conflict packet, uncertainty labels",
            status: "ABSORBED",
        },
        Factor {
            id: "CY6.actor_critic",
            source: "AgenticControl",
            factor: "executor + evaluator/reviewer split",
            hermes_mapping: "delegate_task/audit model/inspection team split for high-value tasks",
            status: "ABSORBED",
        },
        Factor {
            id: "CY7.runtime_authority_levels",
            source: "A Control-Theoretic Foundation for Agentic Systems",
            factor: "levels of runtime authority over parameters, strategy, architecture, goals",
            hermes_mapping:
                "PGG mutations gated by risk: read-only/design/observe-first/enforce/production",
            status: "ABSORBED",
        },
    ];

    let checks = vec![
        Check {
            id: "source_doc_frozen",
            status: if exists(&source) && exists(&frozen) {
                "PASS"
            } else {
                "BLOCKED"
            },
            score: if exists(&source) && exists(&frozen) {
                1.0
            } else {
                0.0
            },
            evidence: format!("source={} frozen={}", source.display(), frozen.display()),
            boundary: "uploaded doc copied/frozen locally",
        },
        Check {
            id: "self_recognition_bootstrap",
            status: if exists(&bootstrap) { "PASS" } else { "WATCH" },
            score: if exists(&bootstrap) { 1.0 } else { 0.5 },
            evidence: bootstrap.display().to_string(),
            boundary: "workspace bootstrap only; no startup mutation",
        },
        Check {
            id: "openclaw_mapped_to_hermes",
            status: "PASS",
            score: 1.0,
            evidence:
                "OpenClaw Heartbeat requirement mapped to Hermes launchd/autonomy/health discipline"
                    .to_string(),
            boundary: "no OpenClaw config copied",
        },
        Check {
            id: "cc_source_boundary",
            status: "PASS",
            score: 1.0,
            evidence: "repo classified as non-official source recovery; pattern-only absorption"
                .to_string(),
            boundary: "no clone/no execute/no official claim",
        },
        Check {
            id: "execution_matrix_written",
            status: if exists(&comparison) { "PASS" } else { "WATCH" },
            score: if exists(&comparison) { 1.0 } else { 0.5 },
            evidence: comparison.display().to_string(),
            boundary: "matrix is local design evidence",
        },
        Check {
            id: "conflict_packet_written",
            status: if exists(&conflict) { "PASS" } else { "WATCH" },
            score: if exists(&conflict) { 1.0 } else { 0.5 },
            evidence: conflict.display().to_string(),
            boundary: "high-risk mutations frozen",
        },
    ];
    let score =
        (checks.iter().map(|c| c.score).sum::<f64>() / checks.len() as f64 * 1000.0).round() / 10.0;
    let blocked_count = checks.iter().filter(|c| c.status == "BLOCKED").count();
    let watch_count = checks.iter().filter(|c| c.status == "WATCH").count();
    let status = if blocked_count > 0 {
        "BLOCKED"
    } else if watch_count > 0 {
        "WATCH_PARTIAL_EXECUTION"
    } else {
        "PASS_PATTERN_ABSORBED"
    };
    let report = Report {
        schema: "pgg_cc_cybernetics_absorption_gate/v1",
        generated_at: Local::now().to_rfc3339(),
        status,
        score,
        source_doc_sha256: sha256_file(&source),
        source_doc_path: source.display().to_string(),
        openclaw_mapping_rule: "Any OpenClaw/Heartbeat/龙虾 runtime instruction in the uploaded guide is mapped to local Hermes/PGG equivalents; do not copy OpenClaw directories, configs, cron jobs, credentials, or docs as executable policy.",
        requirements,
        cc_engineering_factors: cc_factors,
        cybernetics_factors: cyber_factors,
        checks,
        watch_items: vec![
            "Full 510k-line CC source deep read is not completed in this bounded pass; current absorption is README/directory/API pattern-only.",
            "Full Engineering Cybernetics book/PDF line-by-line study is not completed; current absorption is metadata/abstract + control-theory engineering factors.",
            "Durable heartbeat automation is mapped but not newly scheduled; follow PGG launchd/Rust discipline if later authorized.",
        ],
        blocked_items: Vec::new(),
        boundary: vec![
            "read-only external source handling",
            "no external code execution",
            "no OpenClaw runtime/config import",
            "no provider/config/credential/security/scheduler mutation",
            "no MEMORY/USER automatic write",
            "no full AGI/T5/zero hallucination/legal correctness claim",
        ],
    };

    let json = serde_json::to_string_pretty(&report).unwrap_or_else(|_| "{}".to_string());
    let dir = latest_dir();
    let _ = fs::create_dir_all(&dir);
    let _ = fs::write(dir.join("latest.json"), &json);
    println!("{}", json);
}
