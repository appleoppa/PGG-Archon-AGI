use chrono::{Local, SecondsFormat};
use serde::{Deserialize, Serialize};
use std::{collections::BTreeMap, env, fs, path::PathBuf};

#[derive(Deserialize)]
struct Queue { items: Vec<WorkItem> }
#[derive(Deserialize, Clone)]
struct WorkItem {
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
struct PackIndex {
    schema: String,
    generated_at: String,
    source_queue: String,
    status: String,
    package_count: usize,
    template_count: usize,
    packages: Vec<CasePackage>,
    boundary: Vec<String>,
}
#[derive(Serialize)]
struct CasePackage { case_id: String, case_path: String, package_dir: String, roles: Vec<String> }
fn home() -> PathBuf { PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string())) }
fn sanitize(s: &str) -> String { s.chars().map(|c| if c=='/' || c==':' { '_' } else { c }).collect() }
fn instructions(role: &str) -> &'static str {
    match role {
        "cms" => "Record CMS numbering/archive/ledger verification. Include cms_case_guard output and case root path. Do not state legal merits.",
        "matter_department" => "Record matter department routing: case type, parties, stage, objective, responsible department, and unresolved business questions.",
        "evidence_management" => "Record evidence inventory, OCR quality, fact-evidence map, missing originals, and POOR_QUALITY_NEEDS_VERIFICATION items.",
        "legal_support" => "Record local-first law/case retrieval: statutes, guiding cases, search paths, query terms, and legal basis uncertainty.",
        "inspection_audit" => "Record independent challenge: fact gaps, jurisdiction risk, amount/date inconsistencies, document finalization blockers.",
        "secondary_llm_or_subagent" => "Record independent second review or subagent receipt. If not executed, state NOT_EXECUTED and reason.",
        _ => "Record role participation receipt."
    }
}
fn template_md(it: &WorkItem, generated: &str) -> String {
    format!(r#"# Receipt Template — {role}

- Generated: `{generated}`
- Case: `{case}`
- Case path: `{path}`
- Required role: `{role}`
- Assigned profile: `{profile}`
- Queue status: `{status}`
- Priority: `{priority}`

## Boundary

This is a **template package**, not a participation receipt. It must not be counted by `case_trusted_workflow_gate` until a real reviewer/department/subagent fills it with evidence and archives it into the case's accepted receipt location.

This template is for retrospective/current governance only. It does not claim historical real-time participation.

## Required action

{action}

## Role-specific instructions

{instructions}

## Evidence to attach/read back

- Source files reviewed:
- Commands/tools actually run:
- Output paths:
- Key findings:
- Blockers/WATCH:
- Reviewer/subagent identity:
- Timestamp:

## Draft receipt content

Status: `NOT_EXECUTED_TEMPLATE_ONLY`

Summary:

Evidence:

Risks:

Next action:

## Acceptance rule

{rule}
"#,
        role=it.required_role, generated=generated, case=it.case_id, path=it.case_path,
        profile=it.assigned_profile, status=it.status, priority=it.priority,
        action=it.action, instructions=instructions(&it.required_role), rule=it.receipt_rule)
}
fn main() {
    let h=home();
    let source=h.join(".hermes/workspace/pgg-archon-governance/legal-multiagent-ops/receipt-queue/latest.json");
    let out_root=h.join(".hermes/workspace/pgg-archon-governance/legal-multiagent-ops/receipt-packages");
    fs::create_dir_all(&out_root).unwrap();
    let q: Queue=serde_json::from_str(&fs::read_to_string(&source).expect("missing receipt queue latest.json")).unwrap();
    let generated=Local::now().to_rfc3339_opts(SecondsFormat::Secs, true);
    let mut by_case:BTreeMap<String, Vec<WorkItem>>=BTreeMap::new();
    for it in q.items { by_case.entry(it.case_id.clone()).or_default().push(it); }
    let mut packages=Vec::new();
    let mut count=0usize;
    for (case_id, mut items) in by_case {
        items.sort_by(|a,b| a.required_role.cmp(&b.required_role));
        let dir=out_root.join(sanitize(&case_id));
        fs::create_dir_all(&dir).unwrap();
        let mut roles=Vec::new();
        for it in &items {
            roles.push(it.required_role.clone());
            let file=dir.join(format!("{}__TEMPLATE_ONLY.md", it.required_role));
            fs::write(file, template_md(it, &generated)).unwrap();
            count+=1;
        }
        let case_path=items.first().map(|i| i.case_path.clone()).unwrap_or_default();
        let readme=dir.join("README.md");
        fs::write(&readme, format!("# Receipt Template Package\n\nCase: `{}`\n\nTemplates: `{}`\n\nBoundary: template-only, not a trusted workflow receipt.\n", case_id, roles.join(", "))).unwrap();
        packages.push(CasePackage{case_id, case_path, package_dir:dir.display().to_string(), roles});
    }
    let idx=PackIndex{
        schema:"pgg-legal-receipt-template-pack/v1".into(), generated_at:generated, source_queue:source.display().to_string(),
        status: if count==0 {"PASS_NO_TEMPLATES_NEEDED"} else {"PASS_TEMPLATE_PACKAGES_WRITTEN"}.into(),
        package_count:packages.len(), template_count:count, packages,
        boundary:vec![
            "templates are written outside case folders to avoid being counted as participation".into(),
            "no LLM/provider calls; no legal conclusions generated".into(),
            "not historical real-time participation; only retrospective/current governance package".into(),
            "case_trusted_workflow_gate must still require real receipts".into(),
        ]
    };
    fs::write(out_root.join("latest.json"), serde_json::to_string_pretty(&idx).unwrap()).unwrap();
    let mut md=String::new();
    md.push_str("# PGG Legal Receipt Template Packages\n\n");
    md.push_str(&format!("- Status: `{}`\n- Packages: `{}`\n- Templates: `{}`\n\n", idx.status, idx.package_count, idx.template_count));
    for p in &idx.packages { md.push_str(&format!("- `{}` → `{}` ({})\n", p.case_id, p.package_dir, p.roles.join(", "))); }
    fs::write(out_root.join("latest.md"), md).unwrap();
    println!("{}", serde_json::json!({"ok":true,"status":idx.status,"package_count":idx.package_count,"template_count":idx.template_count,"out":out_root}));
}
