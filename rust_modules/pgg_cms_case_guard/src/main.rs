use serde::Serialize;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

const DEFAULT_CASE_ROOT: &str = "/Users/appleoppa/.hermes/workspace/苹果中枢办案库";

#[derive(Serialize)]
struct NextReport {
    schema: &'static str,
    status: &'static str,
    next_sequence: u64,
    existing_max_sequence: u64,
    case_root: String,
    generated_at_unix: u64,
}

#[derive(Serialize)]
struct ValidateReport {
    schema: &'static str,
    status: &'static str,
    errors: Vec<String>,
    warnings: Vec<String>,
    path: String,
    case_type: String,
    case_seq: Option<u64>,
    case_code: Option<String>,
    next_sequence: u64,
    existing_max_sequence: u64,
}

fn now_unix() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

fn home_case_root() -> PathBuf {
    env::var("CMS_CASE_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from(DEFAULT_CASE_ROOT))
}

fn parse_case_dir_name(name: &str) -> Option<(u64, String)> {
    let first = name.split('-').next()?;
    if first.len() != 4 || !first.chars().all(|c| c.is_ascii_digit()) {
        return None;
    }
    let seq = first.parse::<u64>().ok()?;
    let after = name.strip_prefix(first)?.strip_prefix('-')?;
    let code_part = after.split('-').next().unwrap_or("");
    let code = code_part
        .strip_prefix("PGG")
        .unwrap_or(code_part)
        .to_string();
    Some((seq, code))
}

fn scan_max_sequence(root: &Path) -> u64 {
    let mut max_seq = 0;
    if let Ok(entries) = fs::read_dir(root) {
        for entry in entries.flatten() {
            if let Ok(ft) = entry.file_type() {
                if !ft.is_dir() {
                    continue;
                }
            }
            let name = entry.file_name().to_string_lossy().to_string();
            if let Some((seq, _)) = parse_case_dir_name(&name) {
                max_seq = max_seq.max(seq);
            }
        }
    }
    max_seq
}

fn find_case_identity(path: &Path) -> (Option<u64>, Option<String>) {
    for comp in path.components() {
        let s = comp.as_os_str().to_string_lossy();
        if let Some((seq, code)) = parse_case_dir_name(&s) {
            return (Some(seq), Some(code));
        }
    }
    // Also support nested canonical case names such as PGG-XS-20260608-0007（...）.
    for comp in path.components() {
        let s = comp.as_os_str().to_string_lossy();
        let parts: Vec<&str> = s.split('-').collect();
        if parts.len() >= 4 && parts[0] == "PGG" {
            let code = parts[1].to_string();
            let digits: String = parts[3]
                .chars()
                .take_while(|c| c.is_ascii_digit())
                .collect();
            if let Ok(seq) = digits.parse::<u64>() {
                return (Some(seq), Some(code));
            }
        }
    }
    (None, None)
}

fn print_json<T: Serialize>(value: &T) -> i32 {
    match serde_json::to_string_pretty(value) {
        Ok(s) => {
            println!("{}", s);
            0
        }
        Err(e) => {
            eprintln!("cms_case_guard: JSON serialization error: {}", e);
            2
        }
    }
}

fn usage() -> i32 {
    eprintln!("Usage: cms_case_guard --next [--case-root <path>] | --validate [<path>] [--case-type <type>] [--case-root <path>]");
    2
}

fn main() -> std::process::ExitCode {
    let mut args = env::args().skip(1);
    let mut mode_next = false;
    let mut validate_path: Option<PathBuf> = None;
    let mut case_type: Option<String> = None;
    let mut case_root = home_case_root();

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--next" => mode_next = true,
            "--validate" => {
                if let Some(v) = args.next() {
                    if v == "--case-type" {
                        let Some(t) = args.next() else {
                            return std::process::ExitCode::from(usage() as u8);
                        };
                        case_type = Some(t);
                    } else if v == "--case-root" {
                        let Some(root) = args.next() else {
                            return std::process::ExitCode::from(usage() as u8);
                        };
                        case_root = PathBuf::from(root);
                    } else {
                        validate_path = Some(PathBuf::from(v));
                    }
                } else {
                    validate_path = Some(case_root.clone());
                }
            }
            "--case-type" => {
                let Some(v) = args.next() else {
                    return std::process::ExitCode::from(usage() as u8);
                };
                case_type = Some(v);
            }
            "--case-root" => {
                let Some(v) = args.next() else {
                    return std::process::ExitCode::from(usage() as u8);
                };
                case_root = PathBuf::from(v);
            }
            "--help" | "-h" => return std::process::ExitCode::from(usage() as u8),
            other => {
                eprintln!("cms_case_guard: unknown argument: {}", other);
                return std::process::ExitCode::from(2);
            }
        }
    }

    let max_seq = scan_max_sequence(&case_root);
    let next_sequence = max_seq + 1;

    if mode_next && validate_path.is_none() {
        let report = NextReport {
            schema: "cms-case-guard/v1",
            status: "PASS",
            next_sequence,
            existing_max_sequence: max_seq,
            case_root: case_root.to_string_lossy().to_string(),
            generated_at_unix: now_unix(),
        };
        return std::process::ExitCode::from(print_json(&report) as u8);
    }

    if let Some(path) = validate_path {
        let (case_seq, case_code) = find_case_identity(&path);
        let ct =
            case_type.unwrap_or_else(|| case_code.clone().unwrap_or_else(|| "UNKNOWN".to_string()));
        let mut errors = Vec::new();
        let mut warnings = Vec::new();
        if !path.exists() {
            errors.push("PATH_NOT_FOUND".to_string());
        }
        if !path.is_dir() {
            errors.push("PATH_NOT_DIRECTORY".to_string());
        }
        if path != case_root {
            if case_seq.is_none() {
                errors.push("CASE_SEQUENCE_NOT_FOUND".to_string());
            }
            if case_code.is_none() {
                warnings.push("CASE_CODE_NOT_FOUND".to_string());
            } else if let Some(code) = &case_code {
                if code.to_uppercase() != ct.to_uppercase() {
                    errors.push(format!("CASE_TYPE_MISMATCH expected={} found={}", ct, code));
                }
            }
        }
        let status = if errors.is_empty() { "PASS" } else { "BLOCKED" };
        let report = ValidateReport {
            schema: "cms-case-guard/v1",
            status,
            errors,
            warnings,
            path: path.to_string_lossy().to_string(),
            case_type: ct,
            case_seq,
            case_code,
            next_sequence,
            existing_max_sequence: max_seq,
        };
        let code = print_json(&report);
        return std::process::ExitCode::from(if status == "PASS" { code as u8 } else { 1 });
    }

    std::process::ExitCode::from(usage() as u8)
}
