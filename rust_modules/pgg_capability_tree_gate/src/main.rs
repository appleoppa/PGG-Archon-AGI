use chrono::{Local, SecondsFormat};
use serde_json::{json, Value};
use std::{env, fs, path::{Path, PathBuf}, process::Command};

fn home() -> PathBuf { PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string())) }
fn exists(p: &Path) -> bool { p.exists() }
fn size(p: &Path) -> u64 { fs::metadata(p).map(|m| m.len()).unwrap_or(0) }
fn line_count(p: &Path) -> usize { fs::read_to_string(p).map(|s| s.lines().filter(|l| !l.trim().is_empty()).count()).unwrap_or(0) }
fn command_ok(cmd: &str, args: &[&str]) -> Value {
    match Command::new(cmd).args(args).output() {
        Ok(o) => json!({"ok": o.status.success(), "rc": o.status.code(), "stdout_prefix": String::from_utf8_lossy(&o.stdout).chars().take(240).collect::<String>()}),
        Err(e) => json!({"ok": false, "error": e.to_string()}),
    }
}
fn latest_file(dir: &Path, prefix: &str, suffix: &str) -> Option<PathBuf> {
    let mut rows: Vec<(std::time::SystemTime, PathBuf)> = Vec::new();
    if let Ok(rd) = fs::read_dir(dir) {
        for e in rd.flatten() {
            let p = e.path();
            let name = p.file_name().and_then(|x| x.to_str()).unwrap_or("");
            if name.starts_with(prefix) && name.ends_with(suffix) {
                let mt = e.metadata().and_then(|m| m.modified()).unwrap_or(std::time::UNIX_EPOCH);
                rows.push((mt, p));
            }
        }
    }
    rows.sort_by(|a,b| b.0.cmp(&a.0));
    rows.first().map(|x| x.1.clone())
}
fn main() {
    let h = home();
    let hermes = h.join(".hermes");
    let workspace = hermes.join("workspace/pgg-archon-governance");
    let mut nodes: Vec<Value> = Vec::new();
    let manifest = hermes.join("data/EVOLUTION_MANIFEST.json");
    let report_quality = hermes.join("workspace/pgg-archon-governance/report-quality-gate/latest.json");
    let autonomy_latest = latest_file(&workspace.join("autonomy-default"), "autonomy_", ".json");
    let capabilities = vec![
        ("autonomy_loop", hermes.join("bin/pgg-autonomy-default-loop"), "daily probes / low-risk fixes / report quality subprobe"),
        ("aris_reflection", hermes.join("bin/pgg-aris-reflection"), "three-layer reflection surface"),
        ("neuron_system", hermes.join("bin/pgg_neuron_system_status"), "candidate-only neural consolidation"),
        ("report_quality_gate", hermes.join("bin/pgg-report-quality-gate"), "morning/daily report pipeline quality gate"),
        ("goal_gate", hermes.join("bin/hermes-goal"), "unified goal audit"),
        ("memory_system", hermes.join("bin/pgg_memory_system"), "curated memory/Akashic status"),
        ("omniroute_status", hermes.join("bin/omniroute_ui_status"), "provider/UI route status"),
    ];
    let mut present = 0;
    for (id, path, desc) in capabilities {
        let ok = exists(&path);
        if ok { present += 1; }
        nodes.push(json!({"id": id, "status": if ok {"PRESENT"} else {"MISSING"}, "path": path, "description": desc, "bytes": size(&path)}));
    }
    let manifest_present = exists(&manifest) && size(&manifest) > 100;
    let rq_present = exists(&report_quality) && size(&report_quality) > 50;
    let autonomy_present = autonomy_latest.as_ref().map(|p| exists(p)).unwrap_or(false);
    let score = ((present as f64 / 7.0) * 70.0
        + if manifest_present {10.0} else {0.0}
        + if rq_present {10.0} else {0.0}
        + if autonomy_present {10.0} else {0.0}).round() as i64;
    let status = if score >= 85 {"PASS_CAPABILITY_TREE_LOCAL_READY"} else if score >= 60 {"WATCH_CAPABILITY_TREE_PARTIAL"} else {"BLOCKED_CAPABILITY_TREE_MISSING"};
    let result = json!({
        "schema":"pgg-capability-tree-gate/v1",
        "generated_at": Local::now().to_rfc3339_opts(SecondsFormat::Secs, true),
        "status": status,
        "score": score,
        "nodes": nodes,
        "sources": {
            "manifest": {"path": manifest, "exists": manifest_present, "bytes": size(&manifest)},
            "report_quality_latest": {"path": report_quality, "exists": rq_present, "lines": line_count(&report_quality)},
            "autonomy_latest": autonomy_latest,
            "launchd_autonomy": command_ok("launchctl", &["list"])
        },
        "boundary": [
            "read-only capability tree generation",
            "no PCEC 3h daemon enabled",
            "root capability_tree.md remains compatibility index",
            "does not prove external benchmark / AGI level / legal correctness"
        ]
    });
    let out_dir = workspace.join("capability-tree-gate");
    fs::create_dir_all(&out_dir).ok();
    let stamp = Local::now().format("%Y%m%d-%H%M%S").to_string();
    let jp = out_dir.join(format!("capability-tree-{stamp}.json"));
    fs::write(&jp, serde_json::to_string_pretty(&result).unwrap()).unwrap();
    fs::write(out_dir.join("latest.json"), serde_json::to_string_pretty(&result).unwrap()).unwrap();
    let mut md = String::new();
    md.push_str("# PGG/Hermes Capability Tree Gate\n\n");
    md.push_str(&format!("Status: `{}`  Score: `{}`\n\n", status, score));
    md.push_str("## Nodes\n\n");
    if let Some(arr)=result.get("nodes").and_then(|v| v.as_array()) {
        for n in arr { md.push_str(&format!("- **{}** — {} — `{}`\n", n["id"].as_str().unwrap_or(""), n["description"].as_str().unwrap_or(""), n["status"].as_str().unwrap_or(""))); }
    }
    md.push_str("\n## Boundary\n\n- Read-only; no PCEC daemon; no AGI/T5/external benchmark claim.\n");
    fs::write(out_dir.join("capability-tree-latest.md"), md).unwrap();
    println!("{}", serde_json::to_string(&json!({"ok":true,"status":status,"score":score,"json":jp,"latest":out_dir.join("latest.json")})).unwrap());
}
