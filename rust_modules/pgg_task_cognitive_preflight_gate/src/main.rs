use chrono::Utc;
use serde::Serialize;
use std::collections::{BTreeSet, HashMap};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Serialize, Clone)]
struct Check {
    name: String,
    ok: bool,
    severity: String,
    evidence: serde_json::Value,
    action: String,
}

#[derive(Debug, Serialize, Clone)]
struct Hazard {
    id: String,
    matched: Vec<String>,
    required_skills: Vec<String>,
    required_live_evidence: Vec<String>,
    required_gates: Vec<String>,
    principle: String,
}

#[derive(Debug, Serialize)]
struct Report {
    schema: String,
    status: String,
    timestamp: String,
    task: String,
    mode: String,
    loaded_skills: Vec<String>,
    matched_hazards: Vec<Hazard>,
    required_retrieval_queries: Vec<String>,
    required_next_actions: Vec<String>,
    checks: Vec<Check>,
    passed: usize,
    total: usize,
    boundary: String,
}

fn home() -> PathBuf {
    PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}

fn contains_any(task: &str, words: &[&str]) -> Vec<String> {
    let t = task.to_lowercase();
    let ascii_tokens: BTreeSet<String> = t
        .split(|c: char| !c.is_ascii_alphanumeric() && c != '-' && c != '_')
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
        .collect();
    words
        .iter()
        .filter(|w| {
            let wl = w.to_lowercase();
            if wl.is_ascii() && wl.len() <= 3 {
                ascii_tokens.contains(&wl)
            } else {
                t.contains(&wl)
            }
        })
        .map(|s| s.to_string())
        .collect()
}

fn file_nonempty(path: &Path) -> bool {
    fs::metadata(path)
        .map(|m| m.is_file() && m.len() > 0)
        .unwrap_or(false)
}
fn cmd_exists(path: &Path) -> bool {
    fs::metadata(path).map(|m| m.is_file()).unwrap_or(false)
}

fn skill_exists(name: &str) -> bool {
    let root = home().join(".hermes/skills");
    let mut stack = vec![root];
    while let Some(dir) = stack.pop() {
        if let Ok(rd) = fs::read_dir(&dir) {
            for e in rd.flatten() {
                let p = e.path();
                if p.is_dir() {
                    if p.file_name().and_then(|s| s.to_str()) == Some(name)
                        && p.join("SKILL.md").exists()
                    {
                        return true;
                    }
                    stack.push(p);
                }
            }
        }
    }
    false
}

fn parse_args() -> (String, Vec<String>, String) {
    let args: Vec<String> = env::args().collect();
    let mut task = String::new();
    let mut loaded = Vec::new();
    let mut mode = "advisory".to_string();
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--task" => {
                if i + 1 < args.len() {
                    task = args[i + 1].clone();
                    i += 1;
                }
            }
            "--loaded-skills" => {
                if i + 1 < args.len() {
                    loaded = args[i + 1]
                        .split(',')
                        .map(|s| s.trim().to_string())
                        .filter(|s| !s.is_empty())
                        .collect();
                    i += 1;
                }
            }
            "--mode" => {
                if i + 1 < args.len() {
                    mode = args[i + 1].clone();
                    i += 1;
                }
            }
            "--help" | "-h" => {
                println!("Usage: pgg-task-cognitive-preflight-gate --task <text> [--loaded-skills a,b] [--mode advisory|blocking]");
                std::process::exit(0);
            }
            other => {
                if task.is_empty() {
                    task = other.to_string();
                }
            }
        }
        i += 1;
    }
    (task, loaded, mode)
}

fn main() {
    let (task, loaded_skills, mode) = parse_args();
    let mut checks: Vec<Check> = Vec::new();
    let mut hazards: Vec<Hazard> = Vec::new();
    let mut required_queries: BTreeSet<String> = BTreeSet::new();
    let mut next_actions: BTreeSet<String> = BTreeSet::new();
    let mut add_check =
        |name: &str, ok: bool, severity: &str, evidence: serde_json::Value, action: &str| {
            checks.push(Check {
                name: name.to_string(),
                ok,
                severity: severity.to_string(),
                evidence,
                action: action.to_string(),
            });
        };

    add_check(
        "task_description_present",
        !task.trim().is_empty(),
        "critical",
        serde_json::json!({"chars": task.len()}),
        "必须先有明确任务描述；否则不能做任务前认知预检",
    );
    let mem_dir = home().join(".hermes/memories");
    add_check(
        "curated_memory_files_present",
        file_nonempty(&mem_dir.join("MEMORY.md")) && file_nonempty(&mem_dir.join("USER.md")),
        "critical",
        serde_json::json!({"memory": mem_dir.join("MEMORY.md"), "user": mem_dir.join("USER.md")}),
        "任务前至少确认 curated MEMORY/USER 可读；它们是索引，不是唯一事实源",
    );
    add_check(
        "session_search_available",
        true,
        "high",
        serde_json::json!({"tool":"session_search","note":"Hermes runtime tool; use for past-session recall when task has historical context"}),
        "涉及历史状态/曾经修过/用户纠错时必须检索 session_search，而不是只凭 MEMORY",
    );
    add_check(
        "skill_system_present",
        home().join(".hermes/skills").is_dir(),
        "critical",
        serde_json::json!({"skills_root": home().join(".hermes/skills")}),
        "必须加载匹配 skill；skill 是 procedural memory 主存储",
    );
    add_check(
        "memory_system_command_present",
        cmd_exists(&home().join(".hermes/bin/记忆系统")),
        "medium",
        serde_json::json!({"cmd": home().join(".hermes/bin/记忆系统")}),
        "用户提到记忆系统/神经元时，运行 `记忆系统 --json` 做 live readback",
    );

    let mut hazard_defs: HashMap<&str, (&[&str], Vec<&str>, Vec<&str>, Vec<&str>, &str)> =
        HashMap::new();
    hazard_defs.insert("memory_neuron_context", (&["记忆", "神经元", "忘", "串联", "remember", "memory"], vec!["memory-retrieval-architecture", "hermes-evolution"], vec!["记忆系统 --json", "session_search(query=任务关键词)", "相关 skill_view 读回"], vec!["pgg-task-cognitive-preflight-gate"], "Memory is an index, not proof. Build a task-time cognition bundle from MEMORY+skills+sessions+live gates."));
    hazard_defs.insert("ui_status_ledger", (&["ui", "dashboard", "状态", "ledger", "provider", "llm", "通道", "omniroute", "量子路由"], vec!["pgg-live-state-sync-readback", "hermes-evolution"], vec!["live gate/snapshot", "latest jsonl tail", "browser/API readback"], vec!["pgg-omniroute-ui-stale-provider-gate"], "Never aggregate current state from historical ledgers without filtering by live active set."));
    hazard_defs.insert("legal_casework", (&["案件", "诉讼", "法律", "律所", "oa", "lawlink", "cms"], vec!["legal-casework-router", "agent-cms", "dept-evidence-management", "dept-legal-support", "dept-inspection-team"], vec!["cms_case_guard --next", "材料路径读回", "六角色 receipt"], vec!["cms_case_guard", "LawLink sync/readback when case closes"], "Formal casework needs CMS/evidence/legal/audit/secondary receipts; draft until verified."));
    hazard_defs.insert(
        "github_external_side_effect",
        (
            &["github", "pr", "push", "merge", "commit", "远程", "仓库"],
            vec![
                "github-delivery-router",
                "github-pr-workflow",
                "github-auth",
            ],
            vec![
                "git status",
                "gh auth status",
                "remote/branch readback",
                "CI/checks readback",
            ],
            vec!["secret scan", "scoped commit gate"],
            "External side effects require auth/scope/readback; local tests are not completion.",
        ),
    );
    hazard_defs.insert("hermes_config_runtime", (&["hermes", "config", "provider", "scheduler", "launchd", "mcp", "插件", "工具"], vec!["hermes-agent", "hermes-config-runtime-diagnosis", "pgg-archon-runtime"], vec!["config targeted readback", "launchctl/port/process readback", "provider probe"], vec!["hermes-goal", "pgg-health-monitor --json"], "Hermes runtime changes require docs/skill first, targeted edits, no YAML round-trip, and live verification."));
    hazard_defs.insert(
        "code_change",
        (
            &[
                "修复", "代码", "实现", "build", "测试", "rust", "python", "模块",
            ],
            vec![
                "software-development",
                "systematic-debugging",
                "requesting-code-review",
            ],
            vec![
                "tests/build output",
                "readback changed files",
                "rollback path",
            ],
            vec!["cargo test/pytest/focused smoke"],
            "Do not stop at patching; build/test/readback and settle the lesson if non-trivial.",
        ),
    );

    let loaded_set: BTreeSet<String> = loaded_skills.iter().cloned().collect();
    for (id, (keywords, req_skills, evidence, gates, principle)) in hazard_defs.iter() {
        let matched = contains_any(&task, keywords);
        if !matched.is_empty() {
            let h = Hazard {
                id: id.to_string(),
                matched: matched.clone(),
                required_skills: req_skills.iter().map(|s| s.to_string()).collect(),
                required_live_evidence: evidence.iter().map(|s| s.to_string()).collect(),
                required_gates: gates.iter().map(|s| s.to_string()).collect(),
                principle: principle.to_string(),
            };
            for s in req_skills {
                let exists = skill_exists(s);
                let loaded = loaded_set.contains(&s.to_string());
                add_check(
                    &format!("required_skill_available__{}", s),
                    exists,
                    "high",
                    serde_json::json!({"skill":s,"exists":exists,"loaded_in_args":loaded}),
                    "相关 skill 必须 skill_view 加载；存在但未加载时视为 WATCH",
                );
                if !loaded {
                    next_actions.insert(format!("skill_view(name='{}')", s));
                }
            }
            for e in evidence {
                next_actions.insert(format!("readback: {}", e));
            }
            for g in gates {
                next_actions.insert(format!("run gate if applicable: {}", g));
            }
            required_queries.insert(format!(
                "session_search query for hazard {} with task keywords",
                id
            ));
            hazards.push(h);
        }
    }

    let has_hazard = !hazards.is_empty();
    add_check(
        "hazard_patterns_matched",
        has_hazard,
        "medium",
        serde_json::json!({"count": hazards.len(), "hazards": hazards.iter().map(|h| h.id.clone()).collect::<Vec<_>>()}),
        "若无 hazard，仍需按普通事实/证据门禁执行；若有 hazard，必须执行对应 readback/gate",
    );
    let missing_loaded_required: Vec<String> = hazards
        .iter()
        .flat_map(|h| h.required_skills.iter().cloned())
        .filter(|s| !loaded_set.contains(s))
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    add_check(
        "required_skills_loaded_for_this_task",
        missing_loaded_required.is_empty(),
        "high",
        serde_json::json!({"missing_loaded": missing_loaded_required}),
        "开始执行前加载所有相关 skill，避免只记得一部分规则",
    );

    if hazards.iter().any(|h| h.id == "memory_neuron_context") {
        next_actions.insert("build cognition bundle: MEMORY/USER index + relevant skill excerpts + session_search hits + live gates + task-specific hazards".to_string());
        next_actions.insert("do not write raw neurons directly to MEMORY/USER; route to candidate/review/skill/reference/gate".to_string());
    }

    let passed = checks.iter().filter(|c| c.ok).count();
    let total = checks.len();
    let critical_fail = checks.iter().any(|c| !c.ok && c.severity == "critical");
    let high_fail = checks.iter().any(|c| !c.ok && c.severity == "high");
    let status = if critical_fail || (mode == "blocking" && high_fail) {
        "FAIL_TASK_COGNITIVE_PREFLIGHT"
    } else if high_fail || checks.iter().any(|c| !c.ok) {
        "WATCH_TASK_COGNITIVE_PREFLIGHT"
    } else {
        "PASS_TASK_COGNITIVE_PREFLIGHT"
    };

    let report = Report { schema: "PGGTaskCognitivePreflightGate/v1".to_string(), status: status.to_string(), timestamp: Utc::now().to_rfc3339(), task, mode, loaded_skills, matched_hazards: hazards, required_retrieval_queries: required_queries.into_iter().collect(), required_next_actions: next_actions.into_iter().collect(), checks, passed, total, boundary: "read-only/advisory gate; no provider/config/scheduler/security mutation; prevents memory fragmentation by forcing task-time retrieval, skill loading, live readback, and executable gates".to_string() };
    println!("{}", serde_json::to_string_pretty(&report).unwrap());
    if report.status.starts_with("FAIL") {
        std::process::exit(1);
    }
}
