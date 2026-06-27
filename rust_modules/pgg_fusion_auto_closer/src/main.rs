use anyhow::{anyhow, Context, Result};
use chrono::Local;
use rusqlite::{params, Connection, Row};
use serde_json::{json, Value};
use std::{
    env, fs,
    io::{BufRead, BufReader, Write},
    path::PathBuf,
    process::{Command, Stdio},
    time::Duration,
};

#[derive(Debug, Clone)]
struct Provider {
    base_url: String,
    model: String,
    api_mode: String,
    api_key: String,
}
#[derive(Debug, Clone)]
struct Parent {
    id: i64,
    name: String,
    pattern_type: String,
    quality: f64,
    kind: String,
}

fn now() -> String {
    Local::now().format("%Y-%m-%dT%H:%M:%S%z").to_string()
}
fn home() -> PathBuf {
    PathBuf::from(env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".into()))
}
fn default_db() -> PathBuf {
    home().join(".hermes/data/pgg_archon.db")
}
fn config_path() -> PathBuf {
    home().join(".hermes/config.yaml")
}
fn env_path() -> PathBuf {
    home().join(".hermes/.env")
}

fn read_env_var(key: &str) -> Result<String> {
    if let Ok(v) = env::var(key) {
        if !v.is_empty() {
            return Ok(v);
        }
    }
    let text = fs::read_to_string(env_path()).context("read ~/.hermes/.env")?;
    for line in text.lines() {
        let l = line.trim();
        if l.is_empty() || l.starts_with('#') {
            continue;
        }
        let l = l.strip_prefix("export ").unwrap_or(l);
        if let Some((k, v)) = l.split_once('=') {
            if k.trim() == key {
                return Ok(v.trim().trim_matches('"').trim_matches('\'').to_string());
            }
        }
    }
    Err(anyhow!("missing env key {}", key))
}

fn provider() -> Result<Provider> {
    let text = fs::read_to_string(config_path()).context("read ~/.hermes/config.yaml")?;
    let y: serde_yaml::Value = serde_yaml::from_str(&text).context("parse config yaml")?;
    let providers = y
        .get("custom_providers")
        .or_else(|| y.get("providers").and_then(|p| p.get("custom_providers")))
        .ok_or_else(|| anyhow!("custom_providers not found"))?;
    let mut found: Option<Provider> = None;
    if let Some(seq) = providers.as_sequence() {
        for p in seq {
            let name = p.get("name").and_then(|v| v.as_str()).unwrap_or("");
            if name == "gpt55_5yuantoken" {
                let base_url = p
                    .get("base_url")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .trim_end_matches('/')
                    .to_string();
                let model = p
                    .get("model")
                    .or_else(|| p.get("default_model"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("gpt-5.5")
                    .to_string();
                let api_mode = p
                    .get("api_mode")
                    .and_then(|v| v.as_str())
                    .unwrap_or("codex_responses")
                    .to_string();
                let key_env = p
                    .get("key_env")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();
                let api_key = read_env_var(&key_env)?;
                found = Some(Provider {
                    base_url,
                    model,
                    api_mode,
                    api_key,
                });
                break;
            }
        }
    }
    found.ok_or_else(|| anyhow!("gpt55_5yuantoken provider not found"))
}

fn post_gpt(p: &Provider, prompt: &str, system: &str, max_tokens: usize) -> Result<String> {
    let agent = ureq::AgentBuilder::new()
        .timeout(Duration::from_secs(115))
        .build();
    let (url, body) = if p.api_mode == "codex_responses" {
        (
            format!("{}/responses", p.base_url),
            json!({"model":p.model,"instructions":system,"input":prompt,"max_output_tokens":max_tokens}),
        )
    } else if p.api_mode == "chat_completions" {
        (
            format!("{}/chat/completions", p.base_url),
            json!({"model":p.model,"messages":[{"role":"system","content":system},{"role":"user","content":prompt}],"max_tokens":max_tokens,"temperature":0.2}),
        )
    } else {
        return Err(anyhow!("unsupported api_mode {}", p.api_mode));
    };
    let resp: Value = agent
        .post(&url)
        .set("Content-Type", "application/json")
        .set("Accept", "application/json")
        .set("User-Agent", "Hermes-Agent-Fusion-AutoCloser/1.0")
        .set("Authorization", &format!("Bearer {}", p.api_key))
        .send_json(body)
        .map_err(|e| anyhow!("provider_http_error: {}", e))?
        .into_json()
        .context("provider json")?;
    if p.api_mode == "codex_responses" {
        if let Some(s) = resp.get("output_text").and_then(|v| v.as_str()) {
            if !s.trim().is_empty() {
                return Ok(s.to_string());
            }
        }
        let mut parts = vec![];
        if let Some(out) = resp.get("output").and_then(|v| v.as_array()) {
            for item in out {
                if let Some(cont) = item.get("content").and_then(|v| v.as_array()) {
                    for b in cont {
                        if let Some(t) = b
                            .get("text")
                            .or_else(|| b.get("content"))
                            .and_then(|v| v.as_str())
                        {
                            parts.push(t.to_string());
                        }
                    }
                }
            }
        }
        let text = parts.join("\n");
        if text.trim().is_empty() {
            return Err(anyhow!("empty provider response"));
        }
        Ok(text)
    } else {
        resp.get("choices")
            .and_then(|v| v.as_array())
            .and_then(|a| a.get(0))
            .and_then(|c| c.get("message"))
            .and_then(|m| m.get("content"))
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
            .ok_or_else(|| anyhow!("empty chat response"))
    }
}

fn material_kind(code: &str) -> String {
    let s = code.trim_start();
    if s.starts_with('{')
        || s.starts_with('[')
        || s.contains("\"strategy\"")
        || s.contains("'strategy'")
    {
        return "metadata_gene".into();
    }
    if s.contains("def ") || s.contains("class ") || s.contains("fn ") {
        return "python_code".into();
    }
    "text".into()
}
fn row_parent(r: &Row) -> rusqlite::Result<Parent> {
    let code: String = r.get(4)?;
    Ok(Parent {
        id: r.get(0)?,
        name: r.get(1)?,
        pattern_type: r.get(2)?,
        quality: r.get(3)?,
        kind: material_kind(&code),
    })
}

fn choose_pair(conn: &Connection) -> Result<Option<(Parent, Parent)>> {
    let mut stmt = conn.prepare(r#"
        SELECT gl.gene_id, COALESCE(g.name,''), COALESCE(g.pattern_type,''),
               COALESCE(CASE WHEN gl.quality_score < 5.0 AND g.quality_score > 10.0 THEN g.quality_score ELSE gl.quality_score END, g.quality_score, 0) AS q,
               COALESCE(g.code_snippet,'')
        FROM gene_lifecycle gl JOIN genes g ON gl.gene_id=g.id
        WHERE gl.state IN ('promoted','active') AND g.code_snippet IS NOT NULL
          AND LENGTH(g.code_snippet) BETWEEN 500 AND 20000
          AND g.pattern_type NOT IN ('auto_fusion','report','documentation','llm_fusion')
        ORDER BY q DESC LIMIT 120
    "#)?;
    let parents: Vec<Parent> = stmt
        .query_map([], row_parent)?
        .filter_map(|r| r.ok())
        .filter(|p| p.kind != "text")
        .collect();
    for a in &parents {
        for b in &parents {
            if a.id >= b.id {
                continue;
            }
            let has_intake = a.pattern_type == "intake_loop_candidate"
                || b.pattern_type == "intake_loop_candidate";
            let has_code = a.kind == "python_code" || b.kind == "python_code";
            if !has_intake || !has_code {
                continue;
            }
            let pair1 = format!("{},{}", a.id, b.id);
            let pair2 = format!("{},{}", b.id, a.id);
            let exists: i64 = conn.query_row(
                r#"
                SELECT COUNT(*) FROM evolution_genes eg JOIN genes g ON g.id=eg.gene_id
                WHERE g.pattern_type='llm_fusion' AND eg.review_status='approved'
                  AND (eg.parent_gene_id=?1 OR eg.parent_gene_id=?2)
            "#,
                params![pair1, pair2],
                |r| r.get(0),
            )?;
            if exists == 0 {
                return Ok(Some((a.clone(), b.clone())));
            }
        }
    }
    Ok(None)
}

fn extract_code(text: &str) -> String {
    if let Some(start) = text.find("```python") {
        let rest = &text[start + 9..];
        if let Some(end) = rest.find("```") {
            return rest[..end].trim().to_string();
        }
    }
    if let Some(start) = text.find("def ") {
        return text[start..].trim().trim_matches('`').to_string();
    }
    text.trim().to_string()
}

fn ast_check(code: &str) -> Result<()> {
    let mut child = Command::new("python3")
        .arg("-c")
        .arg("import ast,sys; ast.parse(sys.stdin.read()); print('AST_OK')")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()?;
    child.stdin.as_mut().unwrap().write_all(code.as_bytes())?;
    let out = child.wait_with_output()?;
    if !out.status.success() {
        return Err(anyhow!(
            "ast failed: {}",
            String::from_utf8_lossy(&out.stderr)
        ));
    }
    Ok(())
}

fn smoke_check(code: &str) -> Result<Value> {
    let py = format!(
        r#"{}
import json
fn = globals().get('fused_akashic_evm_memory_gate')
if fn is None:
    funcs=[v for v in globals().values() if callable(v) and getattr(v,'__name__','').startswith('fused_')]
    fn=funcs[0] if funcs else None
if fn is None: raise SystemExit('NO_FN')
good_input = {{
 'id': 'auto-smoke-good',
 'source_ref':'auto-smoke',
 'verification_status':'verified',
 'boundary':'internal;local_only;dry_run;no_agi;no_asi;no_t5',
 'candidate':'x',
 'status':'candidate',
 'claimed_status':'candidate',
 'value':1,
 'fitness':1,
 'risk_penalty':0,
 'evidence_grade':1.0,
 'promotion_threshold':0.7,
 'strategy': ['evidence_gate', 'evm_score'],
 'preconditions': ['local_only'],
 'constraints': ['no_network', 'no_file', 'no_command'],
 'validation': {{'static_ast_parse_passed': True, 'standard_gene_template_constructed': True}},
 'signals_match': True,
}}
fake_input = dict(good_input)
fake_input.update({{'verification_status':'candidate','claimed_status':'verified','status':'verified'}})
print(json.dumps({{'good': fn(good_input), 'fake': fn(fake_input)}}, ensure_ascii=False))
"#,
        code
    );
    let out = Command::new("python3").arg("-c").arg(py).output()?;
    if !out.status.success() {
        return Err(anyhow!(
            "smoke failed: {}",
            String::from_utf8_lossy(&out.stderr)
        ));
    }
    let v: Value = serde_json::from_slice(&out.stdout)?;
    let good_ok = v
        .get("good")
        .and_then(|x| x.get("accepted"))
        .and_then(|x| x.as_bool())
        .unwrap_or(false);
    let fake_ok = v
        .get("fake")
        .and_then(|x| x.get("accepted"))
        .and_then(|x| x.as_bool())
        .unwrap_or(false);
    if !good_ok || fake_ok {
        return Err(anyhow!(
            "smoke gate failed: good.accepted={} fake.accepted={}",
            good_ok,
            fake_ok
        ));
    }
    Ok(v)
}

fn write_offspring(conn: &Connection, a: &Parent, b: &Parent, code: &str) -> Result<i64> {
    let max_id: i64 = conn.query_row("SELECT COALESCE(MAX(id),0) FROM genes", [], |r| r.get(0))?;
    let id = max_id + 1;
    let q = (((a.quality + b.quality) / 2.0) * 0.9 * 100.0).round() / 100.0;
    let name = format!(
        "llm_fusion_{}_{}",
        a.name.chars().take(20).collect::<String>(),
        b.name.chars().take(20).collect::<String>()
    )
    .replace(' ', "_")
    .chars()
    .take(60)
    .collect::<String>();
    let ts = now();
    conn.execute("INSERT INTO genes (id,name,pattern_type,source_repo,code_snippet,quality_score,extracted_at) VALUES (?1,?2,'llm_fusion','fusion_auto_closer',?3,?4,?5)", params![id,name,code,q,ts])?;
    conn.execute("INSERT OR IGNORE INTO gene_lifecycle (gene_id,state,candidate_at,quality_score) VALUES (?1,'candidate',?2,?3)", params![id,ts,q])?;
    conn.execute("INSERT OR IGNORE INTO evolution_genes (gene_id,parent_gene_id,state,generation,mutation_vector,fitness_before,fitness_after,created_at,review_status,review_channel) VALUES (?1,?2,'candidate',1,'llm_fusion',NULL,?3,?4,'pending','gpt55_auto_generated')", params![id, format!("{},{}", a.id,b.id), q, ts])?;
    Ok(id)
}

fn approve_and_promote(conn: &Connection, id: i64, review: &Value) -> Result<()> {
    let ts = now();
    let conf = review
        .get("confidence")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.0);
    conn.execute("UPDATE evolution_genes SET state='verified', review_status='approved', review_channel='gpt55_auto_review_gate', review_confidence=?1, review_reason=?2, reviewed_at=?3 WHERE gene_id=?4 AND mutation_vector='llm_fusion'", params![conf, review.to_string(), ts, id])?;
    conn.execute("UPDATE gene_lifecycle SET state='promoted', promoted_at=?1 WHERE gene_id=?2 AND state='candidate'", params![ts,id])?;
    let q: f64 = conn.query_row(
        "SELECT quality_score FROM genes WHERE id=?1",
        params![id],
        |r| r.get(0),
    )?;
    conn.execute("INSERT OR IGNORE INTO evolution_genes (gene_id,parent_gene_id,state,generation,mutation_vector,fitness_before,fitness_after,promoted_at,retired_at,evidence_ref,created_at,review_status,review_channel) VALUES (?1,NULL,'promoted',1,'auto_promoted',NULL,?2,?3,NULL,'{}',?3,'approved','promotion_gate_after_llm_review')", params![id,q,ts])?;
    Ok(())
}

struct RunLock {
    path: PathBuf,
}
impl Drop for RunLock {
    fn drop(&mut self) {
        let _ = fs::remove_dir(&self.path);
    }
}
fn acquire_lock() -> Result<Option<RunLock>> {
    let dir = home().join(".hermes/run/pgg-fusion-auto-closer.lock");
    if let Some(parent) = dir.parent() {
        fs::create_dir_all(parent)?;
    }
    match fs::create_dir(&dir) {
        Ok(()) => Ok(Some(RunLock { path: dir })),
        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => Ok(None),
        Err(e) => Err(e.into()),
    }
}

fn ledger_recent_success() -> Value {
    let ledger = home().join(".hermes/logs/periodic-1h/ledger.jsonl");
    if !ledger.exists() {
        return json!({"path": ledger, "exists": false, "recent_rc0": false});
    }
    let file = match fs::File::open(&ledger) {
        Ok(f) => f,
        Err(e) => {
            return json!({"path": ledger, "exists": true, "recent_rc0": false, "error": e.to_string()})
        }
    };
    let lines: Vec<String> = BufReader::new(file)
        .lines()
        .filter_map(|l| l.ok())
        .collect();
    let mut matches = vec![];
    for line in lines.iter().rev().take(200) {
        if line.contains("\"task\":\"fusion_auto_closer\"") {
            matches.push(line.clone());
            if matches.len() >= 5 {
                break;
            }
        }
    }
    let recent_rc0 = matches.iter().any(|l| l.contains("\"rc\":0"));
    json!({"path": ledger, "exists": true, "recent_rc0": recent_rc0, "recent": matches})
}

fn status_report() -> Result<Value> {
    let db = default_db();
    let script = home().join(".hermes/scripts/pgg_periodic_1h.sh");
    let binary = home().join(".hermes/bin/pgg-fusion-auto-closer");
    let script_text = fs::read_to_string(&script).unwrap_or_default();
    let in_supervisor = script_text.contains("fusion_auto_closer")
        && script_text.contains("pgg-fusion-auto-closer");
    let mut counts = json!({"db_path": db, "exists": db.exists()});
    if db.exists() {
        let conn = Connection::open(&db)?;
        let llm_total: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM genes WHERE pattern_type='llm_fusion'",
                [],
                |r| r.get(0),
            )
            .unwrap_or(0);
        let auto_total: i64 = conn.query_row("SELECT COUNT(*) FROM genes WHERE pattern_type='llm_fusion' AND source_repo='fusion_auto_closer'", [], |r| r.get(0)).unwrap_or(0);
        let auto_promoted: i64 = conn.query_row("SELECT COUNT(DISTINCT g.id) FROM genes g JOIN gene_lifecycle gl ON gl.gene_id=g.id WHERE g.pattern_type='llm_fusion' AND g.source_repo='fusion_auto_closer' AND gl.state='promoted'", [], |r| r.get(0)).unwrap_or(0);
        let approved: i64 = conn.query_row("SELECT COUNT(DISTINCT g.id) FROM genes g JOIN evolution_genes eg ON eg.gene_id=g.id WHERE g.pattern_type='llm_fusion' AND g.source_repo='fusion_auto_closer' AND eg.review_status='approved'", [], |r| r.get(0)).unwrap_or(0);
        counts = json!({"db_path": db, "exists": true, "llm_fusion_total": llm_total, "auto_closer_total": auto_total, "auto_closer_promoted": auto_promoted, "auto_closer_approved": approved});
    }
    let ledger = ledger_recent_success();
    let pass = binary.exists()
        && in_supervisor
        && ledger
            .get("recent_rc0")
            .and_then(|v| v.as_bool())
            .unwrap_or(false)
        && counts
            .get("auto_closer_total")
            .and_then(|v| v.as_i64())
            .unwrap_or(0)
            > 0
        && counts
            .get("auto_closer_promoted")
            .and_then(|v| v.as_i64())
            .unwrap_or(0)
            > 0;
    Ok(json!({
        "schema": "pgg_fusion_auto_closer/status/v1",
        "created_at": now(),
        "status": if pass { "PASS" } else { "WATCH" },
        "binary": {"path": binary, "exists": binary.exists()},
        "supervisor": {"script": script, "contains_task": in_supervisor},
        "ledger": ledger,
        "db": counts,
        "boundary": "read-only status; no provider call; no DB write; does not prove runtime gene consumption"
    }))
}

fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    let dry_run = args.iter().any(|a| a == "--dry-run");
    if args.iter().any(|a| a == "--status") {
        println!("{}", serde_json::to_string_pretty(&status_report()?)?);
        return Ok(());
    }
    let _lock = match acquire_lock()? {
        Some(lock) => lock,
        None => {
            println!(
                "{}",
                serde_json::to_string_pretty(
                    &json!({"schema":"pgg_fusion_auto_closer/v1","status":"SKIP_LOCKED","created_at":now(),"boundary":"another fusion_auto_closer run is active; no DB write"})
                )?
            );
            return Ok(());
        }
    };
    let db = default_db();
    let p = provider()?;
    let conn = Connection::open(&db)?;
    let before: i64 = conn.query_row(
        "SELECT COUNT(*) FROM genes WHERE pattern_type='llm_fusion'",
        [],
        |r| r.get(0),
    )?;
    let Some((a, b)) = choose_pair(&conn)? else {
        println!(
            "{}",
            serde_json::to_string_pretty(
                &json!({"schema":"pgg_fusion_auto_closer/v1","status":"NO_PAIR","created_at":now(),"before_llm_fusion":before})
            )?
        );
        return Ok(());
    };
    let gen_prompt = format!("生成一个很短的单一 Python 函数代码块，函数名 fused_akashic_evm_memory_gate。禁止 import、禁止 class、禁止文件/网络/命令/eval/exec。只用 dict/list/float/str/bool 基础语法。输入 dict 或 list[dict]；返回 dict 含 status,score,accepted,reasons,evidence。必须：1) source_ref、verification_status、boundary、candidate 证据门禁；2) claimed_status/status 为 verified 但 verification_status != verified 时拒绝；3) score = clamp(0..1, 0.35*value + 0.35*fitness + 0.2*evidence_grade - 0.25*risk_penalty)；4) accepted 需 verified+source_ref+boundary+candidate存在+score>=promotion_threshold+无reasons。只输出代码块。父本A={} {} quality{}；父本B={} {} quality{}。", a.id,a.pattern_type,a.quality,b.id,b.pattern_type,b.quality);
    let gen_text = post_gpt(
        &p,
        &gen_prompt,
        "只输出一个短 python 代码块；不要解释；不要 import。",
        700,
    )?;
    let code = extract_code(&gen_text);
    if let Err(e) = ast_check(&code) {
        println!(
            "{}",
            serde_json::to_string_pretty(
                &json!({"schema":"pgg_fusion_auto_closer/v1","status":"REJECTED_NO_WRITE","stage":"ast_check","error":e.to_string(),"pair":[a.id,b.id],"before_llm_fusion":before,"boundary":"fail-closed; no DB write"})
            )?
        );
        return Ok(());
    }
    let smoke = match smoke_check(&code) {
        Ok(v) => v,
        Err(e) => {
            println!(
                "{}",
                serde_json::to_string_pretty(
                    &json!({"schema":"pgg_fusion_auto_closer/v1","status":"REJECTED_NO_WRITE","stage":"smoke_check","error":e.to_string(),"pair":[a.id,b.id],"before_llm_fusion":before,"boundary":"fail-closed; no DB write"})
                )?
            );
            return Ok(());
        }
    };
    let review_prompt = format!("只输出严格 JSON: {{\"verdict\":\"PASS|FAIL\",\"confidence\":0.0,\"approved\":true|false,\"reasons\":[\"...\"]}}。审计代码是否安全、单函数、非简单拼接、含证据门禁+EVM评分、candidate不得冒充verified、结构化返回。\n```python\n{}\n```", code);
    let review_text = post_gpt(&p, &review_prompt, "严格 JSON 审计器。只输出 JSON。", 600)?;
    let review: Value = serde_json::from_str(review_text.trim()).or_else(|_| {
        let s = review_text
            .find('{')
            .ok_or_else(|| anyhow!("no json start"))?;
        let e = review_text
            .rfind('}')
            .ok_or_else(|| anyhow!("no json end"))?;
        serde_json::from_str(&review_text[s..=e]).map_err(|e| anyhow!(e))
    })?;
    let approved = review
        .get("approved")
        .and_then(|v| v.as_bool())
        .unwrap_or(false)
        || review.get("verdict").and_then(|v| v.as_str()) == Some("PASS");
    if dry_run {
        println!(
            "{}",
            serde_json::to_string_pretty(
                &json!({"schema":"pgg_fusion_auto_closer/v1","dry_run":true,"pair":[a.id,b.id],"smoke":smoke,"review":review,"approved":approved,"before_llm_fusion":before})
            )?
        );
        return Ok(());
    }
    let backup = db.with_extension(format!(
        "db.bak.{}",
        Local::now().format("%Y%m%d%H%M%S-fusion-auto-closer")
    ));
    fs::copy(&db, &backup)?;
    let id = write_offspring(&conn, &a, &b, &code)?;
    if approved {
        approve_and_promote(&conn, id, &review)?;
    }
    let after: i64 = conn.query_row(
        "SELECT COUNT(*) FROM genes WHERE pattern_type='llm_fusion'",
        [],
        |r| r.get(0),
    )?;
    println!(
        "{}",
        serde_json::to_string_pretty(
            &json!({"schema":"pgg_fusion_auto_closer/v1","created_at":now(),"dry_run":false,"backup":backup,"pair":[a.id,b.id],"offspring_id":id,"approved":approved,"review":review,"smoke":smoke,"before_llm_fusion":before,"after_llm_fusion":after,"boundary":"direct provider HTTP; no Hermes session MCP import dependency; pending/promote determined by GPT5.5 JSON review"})
        )?
    );
    Ok(())
}
