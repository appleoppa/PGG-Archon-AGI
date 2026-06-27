/// P15: `hermes_pgg_ultimate_formula` — APEX Ultimate 终极进化公式
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use serde_json::{json, Value};

fn fin(v: &Value, d: f64) -> f64 { match v.as_f64() { Some(n) if n.is_finite() => n, _ => d } }
fn clamp(v: f64, lo: f64, hi: f64) -> f64 { v.max(lo).min(hi) }
fn r3(v: f64) -> f64 { (v * 1000.0).round() / 1000.0 }
fn r6(v: f64) -> f64 { (v * 1_000_000.0).round() / 1_000_000.0 }

macro_rules! obj {
    ($s:expr) => {{
        let _v: Value = if $s == "null" || $s.is_empty() { json!({}) } else { serde_json::from_str($s).unwrap_or(json!({})) };
        _v.as_object().cloned().unwrap_or_default()
    }};
}

#[pyfunction]
fn compute_evm_full(s: &str) -> PyResult<String> {
    let o = obj!(s);
    let mut c = json!({});
    let mut sc = 0.0;
    for (n, w) in [("task_success",0.25),("correctness",0.20),("closure",0.15),("reasoning_stability",0.10),("tool_use",0.10),("long_context_state",0.10),("self_repair",0.10)] {
        let v = fin(o.get(n).unwrap_or(&json!(50.0)), 50.0).max(0.0).min(100.0);
        c.as_object_mut().unwrap().insert(n.to_string(), json!(v));
        sc += v * w;
    }
    Ok(json!({"score": r3(sc), "components": c}).to_string())
}

#[pyfunction]
fn compute_sigma_delta(s: &str) -> PyResult<String> {
    let o = obj!(s);
    let mut sc = 0.0;
    for (n, w) in [("hallucination",20.0),("security",20.0),("unclosed_debt",15.0),("cost",10.0),("latency",8.0),("instability",10.0),("memory_pollution",7.0),("tool_risk",5.0),("governance_debt",5.0)] {
        sc += fin(o.get(n).unwrap_or(&json!(0.0)), 0.0).max(0.0).min(1.0) * w;
    }
    let ca = |k: &str| o.get(k).and_then(|x| x.as_bool()).unwrap_or(false);
    let cn = |k: &str| o.get(k).map(|x| fin(x, 0.0) >= 1.0).unwrap_or(false);
    Ok(json!({"score": sc.min(100.0), "critical_active": ca("critical")||cn("p0")||cn("critical_security")||cn("credential_leak")||cn("false_completion")}).to_string())
}

#[pyfunction]
#[pyo3(signature = (v = "null", a = "null", b = "null"))]
fn compute_omega_a(v: &str, a: &str, b: &str) -> PyResult<String> {
    let val: Value = if v == "null" { json!(1.0) } else { serde_json::from_str(v).unwrap_or(json!(1.0)) };
    let ap: Value = if a == "null" { Value::Null } else { serde_json::from_str(a).unwrap_or(Value::Null) };
    let bs: Value = if b == "null" { Value::Null } else { serde_json::from_str(b).unwrap_or(Value::Null) };
    let (raw, src) = if !ap.is_null() && !bs.is_null() {
        let bv = fin(&bs, 0.0);
        (if bv.abs() < 0.001 { 1.0 } else { fin(&ap, 0.0) / bv }, "net_score_ratio")
    } else {
        (fin(&val, 1.0), if v == "null" { "direct_or_default" } else { "direct" })
    };
    Ok(json!({"value": r3(clamp(raw,0.5,2.0)), "raw_value": r6(raw), "source": src}).to_string())
}

#[pyfunction]
#[pyo3(signature = (sig = "null", d = "null"))]
fn compute_theta_stable(sig: &str, d: &str) -> PyResult<String> {
    let direct: Value = if d == "null" { Value::Null } else { serde_json::from_str(d).unwrap_or(Value::Null) };
    if !direct.is_null() {
        let raw = fin(&direct, 1.0).max(0.0).min(2.0);
        return Ok(json!({"value": r3(clamp(raw,0.5,2.0)), "raw_score": r3(raw*100.0), "source":"direct_theta_value"}).to_string());
    }
    let o = obj!(sig);
    let mut rs = 0.0;
    for k in ["psi_practice_knowledge_unity","lambda_causal_chain","gamma_self_healing_allocation","xi_deterministic_execution","phi_closed_loop_control","upsilon_resource_harmony"] {
        rs += fin(o.get(k).unwrap_or(&json!(75.0)), 75.0).max(0.0).min(100.0) * (1.0/6.0);
    }
    Ok(json!({"value": r3(clamp(0.5+rs/100.0*1.5,0.5,2.0)), "raw_score": r3(rs), "source":"six_dimensional_theta_stable"}).to_string())
}

#[pyfunction]
#[pyo3(signature = (evm="null",del="null",om="null",an="null",bn="null",aa="null",bb="null",ts="null",td="null",tao="null",ct=1.0))]
fn build_ultimate_evolution_formula_report(evm:&str,del:&str,om:&str,an:&str,bn:&str,aa:&str,bb:&str,ts:&str,td:&str,tao:&str,ct:f64) -> PyResult<String> {
    let e: Value = serde_json::from_str(&compute_evm_full(evm)?).unwrap();
    let d: Value = serde_json::from_str(&compute_sigma_delta(del)?).unwrap();
    let o: Value = serde_json::from_str(&compute_omega_a(om,an,bn)?).unwrap();
    let t: Value = serde_json::from_str(&compute_theta_stable(ts,td)?).unwrap();
    let aa_v: Value = if aa == "null" { json!(1.0) } else { serde_json::from_str(aa).unwrap_or(json!(1.0)) };
    let bb_v: Value = if bb == "null" { json!(1.0) } else { serde_json::from_str(bb).unwrap_or(json!(1.0)) };
    let al = clamp(fin(&aa_v, 1.0), 0.0, 2.0);
    let be = clamp(fin(&bb_v, 1.0), 0.0, 2.0);
    let tr: Value = if tao == "null" { json!({}) } else { serde_json::from_str(tao).unwrap_or(json!({})) };
    let ta = clamp(fin(tr.get("A").unwrap_or(&json!(1.0)), 1.0), 0.0, 2.0);
    let tb = clamp(fin(tr.get("B").unwrap_or(&json!(1.0)), 1.0), 0.0, 2.0);
    let tt = clamp(fin(tr.get("tdhlgwb").unwrap_or(&json!(1.0)), 1.0), 0.0, 2.0);
    let raw = fin(&o["value"],1.0)*al*be*fin(&t["value"],1.0)*ta*tb*tt*fin(&e["score"],0.0)-fin(&d["score"],0.0);
    let ca = d["critical_active"].as_bool().unwrap_or(false) && ct <= 1.0;
    let sc = if ca { 0.0 } else { raw.max(0.0).min(100.0) };
    let st = if ca { "BLOCKED" } else if sc >= 75.0 { "PASS" } else if sc >= 50.0 { "WATCH" } else { "HOLD" };
    let mut bl: Vec<String> = Vec::new();
    if ca { bl.push("p0_critical_delta_fuse_triggered".into()); }
    Ok(json!({"schema":"PGGArchonUltimateEvolutionFormulaReport/v1","status":st,"score":r3(sc),"raw_score":r3(raw),"omega_a":o,"theta_stable":t,"evm_full":e,"sigma_delta_all":d,"alpha_ack":r3(al),"beta_bg":r3(be),"tao_multipliers":{"A":r3(ta),"B":r3(tb),"tdhlgwb":r3(tt)},"critical_fuse":{"active":ca},"blockers":bl,"side_effects":"read_only_report"}).to_string())
}

#[pymodule]
fn hermes_pgg_ultimate_formula(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__NATIVE__", true)?; m.add("__VERSION__", "0.1.0")?;
    m.add_function(wrap_pyfunction!(compute_evm_full, m)?)?;
    m.add_function(wrap_pyfunction!(compute_sigma_delta, m)?)?;
    m.add_function(wrap_pyfunction!(compute_omega_a, m)?)?;
    m.add_function(wrap_pyfunction!(compute_theta_stable, m)?)?;
    m.add_function(wrap_pyfunction!(build_ultimate_evolution_formula_report, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn j(s: &str) -> Value { serde_json::from_str(s).unwrap() }
    #[test] fn evm_def() { assert!(j(&compute_evm_full("{}").unwrap())["score"].as_f64().unwrap() > 0.0); }
    #[test] fn evm_100() { let r=compute_evm_full(r#"{"task_success":100,"correctness":100,"closure":100,"reasoning_stability":100,"tool_use":100,"long_context_state":100,"self_repair":100}"#).unwrap(); assert!((j(&r)["score"].as_f64().unwrap()-100.0).abs()<0.1); }
    #[test] fn delta_empty() { let r=compute_sigma_delta("{}").unwrap(); assert!(!j(&r)["critical_active"].as_bool().unwrap()); }
    #[test] fn delta_crit() { let r=compute_sigma_delta(r#"{"critical":true}"#).unwrap(); assert!(j(&r)["critical_active"].as_bool().unwrap()); }
    #[test] fn omega_def() { assert!((j(&compute_omega_a("null","null","null").unwrap())["value"].as_f64().unwrap()-1.0).abs()<0.001); }
    #[test] fn theta_def() { assert_eq!(j(&compute_theta_stable("null","null").unwrap())["source"],"six_dimensional_theta_stable"); }
    #[test] fn theta_dir() { assert_eq!(j(&compute_theta_stable("null","1.5").unwrap())["source"],"direct_theta_value"); }
    #[test] fn rpt_def() { let r=build_ultimate_evolution_formula_report("null","null","null","null","null","null","null","null","null","null",1.0).unwrap(); assert_eq!(j(&r)["schema"],"PGGArchonUltimateEvolutionFormulaReport/v1"); }
    #[test] fn rpt_crit() { let r=build_ultimate_evolution_formula_report("null",r#"{"critical":true}"#,"null","null","null","null","null","null","null","null",1.0).unwrap(); assert_eq!(j(&r)["status"],"BLOCKED"); }
    #[test] fn rpt_pass() { let e=r#"{"task_success":100,"correctness":100,"closure":100,"reasoning_stability":100,"tool_use":100,"long_context_state":100,"self_repair":100}"#; let r=build_ultimate_evolution_formula_report(e,"null","null","null","null","null","null","null","null","null",1.0).unwrap(); assert_eq!(j(&r)["status"],"PASS"); }
}