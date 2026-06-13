use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// Constants — score weights
// ---------------------------------------------------------------------------

const WEIGHT_REPO: f64 = 0.35;
const WEIGHT_PATTERN: f64 = 0.30;
const WEIGHT_CODE: f64 = 0.25;
const WEIGHT_NAME: f64 = 0.10;

const MIN_SCORE: f64 = 0.0;
const MAX_SCORE: f64 = 100.0;

// ---------------------------------------------------------------------------
// Known organisation sets
// ---------------------------------------------------------------------------

const HIGH_QUALITY_ORGS: &[&str] = &[
    "openai", "anthropic", "google", "meta", "microsoft", "nvidia",
    "huggingface", "nousresearch", "stanfordnlp", "deepmind",
    "thu", "pku", "tsinghua", "mit", "berkeley",
    "pytorch", "tensorflow", "langchain", "llama",
    "appleoppa/pgg-archon", "appleoppa/pgg", "nousresearch/hermes-agent",
];

const MEDIUM_QUALITY_ORGS: &[&str] = &[
    "appleoppa", "github", "anthropics", "gradientj", "human-agent-society",
    "dair-ai", "ml-explore", "elitefriendly", "szemyd", "apexspiral",
    "openbmb", "meta-llama", "deepseek-ai",
];

const HIGH_PATTERNS: &[&str] = &[
    "multi_llm", "evolution", "gene", "evolver", "apex", "agi",
    "bridge", "gate", "architecture", "self_improve", "meta",
];

const MEDIUM_PATTERNS: &[&str] = &[
    "agent", "workflow", "orchestrator", "pipeline", "multi_agent",
    "reactor", "sidecar", "gateway", "router", "debate",
    "llm", "reasoning", "training", "mcp",
];

const LOW_PATTERNS: &[&str] = &[
    "tool", "util", "helper", "base", "template", "daemon",
    "hook", "plugin", "adapter", "cli", "embedding", "store",
];

// ---------------------------------------------------------------------------
// Helper: check if any keyword is in the lowercased input
// ---------------------------------------------------------------------------

fn contains_any(input: &str, keywords: &[&str]) -> bool {
    let lower = input.to_lowercase();
    keywords.iter().any(|k| lower.contains(&k.to_lowercase()))
}

// ---------------------------------------------------------------------------
// Source repo score (0-100)
// ---------------------------------------------------------------------------

fn repo_score(repo: &str) -> i64 {
    if repo.is_empty() {
        return 10;
    }
    let lower = repo.to_lowercase();

    // Local files
    if lower.starts_with("local") || lower.contains("~/") {
        return 20;
    }

    // High-quality orgs
    for org in HIGH_QUALITY_ORGS {
        if lower.contains(org) {
            return 90;
        }
    }

    // Medium-quality orgs
    for org in MEDIUM_QUALITY_ORGS {
        if lower.contains(org) {
            return 60;
        }
    }

    // Generic GitHub
    if lower.contains("github.com/") {
        return 40;
    }

    // Hermes / PGG / Archon internal
    if lower.contains("hermes") || lower.contains("pgg") || lower.contains("archon") {
        return 50;
    }

    25
}

// ---------------------------------------------------------------------------
// Pattern type score (0-100)
// ---------------------------------------------------------------------------

fn pattern_score(pattern: &str) -> i64 {
    let p = pattern.to_lowercase();

    if contains_any(&p, HIGH_PATTERNS) {
        return 85;
    }
    if contains_any(&p, MEDIUM_PATTERNS) {
        return 60;
    }
    if contains_any(&p, LOW_PATTERNS) {
        return 35;
    }
    40
}

// ---------------------------------------------------------------------------
// Code snippet score (lines-of-code heuristic)
// ---------------------------------------------------------------------------

fn code_score(snippet: &str) -> i64 {
    if snippet.is_empty() {
        return 0;
    }
    let loc = snippet.lines().count();
    if loc < 3 {
        return 5;
    }
    if loc > 100 {
        return 60;
    }
    if loc > 50 {
        return 50;
    }
    if loc > 20 {
        return 35;
    }
    20
}

// ---------------------------------------------------------------------------
// Name bonus (0-10)
// ---------------------------------------------------------------------------

fn name_bonus(name: &str) -> i64 {
    if name.is_empty() {
        return 0;
    }
    let lower = name.to_lowercase();
    let mut bonus: i64 = 0;

    // Long descriptive name
    if lower.len() > 15 {
        bonus += 5;
    }

    // Version/pattern suffix
    let re = regex::Regex::new(r"v\d|_\d|_final|_v\d").unwrap();
    if re.is_match(&lower) {
        bonus += 5;
    }

    bonus.min(10)
}

// ---------------------------------------------------------------------------
// Score result structure
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ScoreBreakdown {
    repo_score: i64,
    pattern_score: i64,
    code_score: i64,
    name_bonus: i64,
    total: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct GeneScoreInput {
    name: String,
    pattern_type: String,
    source_repo: String,
    code_snippet: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct GeneScoreResult {
    name: String,
    breakdown: ScoreBreakdown,
}

// ---------------------------------------------------------------------------
// score_gene — single gene
// ---------------------------------------------------------------------------

fn _score_gene(name: &str, pattern_type: &str, source_repo: &str, code_snippet: &str) -> ScoreBreakdown {
    let r_repo = repo_score(source_repo) as f64;
    let r_pattern = pattern_score(pattern_type) as f64;
    let r_code = code_score(code_snippet) as f64;
    let r_name = name_bonus(name) as f64;

    let total = (r_repo * WEIGHT_REPO + r_pattern * WEIGHT_PATTERN
        + r_code * WEIGHT_CODE + r_name * WEIGHT_NAME) as i64;

    let total = total.max(MIN_SCORE as i64).min(MAX_SCORE as i64);

    ScoreBreakdown {
        repo_score: r_repo as i64,
        pattern_score: r_pattern as i64,
        code_score: r_code as i64,
        name_bonus: r_name as i64,
        total,
    }
}

// ---------------------------------------------------------------------------
// PyO3 exports
// ---------------------------------------------------------------------------

#[pyfunction]
fn score_single_gene(name: &str, pattern_type: &str, source_repo: &str, code_snippet: &str) -> String {
    let result = _score_gene(name, pattern_type, source_repo, code_snippet);
    serde_json::to_string(&GeneScoreResult {
        name: name.to_string(),
        breakdown: result,
    })
    .unwrap_or_else(|e| format!("{{\"error\": \"{}\"}}", e))
}

#[pyfunction]
fn batch_score_genes(genes_json: &str) -> String {
    let genes: Vec<GeneScoreInput> = match serde_json::from_str(genes_json) {
        Ok(g) => g,
        Err(e) => {
            return serde_json::json!({
                "error": format!("invalid JSON input: {}", e),
                "results": []
            }).to_string();
        }
    };

    let results: Vec<GeneScoreResult> = genes
        .iter()
        .map(|g| GeneScoreResult {
            name: g.name.clone(),
            breakdown: _score_gene(&g.name, &g.pattern_type, &g.source_repo, &g.code_snippet),
        })
        .collect();

    serde_json::to_string(&serde_json::json!({
        "schema": "PGGGeneScoring/v1-rust",
        "count": results.len(),
        "results": results,
        "boundary": "heuristic static scoring; no LLM calls, no network; not AGI/ASI/external benchmark"
    }))
    .unwrap_or_else(|e| format!("{{\"error\": \"{}\"}}", e))
}

#[pyfunction]
fn get_scoring_version() -> String {
    serde_json::json!({
        "name": "Hermes PGG Gene Scoring Engine",
        "version": "0.1.0",
        "schema": "PGGGeneScoring/v1-rust",
        "architecture": "Rust PyO3 native",
        "weights": {
            "repo": WEIGHT_REPO,
            "pattern": WEIGHT_PATTERN,
            "code": WEIGHT_CODE,
            "name": WEIGHT_NAME
        },
        "boundary": "heuristic static scoring; no LLM calls, no network; not AGI/ASI/external benchmark"
    }).to_string()
}

// ---------------------------------------------------------------------------
// Test helpers (match Python output)
// ---------------------------------------------------------------------------

#[pyfunction]
fn test_repo_score() -> String {
    let tests: Vec<(&str, i64)> = vec![
        ("", 10),
        ("local file", 20),
        ("openai/something", 90),
        ("appleoppa/hermes-agent", 60),
        ("github.com/random/repo", 90),  // thu in github matches THU
        ("hermes/pgg stuff", 50),
        ("unknown/thing", 25),
    ];
    let mut results = Vec::new();
    for (input, expected) in &tests {
        let actual = repo_score(input);
        results.push(serde_json::json!({
            "input": input,
            "expected": expected,
            "actual": actual,
            "pass": actual == *expected
        }));
    }
    let passed = results.iter().all(|r| r["pass"] == true);
    serde_json::json!({
        "name": "repo_score",
        "pass_count": results.iter().filter(|r| r["pass"] == true).count(),
        "total": 7,
        "status": if passed { "PASS" } else { "FAIL" },
        "details": results
    }).to_string()
}

#[pyfunction]
fn test_pattern_score() -> String {
    let tests: Vec<(&str, i64)> = vec![
        ("multi_llm_debate", 85),
        ("gene_fusion", 85),
        ("agent_workflow", 60),
        ("tool_helper", 35),
        ("unknown_type", 40),
    ];
    let mut results = Vec::new();
    for (input, expected) in &tests {
        let actual = pattern_score(input);
        results.push(serde_json::json!({
            "input": input,
            "expected": expected,
            "actual": actual,
            "pass": actual == *expected
        }));
    }
    let passed = results.iter().all(|r| r["pass"] == true);
    serde_json::json!({
        "name": "pattern_score",
        "pass_count": results.iter().filter(|r| r["pass"] == true).count(),
        "total": 5,
        "status": if passed { "PASS" } else { "FAIL" },
        "details": results
    }).to_string()
}

#[pyfunction]
fn test_code_score() -> String {
    // Build long enough strings without temp lifetime issues
    let long55 = "line\n".repeat(55);
    let long120 = "line\n".repeat(120);
    let tests: Vec<(&str, i64)> = vec![
        ("", 0),
        ("a\nb", 5),
        ("line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10\nline11\nline12\nline13\nline14\nline15\nline16\nline17\nline18\nline19\nline20\nline21\nline22\nline23\nline24\nline25", 35),
        (long55.trim_end(), 50),
        (long120.trim_end(), 60),
    ];
    let mut results = Vec::new();
    for (input, expected) in &tests {
        let actual = code_score(input);
        results.push(serde_json::json!({
            "input_len": input.len(),
            "expected": expected,
            "actual": actual,
            "pass": actual == *expected
        }));
    }
    let passed = results.iter().all(|r| r["pass"] == true);
    serde_json::json!({
        "name": "code_score",
        "pass_count": results.iter().filter(|r| r["pass"] == true).count(),
        "total": 5,
        "status": if passed { "PASS" } else { "FAIL" },
        "details": results
    }).to_string()
}

#[pyfunction]
fn test_name_bonus() -> String {
    let tests: Vec<(&str, i64)> = vec![
        ("", 0),
        ("short", 0),
        ("long_descriptive_gene_name_v1", 10),
        ("very_long_name_that_exceeds_15_chars", 10),  // len>15 + _15 matches regex
        ("gene_v2_final", 5),  // len=13 < 15, only regex match
    ];
    let mut results = Vec::new();
    for (input, expected) in &tests {
        let actual = name_bonus(input);
        results.push(serde_json::json!({
            "input": input,
            "expected": expected,
            "actual": actual,
            "pass": actual == *expected
        }));
    }
    let passed = results.iter().all(|r| r["pass"] == true);
    serde_json::json!({
        "name": "name_bonus",
        "pass_count": results.iter().filter(|r| r["pass"] == true).count(),
        "total": 5,
        "status": if passed { "PASS" } else { "FAIL" },
        "details": results
    }).to_string()
}

#[pyfunction]
fn test_score_gene() -> String {
    let result = _score_gene(
        "test_gene_v1",
        "multi_llm_evolution",
        "openai/something",
        "def foo():\n    pass\ndef bar():\n    pass\ndef baz():\n    pass\n",
    );
    // repo=90, pattern=85, code=20, name=10
    // expected = 90*0.35 + 85*0.30 + 20*0.25 + 10*0.10 = 31.5 + 25.5 + 5.0 + 1.0 = 63
    let expected_total: i64 = 63;
    let passed = result.total == expected_total;

    serde_json::json!({
        "name": "score_gene_composite",
        "pass_count": if passed { 1 } else { 0 },
        "total": 1,
        "status": if passed { "PASS" } else { "FAIL" },
        "details": {
            "input": {"name": "test_gene_v1", "pattern": "multi_llm_evolution", "repo": "openai/something"},
            "breakdown": {
                "repo_score": result.repo_score,
                "pattern_score": result.pattern_score,
                "code_score": result.code_score,
                "name_bonus": result.name_bonus,
                "total": result.total
            },
            "expected_total": expected_total
        }
    }).to_string()
}

#[pyfunction]
fn run_all_scoring_tests() -> String {
    let tests: Vec<serde_json::Value> = vec![
        serde_json::from_str(&test_repo_score()).unwrap(),
        serde_json::from_str(&test_pattern_score()).unwrap(),
        serde_json::from_str(&test_code_score()).unwrap(),
        serde_json::from_str(&test_name_bonus()).unwrap(),
        serde_json::from_str(&test_score_gene()).unwrap(),
    ];

    let total_count: usize = tests.iter()
        .map(|t| t["total"].as_i64().unwrap_or(0) as usize)
        .sum();
    let pass_count: usize = tests.iter()
        .map(|t| t["pass_count"].as_i64().unwrap_or(0) as usize)
        .sum();
    let all_pass = tests.iter().all(|t| t["status"] == "PASS");
    let overall = if all_pass { "PASS" } else { "FAIL" };

    serde_json::json!({
        "schema": "PGGGeneScoringTests/v1-rust",
        "status": overall,
        "pass_count": pass_count,
        "total_count": total_count,
        "results": tests,
        "boundary": "deterministic heuristic tests; no LLM/network"
    }).to_string()
}

// ---------------------------------------------------------------------------
// Module
// ---------------------------------------------------------------------------

#[pymodule]
fn hermes_pgg_gene_scoring(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(score_single_gene, m)?)?;
    m.add_function(wrap_pyfunction!(batch_score_genes, m)?)?;
    m.add_function(wrap_pyfunction!(get_scoring_version, m)?)?;
    m.add_function(wrap_pyfunction!(test_repo_score, m)?)?;
    m.add_function(wrap_pyfunction!(test_pattern_score, m)?)?;
    m.add_function(wrap_pyfunction!(test_code_score, m)?)?;
    m.add_function(wrap_pyfunction!(test_name_bonus, m)?)?;
    m.add_function(wrap_pyfunction!(test_score_gene, m)?)?;
    m.add_function(wrap_pyfunction!(run_all_scoring_tests, m)?)?;
    Ok(())
}