use chrono::{Local, SecondsFormat};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{
    collections::{BTreeMap, BTreeSet},
    env, fs,
    path::{Path, PathBuf},
    process::Command,
};

const REQUIRED_ROLES: [&str; 6] = [
    "cms",
    "matter_department",
    "evidence_management",
    "legal_support",
    "inspection_audit",
    "secondary_llm_or_subagent",
];

const VALID_TYPES: [&str; 7] = [
    "subagent",
    "provider_llm",
    "external_llm",
    "department_agent",
    "human_lawyer",
    "tool_receipt",
    "cms_gate_run",
];

const NON_TYPES: [&str; 6] = [
    "central_agent_draft",
    "skill_loaded",
    "template",
    "status_field_only",
    "gate_exists_only",
    "department_named_file_only",
];

#[derive(Deserialize)]
struct OpsReport {
    cases: Vec<CaseScan>,
}
#[derive(Deserialize)]
struct CaseScan {
    name: String,
    path: String,
    trusted_status: String,
}
#[derive(Serialize, Clone)]
struct WorkItem {
    item_id: String,
    case_id: String,
    case_path: String,
    required_role: String,
    assigned_profile: String,
    status: String,
    priority: String,
    action: String,
    receipt_rule: String,
}
#[derive(Serialize)]
struct QueueReport {
    schema: String,
    generated_at: String,
    status: String,
    source_report: String,
    item_count: usize,
    items: Vec<WorkItem>,
    profile_status_ok: bool,
    existing_receipt_role_counts: BTreeMap<String, usize>,
    case_existing_roles: BTreeMap<String, Vec<String>>,
    boundary: Vec<String>,
}
fn home() -> PathBuf {
    PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}
fn run(cmd: &str, args: &[&str]) -> (bool, String) {
    match Command::new(cmd).args(args).output() {
        Ok(o) => {
            let mut s = String::new();
            s.push_str(&String::from_utf8_lossy(&o.stdout));
            s.push_str(&String::from_utf8_lossy(&o.stderr));
            (o.status.success(), s.trim().chars().take(2000).collect())
        }
        Err(e) => (false, format!("exec error: {e}")),
    }
}
fn profile_for(role: &str) -> &'static str {
    match role {
        "cms" => "default",
        "matter_department" => "pgg-business-master",
        "evidence_management" => "pgg-fact-evidence",
        "legal_support" => "pgg-law-source",
        "inspection_audit" => "pgg-inspection-audit",
        "secondary_llm_or_subagent" => "delegate_task_or_pgg-strategy-simulation",
        _ => "default",
    }
}
fn role_action(role: &str) -> &'static str {
    match role {
        "cms" => "archive cms_case_guard output and case ledger receipt",
        "matter_department" => "write matter/case-type routing receipt and business handling note",
        "evidence_management" => "write evidence inventory/fact-evidence map/OCR quality receipt",
        "legal_support" => "write local-first legal basis/query receipt",
        "inspection_audit" => "write independent inspection/audit challenge receipt",
        "secondary_llm_or_subagent" => {
            "obtain independent subagent/provider review receipt or failure reason"
        }
        _ => "write role receipt",
    }
}
fn read_string(v: &Value, keys: &[&str]) -> Option<String> {
    for k in keys {
        if let Some(s) = v.get(*k).and_then(|x| x.as_str()) {
            if !s.trim().is_empty() {
                return Some(s.trim().to_string());
            }
        }
    }
    None
}
fn normalize_receipts(data: &Value) -> Vec<Value> {
    if let Some(arr) = data.get("receipts").and_then(|x| x.as_array()) {
        return arr.clone();
    }
    if let Some(arr) = data.get("participants").and_then(|x| x.as_array()) {
        return arr.clone();
    }
    if let Some(obj) = data.get("roles").and_then(|x| x.as_object()) {
        let mut out = Vec::new();
        for (role, val) in obj {
            if val.is_object() {
                let mut cloned = val.clone();
                if let Some(m) = cloned.as_object_mut() {
                    m.entry("role".to_string())
                        .or_insert(Value::String(role.clone()));
                }
                out.push(cloned);
            }
        }
        return out;
    }
    if let Some(arr) = data.as_array() {
        return arr.clone();
    }
    Vec::new()
}
fn walk_json_files(root: &Path, out: &mut Vec<PathBuf>) {
    if let Ok(rd) = fs::read_dir(root) {
        for ent in rd.flatten() {
            let p = ent.path();
            if p.is_dir() {
                walk_json_files(&p, out);
            } else if let Some(name) = p.file_name().and_then(|s| s.to_str()) {
                if name.contains("trusted_workflow_participation")
                    || name.contains("multi_department")
                    || name.contains("参与真实性")
                    || name.contains("多部门")
                {
                    if name.ends_with(".json") {
                        out.push(p);
                    }
                }
            }
        }
    }
}
fn role_receipt_ok(rec: &Value, case_root: &Path) -> Option<String> {
    let role = read_string(rec, &["role", "department", "name"])?;
    if !REQUIRED_ROLES.contains(&role.as_str()) {
        return None;
    }
    let ptype = read_string(rec, &["participant_type", "type", "evidence_type"])?;
    if NON_TYPES.contains(&ptype.as_str()) || !VALID_TYPES.contains(&ptype.as_str()) {
        return None;
    }
    if role == "secondary_llm_or_subagent"
        && read_string(rec, &["provider", "model", "agent"]).is_none()
    {
        return None;
    }
    let raw = read_string(rec, &["raw_output_path", "receipt_path", "evidence_path"])?;
    let mut p = PathBuf::from(&raw);
    if !p.is_absolute() {
        p = case_root.join(p);
    }
    if p.exists() && p.is_file() && p.metadata().map(|m| m.len() > 0).unwrap_or(false) {
        Some(role)
    } else {
        None
    }
}
fn existing_roles(case_root: &Path) -> BTreeSet<String> {
    let mut files = Vec::new();
    walk_json_files(case_root, &mut files);
    let mut roles = BTreeSet::new();
    files.sort();
    files.dedup();
    for f in files {
        let Ok(raw) = fs::read_to_string(&f) else {
            continue;
        };
        let Ok(data) = serde_json::from_str::<Value>(&raw) else {
            continue;
        };
        for rec in normalize_receipts(&data) {
            if let Some(role) = role_receipt_ok(&rec, case_root) {
                roles.insert(role);
            }
        }
    }
    roles
}
fn write_md(q: &QueueReport, p: &Path) -> std::io::Result<()> {
    let mut s = String::new();
    s.push_str("# PGG Legal Receipt Work Queue\n\n");
    s.push_str(&format!(
        "- Generated: `{}`\n- Status: `{}`\n- Items: `{}`\n- Source: `{}`\n\n",
        q.generated_at, q.status, q.item_count, q.source_report
    ));
    s.push_str("## Existing accepted roles per case\n\n");
    for (case_id, roles) in &q.case_existing_roles {
        s.push_str(&format!("- `{}`: `{}`\n", case_id, roles.join(", ")));
    }
    s.push_str("\n## Pending Items\n\n");
    for it in &q.items {
        s.push_str(&format!(
            "- `{}` | `{}` | `{}` | `{}` | {}\n",
            it.item_id, it.case_id, it.required_role, it.assigned_profile, it.action
        ));
    }
    s.push_str("\n## Boundary\n\n");
    for b in &q.boundary {
        s.push_str(&format!("- {}\n", b));
    }
    fs::write(p, s)
}
fn main() {
    let h = home();
    let source = h.join(".hermes/workspace/pgg-archon-governance/legal-multiagent-ops/latest.json");
    let out_dir =
        h.join(".hermes/workspace/pgg-archon-governance/legal-multiagent-ops/receipt-queue");
    fs::create_dir_all(&out_dir).unwrap();
    let raw = fs::read_to_string(&source)
        .expect("missing D1 latest.json; run pgg-legal-ops-observer first");
    let report: OpsReport = serde_json::from_str(&raw).expect("invalid D1 latest.json");
    let mut items = Vec::new();
    let mut role_counts: BTreeMap<String, usize> = BTreeMap::new();
    let mut case_existing: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for c in report.cases {
        let case_id = c.name.clone();
        let roles_found = existing_roles(Path::new(&c.path));
        for r in &roles_found {
            *role_counts.entry(r.clone()).or_insert(0) += 1;
        }
        case_existing.insert(case_id.clone(), roles_found.iter().cloned().collect());
        if c.trusted_status == "PASS" && roles_found.len() == REQUIRED_ROLES.len() {
            continue;
        }
        for role in REQUIRED_ROLES {
            if roles_found.contains(role) {
                continue;
            }
            items.push(WorkItem{
                item_id: format!("{}::{}", case_id, role),
                case_id: case_id.clone(),
                case_path: c.path.clone(),
                required_role: role.to_string(),
                assigned_profile: profile_for(role).to_string(),
                status: "pending_receipt".into(),
                priority: if role=="cms" || role=="evidence_management" {"P1"} else {"P2"}.into(),
                action: role_action(role).into(),
                receipt_rule: "must create non-empty receipt/raw_output path accepted by case_trusted_workflow_gate; running profile alone does not count".into(),
            });
        }
    }
    let (prof_ok, _) = run(
        h.join(".hermes/bin/pgg-case-departments")
            .to_str()
            .unwrap_or("pgg-case-departments"),
        &["status", "--json"],
    );
    let generated = Local::now().to_rfc3339_opts(SecondsFormat::Secs, true);
    let status = if items.is_empty() {
        "PASS_NO_PENDING_RECEIPTS"
    } else {
        "WATCH_PENDING_RECEIPTS"
    }
    .to_string();
    let q=QueueReport{schema:"pgg-legal-receipt-queue/v2".into(), generated_at:generated, status, source_report:source.display().to_string(), item_count:items.len(), items, profile_status_ok:prof_ok, existing_receipt_role_counts: role_counts, case_existing_roles: case_existing, boundary:vec![
        "queue only; does not start LLM work by itself".into(),
        "assigned_profile is routing hint, not proof of role participation".into(),
        "existing trusted_workflow_participation receipts are recursively parsed per role to avoid duplicate retrospective receipts".into(),
        "receipts must be archived and accepted by case_trusted_workflow_gate".into(),
        "on-demand profile start/touch/reap uses pgg-case-departments".into(),
    ]};
    let date = Local::now().format("%Y%m%d-%H%M%S").to_string();
    let json_path = out_dir.join(format!("receipt-queue-{date}.json"));
    let md_path = out_dir.join(format!("receipt-queue-{date}.md"));
    fs::write(&json_path, serde_json::to_string_pretty(&q).unwrap()).unwrap();
    write_md(&q, &md_path).unwrap();
    fs::write(
        out_dir.join("latest.json"),
        serde_json::to_string_pretty(&q).unwrap(),
    )
    .unwrap();
    fs::write(
        out_dir.join("latest.md"),
        fs::read_to_string(&md_path).unwrap(),
    )
    .unwrap();
    println!(
        "{}",
        serde_json::json!({"ok":true,"schema":q.schema,"status":q.status,"item_count":q.item_count,"existing_receipt_role_counts":q.existing_receipt_role_counts,"json":json_path,"md":md_path})
    );
}
