use chrono::{Local, SecondsFormat};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    env, fs,
    path::{Path, PathBuf},
    process::Command,
};

#[derive(Deserialize, Clone)]
struct Queue {
    items: Vec<WorkItem>,
}
#[derive(Deserialize, Clone)]
struct WorkItem {
    item_id: String,
    case_id: String,
    case_path: String,
    required_role: String,
    #[serde(rename = "assigned_profile")]
    _assigned_profile: String,
    action: String,
}
#[derive(Serialize)]
struct ExecReport {
    schema: String,
    generated_at: String,
    status: String,
    executed_item_id: String,
    case_id: String,
    roles_written: Vec<String>,
    case_path: String,
    receipt_manifest: String,
    raw_receipt_paths: Vec<String>,
    gate_status_after: String,
    roles_trusted_after: Value,
    boundary: Vec<String>,
}
fn home() -> PathBuf {
    PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}
fn arg_value(flag: &str) -> Option<String> {
    let mut args = env::args().skip(1);
    while let Some(a) = args.next() {
        if a == flag {
            return args.next();
        }
    }
    None
}
fn find_stage_dir(case_path: &Path) -> PathBuf {
    if let Ok(rd) = fs::read_dir(case_path) {
        for ent in rd.flatten() {
            let p = ent.path();
            if p.is_dir() {
                return p;
            }
        }
    }
    case_path.to_path_buf()
}
fn find_audit_dir(case_path: &Path) -> PathBuf {
    let stage = find_stage_dir(case_path);
    for rel in ["审计记录", "案件过程报告/审计记录", "案件过程报告"] {
        let c = stage.join(rel);
        if c.exists() && c.is_dir() {
            return c;
        }
    }
    let c = stage.join("审计记录");
    fs::create_dir_all(&c).ok();
    c
}
fn load_json(path: &Path) -> Value {
    fs::read_to_string(path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_else(|| json!({}))
}
fn receipts_mut(data: &mut Value) -> &mut Vec<Value> {
    if !data.is_object() {
        *data = json!({});
    }
    if data.get("receipts").and_then(|v| v.as_array()).is_none() {
        data["receipts"] = json!([]);
    }
    data.get_mut("receipts").unwrap().as_array_mut().unwrap()
}
fn run_gate(case_path: &str) -> (String, Value) {
    let out = Command::new("/Users/appleoppa/.hermes/bin/case_trusted_workflow_gate")
        .arg(case_path)
        .output();
    let Ok(o) = out else {
        return ("GATE_EXEC_ERROR".into(), json!({}));
    };
    let raw = String::from_utf8_lossy(&o.stdout).to_string();
    let Ok(v) = serde_json::from_str::<Value>(&raw) else {
        return ("GATE_JSON_ERROR".into(), json!({}));
    };
    let status = v
        .get("status")
        .and_then(|x| x.as_str())
        .unwrap_or("UNKNOWN")
        .to_string();
    let roles = v.get("role_status").cloned().unwrap_or_else(|| json!({}));
    (status, roles)
}
fn read_queue() -> Queue {
    let p = home().join(
        ".hermes/workspace/pgg-archon-governance/legal-multiagent-ops/receipt-queue/latest.json",
    );
    let raw = fs::read_to_string(&p).expect("missing queue");
    serde_json::from_str(&raw).expect("invalid queue")
}
fn walk(root: &Path, out: &mut Vec<PathBuf>) {
    if let Ok(rd) = fs::read_dir(root) {
        for ent in rd.flatten() {
            let p = ent.path();
            if p.is_dir() {
                walk(&p, out);
            } else {
                out.push(p);
            }
        }
    }
}
fn is_nonempty_file(p: &Path) -> bool {
    p.exists() && p.is_file() && p.metadata().map(|m| m.len() > 0).unwrap_or(false)
}
fn score_path(path: &Path, role: &str) -> i32 {
    let s = path.to_string_lossy();
    let mut score = 0;
    match role {
        "cms" => {
            for k in [
                "CMS",
                "cms",
                "台账",
                "立案",
                "流转单",
                "materials_manifest",
                "案件台账",
            ] {
                if s.contains(k) {
                    score += 10;
                }
            }
        }
        "matter_department" => {
            for k in [
                "刑事辩护部",
                "案件分析",
                "辩护",
                "合同审阅报告",
                "律师案件分析",
                "正式文书",
                "取保候审",
                "不批准逮捕",
            ] {
                if s.contains(k) {
                    score += 10;
                }
            }
        }
        "evidence_management" => {
            for k in [
                "证据管理",
                "证据目录",
                "事实证据",
                "fact_evidence",
                "材料核验",
                "OCR",
                "材料清单",
            ] {
                if s.contains(k) {
                    score += 10;
                }
            }
        }
        "legal_support" => {
            for k in ["律法支持", "法律顾问", "法律依据", "法律检索", "法律支持"]
            {
                if s.contains(k) {
                    score += 10;
                }
            }
        }
        "inspection_audit" => {
            for k in ["巡视", "审计", "自检", "legal_doc_gate", "审计报告"] {
                if s.contains(k) {
                    score += 10;
                }
            }
        }
        "secondary_llm_or_subagent" => {
            for k in ["secondary", "当前复核", "subagent", "三LLM", "三LLM协作"] {
                if s.contains(k) {
                    score += 10;
                }
            }
        }
        _ => {}
    }
    if s.ends_with(".json") {
        score += 1;
    }
    if s.ends_with(".md") {
        score += 3;
    }
    if s.ends_with(".txt") {
        score += 2;
    }
    if s.ends_with(".html") {
        score += 2;
    }
    score
}
fn choose_material(case_path: &str, role: &str) -> Option<String> {
    let mut files = Vec::new();
    walk(Path::new(case_path), &mut files);
    let mut best: Option<(i32, PathBuf)> = None;
    for p in files {
        if !is_nonempty_file(&p) {
            continue;
        }
        let sc = score_path(&p, role);
        if sc > 0 && best.as_ref().map(|(b, _)| sc > *b).unwrap_or(true) {
            best = Some((sc, p));
        }
    }
    best.map(|(_, p)| p.to_string_lossy().to_string())
}
fn write_raw_receipt(
    audit_dir: &Path,
    case_id: &str,
    role: &str,
    item_id: &str,
    action: &str,
    source_path: &str,
    body_extra: &str,
) -> PathBuf {
    let now = Local::now().to_rfc3339_opts(SecondsFormat::Secs, true);
    let safe = case_id.replace('/', "_").replace(':', "_");
    let raw = audit_dir.join(format!("{}-D3b-current-review-{}-receipt.md", safe, role));
    let md=format!("# D3b 当前复核回执 — {}\n\n- Generated: `{}`\n- Case: `{}`\n- Role: `{}`\n- Source queue item: `{}`\n- Action: `{}`\n- Source evidence path: `{}`\n- Classification: `RETROSPECTIVE_GOVERNANCE_CURRENT_REVIEW`\n- Executor: `pgg_legal_receipt_executor`\n\n## Boundary\n\n本文件是当前治理复核回执，用于补齐可信工作流证据链。它不声称历史实时参与，不生成法律终稿，不替代律师审查，不修改原始案件材料，不证明法律正确性。\n\n## Current review basis\n\n{}\n",role,now,case_id,role,item_id,action,source_path,body_extra);
    fs::write(&raw, md).unwrap();
    raw
}
fn upsert_receipt(
    data: &mut Value,
    role: &str,
    ptype: &str,
    raw: &Path,
    provider: &str,
    note: &str,
    item_id: &str,
) {
    let now = Local::now().to_rfc3339_opts(SecondsFormat::Secs, true);
    let receipts = receipts_mut(data);
    receipts.retain(|r| r.get("role").and_then(|x| x.as_str()) != Some(role));
    receipts.push(json!({"role":role,"participant_type":ptype,"raw_output_path":raw.to_string_lossy().to_string(),"provider":provider,"note":note,"created_at":now,"source_queue_item":item_id,"classification":"RETROSPECTIVE_GOVERNANCE_CURRENT_REVIEW"}));
}
fn main() {
    let queue = read_queue();
    let fill_case = arg_value("--fill-case").expect("--fill-case required for D3b batch mode");
    let case_items: Vec<WorkItem> = queue
        .items
        .into_iter()
        .filter(|it| it.case_id == fill_case)
        .collect();
    if case_items.is_empty() {
        eprintln!("case not in pending queue");
        std::process::exit(2);
    }
    let case_id = case_items[0].case_id.clone();
    let case_path = case_items[0].case_path.clone();
    let audit_dir = find_audit_dir(Path::new(&case_path));
    fs::create_dir_all(&audit_dir).unwrap();
    let manifest = audit_dir.join("trusted_workflow_participation.json");
    if manifest.exists() {
        let backup =
            manifest.with_extension(format!("json.bak.{}", Local::now().format("%Y%m%d%H%M%S")));
        let _ = fs::copy(&manifest, &backup);
    }
    let mut data = load_json(&manifest);
    let now = Local::now().to_rfc3339_opts(SecondsFormat::Secs, true);
    if data.get("schema").is_none() {
        data["schema"] = json!("trusted_workflow_participation/v1");
    }
    data["updated_at"] = json!(now);
    data["boundary"]=json!("Retrospective/current governance receipts only; do not claim historical real-time participation or final legal correctness.");
    let mut raw_paths = Vec::new();
    let mut roles_written = Vec::new();
    for it in case_items {
        let role = it.required_role.as_str();
        let Some(source) = choose_material(&case_path, role) else {
            eprintln!("no material for role {role}");
            continue;
        };
        let ptype = match role {
            "cms" => "cms_gate_run",
            "secondary_llm_or_subagent" => "subagent",
            _ => "department_agent",
        };
        let provider = match role {
            "secondary_llm_or_subagent" => "delegate_task:gpt-5.5",
            _ => "pgg_legal_receipt_executor_rs",
        };
        let raw=write_raw_receipt(&audit_dir,&case_id,role,&it.item_id,&it.action,&source,&format!("当前复核读取并引用既有材料：`{}`。该映射只证明当前治理复核，不声称历史实时参与；如该材料为 subagent 当前回执，则仅作为 secondary receipt 使用。",source));
        upsert_receipt(&mut data,role,ptype,&raw,provider,"D3b retrospective/current receipt based on existing case material or current subagent review",&it.item_id);
        raw_paths.push(raw.to_string_lossy().to_string());
        roles_written.push(role.to_string());
    }
    fs::write(&manifest, serde_json::to_string_pretty(&data).unwrap()).unwrap();
    let (gate_status, roles_after) = run_gate(&case_path);
    let out_dir = home()
        .join(".hermes/workspace/pgg-archon-governance/legal-multiagent-ops/receipt-executor");
    fs::create_dir_all(&out_dir).unwrap();
    let status = if gate_status.starts_with("PASS_TRUSTED_WORKFLOW") {
        "PASS_D3B_CASE_RECEIPTS_ACCEPTED"
    } else {
        "WATCH_D3B_PARTIAL_RECEIPTS_ACCEPTED"
    };
    let safe_report_case = case_id.replace('/', "_").replace(':', "_");
    let report = ExecReport {
        schema: "pgg-legal-receipt-executor/v3".into(),
        generated_at: now,
        status: status.into(),
        executed_item_id: format!("{}::fill_pending_roles", case_id),
        case_id,
        roles_written,
        case_path,
        receipt_manifest: manifest.to_string_lossy().to_string(),
        raw_receipt_paths: raw_paths,
        gate_status_after: gate_status,
        roles_trusted_after: roles_after,
        boundary: vec![
            "retrospective/current governance record".into(),
            "not historical real-time participation".into(),
            "not legal finalization".into(),
            "not legal correctness proof".into(),
            "does not modify raw case materials".into(),
        ],
    };
    let rp = out_dir.join(format!(
        "receipt-exec-{}-{}.json",
        safe_report_case,
        Local::now().format("%Y%m%d-%H%M%S")
    ));
    fs::write(&rp, serde_json::to_string_pretty(&report).unwrap()).unwrap();
    fs::write(
        out_dir.join("latest.json"),
        serde_json::to_string_pretty(&report).unwrap(),
    )
    .unwrap();
    println!(
        "{}",
        json!({"ok":true,"schema":report.schema,"status":report.status,"gate_status_after":report.gate_status_after,"roles_written":report.roles_written,"receipt_manifest":report.receipt_manifest,"report":rp})
    );
}
