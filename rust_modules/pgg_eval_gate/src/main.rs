use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::env;
use std::fs::File;
use std::io::{self, BufRead, BufReader, Read};
use std::process;

#[derive(Debug, Deserialize)]
struct GoldenItem {
    #[allow(dead_code)]
    id: Option<String>,
    #[allow(dead_code)]
    question: String,
    expected: String,
    #[allow(dead_code)]
    category: String,
    #[allow(dead_code)]
    source: String,
}

#[derive(Debug, Serialize)]
struct EvalReport {
    schema: &'static str,
    total: usize,
    passed: usize,
    failed: usize,
    accuracy: f64,
    threshold: f64,
    verdict: &'static str,
}

fn usage_and_exit() -> ! {
    eprintln!("Usage: pgg_eval_gate --golden <path> --threshold <0.0-1.0> < model_answer.txt");
    process::exit(2);
}

fn parse_args() -> (String, f64) {
    let mut golden: Option<String> = None;
    let mut threshold = 0.85_f64;
    let mut args = env::args().skip(1);

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--golden" => golden = args.next(),
            "--threshold" => {
                threshold = args
                    .next()
                    .and_then(|s| s.parse::<f64>().ok())
                    .unwrap_or_else(|| usage_and_exit());
            }
            "-h" | "--help" => usage_and_exit(),
            _ => usage_and_exit(),
        }
    }

    if !(0.0..=1.0).contains(&threshold) {
        usage_and_exit();
    }
    (golden.unwrap_or_else(|| usage_and_exit()), threshold)
}

fn load_golden(path: &str) -> Result<Vec<GoldenItem>, String> {
    let file = File::open(path).map_err(|e| format!("open golden failed: {e}"))?;
    let reader = BufReader::new(file);
    let mut items = Vec::new();

    for (idx, line) in reader.lines().enumerate() {
        let line = line.map_err(|e| format!("read line {} failed: {e}", idx + 1))?;
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let item: GoldenItem = serde_json::from_str(trimmed)
            .map_err(|e| format!("parse jsonl line {} failed: {e}", idx + 1))?;
        items.push(item);
    }
    Ok(items)
}

fn normalize(text: &str) -> String {
    text.chars()
        .filter(|c| {
            !c.is_whitespace()
                && !matches!(
                    c,
                    '，' | '。'
                        | '；'
                        | '：'
                        | '、'
                        | '（'
                        | '）'
                        | '('
                        | ')'
                        | ','
                        | '.'
                        | ';'
                        | ':'
                        | '"'
                        | '\''
                        | '“'
                        | '”'
                        | '《'
                        | '》'
                        | '['
                        | ']'
                )
        })
        .collect::<String>()
        .to_lowercase()
}

fn is_cjk(c: char) -> bool {
    ('\u{4e00}'..='\u{9fff}').contains(&c)
}

fn keyword_set(text: &str) -> HashSet<String> {
    let mut set = HashSet::new();
    let normalized = normalize(text);
    let chars: Vec<char> = normalized.chars().collect();

    // Chinese legal answers are often sentence-like. Character bigrams/trigrams give a
    // deterministic, dependency-free overlap signal without LLM calls.
    for n in [2_usize, 3_usize] {
        if chars.len() >= n {
            for win in chars.windows(n) {
                if win.iter().any(|c| is_cjk(*c)) {
                    set.insert(win.iter().collect());
                }
            }
        }
    }

    for token in text.split(|c: char| !c.is_alphanumeric() && !is_cjk(c)) {
        let token = normalize(token);
        if token.chars().count() >= 2 {
            set.insert(token);
        }
    }
    set
}

fn item_passes(answer: &str, expected: &str) -> bool {
    let answer_norm = normalize(answer);
    let expected_norm = normalize(expected);
    if answer_norm.is_empty() || expected_norm.is_empty() {
        return false;
    }
    if answer_norm.contains(&expected_norm) || expected_norm.contains(&answer_norm) {
        return true;
    }

    let expected_keywords = keyword_set(expected);
    if expected_keywords.is_empty() {
        return false;
    }
    let answer_keywords = keyword_set(answer);
    let hits = expected_keywords
        .iter()
        .filter(|kw| answer_keywords.contains(*kw) || answer_norm.contains(kw.as_str()))
        .count();
    let overlap = hits as f64 / expected_keywords.len() as f64;

    // Require substantial lexical agreement. This is intentionally conservative and local-only.
    overlap >= 0.60 || (hits >= 8 && overlap >= 0.45)
}

fn round2(v: f64) -> f64 {
    (v * 100.0).round() / 100.0
}

fn main() {
    let (golden_path, threshold) = parse_args();
    let golden = match load_golden(&golden_path) {
        Ok(items) => items,
        Err(err) => {
            eprintln!("{err}");
            process::exit(1);
        }
    };

    let mut model_answer = String::new();
    io::stdin()
        .read_to_string(&mut model_answer)
        .unwrap_or_default();

    let total = golden.len();
    let passed = golden
        .iter()
        .filter(|item| item_passes(&model_answer, &item.expected))
        .count();
    let failed = total.saturating_sub(passed);
    let accuracy_raw = if total == 0 {
        0.0
    } else {
        passed as f64 / total as f64
    };
    let accuracy = round2(accuracy_raw);
    let verdict = if accuracy_raw >= threshold {
        "PASS"
    } else {
        "FAIL"
    };

    let report = EvalReport {
        schema: "pgg-eval-gate/v1",
        total,
        passed,
        failed,
        accuracy,
        threshold,
        verdict,
    };

    println!("{}", serde_json::to_string(&report).unwrap());
}
