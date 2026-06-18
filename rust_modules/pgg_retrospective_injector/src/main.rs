use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::env;
use std::fs;
use std::io::{self, Read};
use std::path::PathBuf;

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq)]
struct Lesson {
    trigger: String,
    right_action: String,
    injection_prompt: String,
    confidence: f64,
    conflict_status: String,
}

fn home_dir() -> PathBuf {
    env::var("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("/Users/appleoppa"))
}

fn default_lessons_path() -> PathBuf {
    home_dir()
        .join(".hermes/workspace/pgg-archon-governance/feishu-doc-a8e9-20260617/retrospective_lessons.jsonl")
}

fn load_lessons() -> Vec<Lesson> {
    let path = default_lessons_path();
    let text = match fs::read_to_string(&path) {
        Ok(t) => t,
        Err(_) => return Vec::new(),
    };
    text.lines()
        .filter_map(|line| serde_json::from_str::<Lesson>(line).ok())
        .collect()
}

fn score_match(query: &str, lesson: &Lesson) -> bool {
    if lesson.conflict_status != "active" || lesson.confidence < 0.6 {
        return false;
    }
    let q = query.to_lowercase();
    let t = lesson.trigger.to_lowercase();
    if q.is_empty() {
        return true;
    }
    q.split_whitespace()
        .any(|tok| !tok.is_empty() && t.contains(tok))
        || t.split_whitespace()
            .any(|tok| !tok.is_empty() && q.contains(tok))
        || q.contains(&t)
}

fn select_lessons(query: &str, lessons: &[Lesson]) -> Vec<Lesson> {
    let mut matched: Vec<Lesson> = lessons
        .iter()
        .cloned()
        .filter(|l| score_match(query, l))
        .collect();
    matched.sort_by(|a, b| {
        b.confidence
            .partial_cmp(&a.confidence)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    matched.truncate(3);
    matched
}

fn build_context(selected: &[Lesson]) -> String {
    if selected.is_empty() {
        return String::new();
    }
    let mut out = String::from(
        "【任务前复盘提示｜observe-first】\n\n这不是系统提示修改，也不是长期记忆写入；它只是任务前 checklist / 参考教训。\n\n",
    );
    for (idx, lesson) in selected.iter().enumerate() {
        out.push_str(&format!(
            "{}. [{} | conf={:.2}] {}\n   建议动作: {}\n",
            idx + 1,
            lesson.trigger,
            lesson.confidence,
            lesson.injection_prompt,
            lesson.right_action,
        ));
    }
    out.push_str("\n任务前动作：先核实来源、保存原文/证据、再推进执行。\n");
    out
}

fn collect_strings(v: &Value, parts: &mut Vec<String>) {
    match v {
        Value::String(s) if !s.trim().is_empty() => parts.push(s.clone()),
        Value::Array(arr) => {
            for item in arr {
                collect_strings(item, parts);
            }
        }
        Value::Object(map) => {
            for (k, item) in map {
                if k != "hook_event_name" {
                    collect_strings(item, parts);
                }
            }
        }
        _ => {}
    }
}

fn extract_query(payload: &Value) -> String {
    let mut parts = Vec::new();
    collect_strings(payload, &mut parts);
    parts.join(" ")
}

fn context_from_payload(payload: &Value, lessons: &[Lesson]) -> Option<String> {
    let is_first_turn = payload
        .get("extra")
        .and_then(|v| v.get("is_first_turn"))
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    if !is_first_turn {
        return None;
    }
    let query = extract_query(payload);
    let selected = select_lessons(&query, lessons);
    if selected.is_empty() {
        None
    } else {
        Some(build_context(&selected))
    }
}

fn emit_json(context: Option<String>) {
    let out = match context {
        Some(ctx) => json!({"context": ctx, "mode": "pre_llm_call_checklist", "selected": true}),
        None => json!({"selected": false}),
    };
    println!("{}", serde_json::to_string(&out).unwrap());
}

fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).ok();
    let payload: Value = if input.trim().is_empty() {
        json!({})
    } else {
        serde_json::from_str(&input).unwrap_or_else(|_| json!({}))
    };

    let lessons = load_lessons();
    let context = context_from_payload(&payload, &lessons);
    emit_json(context);
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_lessons() -> Vec<Lesson> {
        vec![
            Lesson {
                trigger: "飞书 文档 阅读".into(),
                right_action: "先保存原文和 meta，再对照本机证据".into(),
                injection_prompt: "飞书文档任务先保存原文/meta，并用本机读回证据对照。".into(),
                confidence: 0.91,
                conflict_status: "active".into(),
            },
            Lesson {
                trigger: "办案 金额".into(),
                right_action: "先闭合金额表".into(),
                injection_prompt: "金额类办案先闭合总额、已付、扣减、待付。".into(),
                confidence: 0.88,
                conflict_status: "active".into(),
            },
            Lesson {
                trigger: "PRD Quick-Spec 大改动 系统修改 多文件 生产链路".into(),
                right_action: "触发时先使用 PRD/Quick-Spec checklist".into(),
                injection_prompt: "PRD治理：中高风险/多文件/系统修改先写 PRD 或 Quick-Spec。"
                    .into(),
                confidence: 0.87,
                conflict_status: "active".into(),
            },
            Lesson {
                trigger: "低置信".into(),
                right_action: "不注入".into(),
                injection_prompt: "不应出现".into(),
                confidence: 0.59,
                conflict_status: "active".into(),
            },
            Lesson {
                trigger: "冲突".into(),
                right_action: "不注入".into(),
                injection_prompt: "不应出现冲突项".into(),
                confidence: 0.99,
                conflict_status: "pending".into(),
            },
        ]
    }

    #[test]
    fn selects_only_active_high_confidence_matching_lessons() {
        let selected = select_lessons("请阅读飞书文档并对照", &sample_lessons());
        assert_eq!(selected.len(), 1);
        assert_eq!(
            selected[0].injection_prompt,
            "飞书文档任务先保存原文/meta，并用本机读回证据对照。"
        );
    }

    #[test]
    fn context_is_bounded_checklist_not_system_prompt() {
        let selected = vec![sample_lessons()[0].clone()];
        let ctx = build_context(&selected);
        assert!(ctx.contains("任务前复盘提示"));
        assert!(ctx.contains("不是系统提示修改"));
        assert!(ctx.len() < 1200);
    }

    #[test]
    fn pre_llm_payload_injects_on_first_turn_only() {
        let payload = json!({"hook_event_name":"pre_llm_call", "extra":{"is_first_turn": true, "user_message":"PRD Quick-Spec 大改动 系统修改 多文件 生产链路"}});
        let ctx = context_from_payload(&payload, &sample_lessons()).expect("context");
        assert!(ctx.contains("PRD治理"));

        let payload2 = json!({"hook_event_name":"pre_llm_call", "extra":{"is_first_turn": false, "user_message":"PRD Quick-Spec 大改动 系统修改 多文件 生产链路"}});
        assert!(context_from_payload(&payload2, &sample_lessons()).is_none());
    }
}
