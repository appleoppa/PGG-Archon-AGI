use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict};
type PyObject = Py<PyAny>;
use std::collections::HashSet;
use std::fs;
use std::path::Path;
use walkdir::WalkDir;

// ─── Constants ───

const SKIP_DIRS: &[&str] = &[
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".tox", "dist", "build", ".mypy_cache", ".pytest_cache",
    "target",
];

const SIMULATION_KEYWORDS: &[&str] = &["mock", "simulation", "dry_run"];

// ─── Types ───

#[derive(Clone, Debug, serde::Serialize)]
struct Finding {
    file: String,
    lines: usize,
    bytes: usize,
    notes: Vec<String>,
}

// ─── Main function ───

#[pyfunction]
#[pyo3(signature = (root=".".to_string(), max_files=30))]
fn scan_code_genesis(py: Python<'_>, root: String, max_files: i32) -> PyResult<PyObject> {
    let d = PyDict::new(py);

    // Resolve root path
    let root_path = Path::new(&root);
    let scanned_root = root_path
        .canonicalize()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| root.clone());

    // Validate inputs
    if max_files <= 0 {
        d.set_item("status", "BLOCKED")?;
        d.set_item("py_count", 0)?;
        d.set_item("findings", vec![] as Vec<PyObject>)?;
        d.set_item("skipped_dirs", vec![] as Vec<String>)?;
        d.set_item("scanned_root", &scanned_root)?;
        d.set_item(
            "warnings",
            vec!["max_files must be positive"],
        )?;
        return Ok(d.into());
    }

    if !root_path.exists() {
        d.set_item("status", "BLOCKED")?;
        d.set_item("py_count", 0)?;
        d.set_item("findings", vec![] as Vec<PyObject>)?;
        d.set_item("skipped_dirs", vec![] as Vec<String>)?;
        d.set_item("scanned_root", &scanned_root)?;
        d.set_item(
            "warnings",
            vec![format!("root not found: {}", root)],
        )?;
        return Ok(d.into());
    }

    // Build skip set for O(1) lookups
    let skip_set: HashSet<&str> = SKIP_DIRS.iter().copied().collect();

    // Scan
    let mut py_count: usize = 0;
    let mut findings: Vec<Finding> = Vec::new();
    let mut skipped_dirs: Vec<String> = Vec::new();
    let mut warnings: Vec<String> = Vec::new();
    let mut reached_limit = false;

    for entry in WalkDir::new(&root_path)
        .into_iter()
        .filter_entry(|e| {
            if e.file_type().is_dir() {
                let name = e.file_name().to_string_lossy();
                if skip_set.contains(name.as_ref()) {
                    skipped_dirs.push(e.path().to_string_lossy().to_string());
                    return false;
                }
            }
            true
        })
    {
        let entry = match entry {
            Ok(e) => e,
            Err(_) => continue,
        };

        if !entry.file_type().is_file() {
            continue;
        }

        let path = entry.path();
        if path.extension().map(|e| e != "py").unwrap_or(true) {
            continue;
        }

        if py_count >= max_files as usize {
            reached_limit = true;
            break;
        }

        py_count += 1;

        // Read file content
        let content = match fs::read_to_string(path) {
            Ok(c) => c,
            Err(e) => {
                findings.push(Finding {
                    file: path.to_string_lossy().to_string(),
                    lines: 0,
                    bytes: 0,
                    notes: vec![format!("read_error: {}", e)],
                });
                continue;
            }
        };

        let lines = content.lines().count();
        let bytes = content.len();

        let mut notes: Vec<String> = Vec::new();
        if lines > 500 {
            notes.push("large_file".to_string());
        }
        if content.contains("eval(") || content.contains("exec(") {
            notes.push("dynamic_exec_watch".to_string());
        }
        let lower = content.to_lowercase();
        for kw in SIMULATION_KEYWORDS {
            if lower.contains(kw) {
                notes.push("simulation_marker_watch".to_string());
                break;
            }
        }

        findings.push(Finding {
            file: path.to_string_lossy().to_string(),
            lines,
            bytes,
            notes,
        });
    }

    // Determine status
    let status = if py_count == 0 {
        warnings.push("no python files found".to_string());
        "BLOCKED"
    } else if reached_limit {
        warnings.push(format!("max_files limit reached: {}", max_files));
        "WATCH"
    } else {
        "PASS"
    };

    // Build output dict
    let findings_py: Vec<PyObject> = findings
        .iter()
        .filter_map(|f| {
            let fd = PyDict::new(py);
            fd.set_item("file", &f.file).ok()?;
            fd.set_item("lines", f.lines as i64).ok()?;
            fd.set_item("bytes", f.bytes as i64).ok()?;
            fd.set_item("notes", f.notes.clone()).ok()?;
            Some(fd.into())
        })
        .collect();

    d.set_item("status", status)?;
    d.set_item("py_count", py_count as i64)?;
    d.set_item("findings", findings_py)?;
    d.set_item("skipped_dirs", skipped_dirs)?;
    d.set_item("scanned_root", &scanned_root)?;
    d.set_item("warnings", warnings)?;

    Ok(d.into())
}

// ─── Tests ───

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs::{self, File};
    use std::io::Write;

    fn setup_test_dir(name: &str) -> (String, Vec<String>) {
        let dir = format!("/tmp/pgg_test_codegenesis_{}", name);
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        (dir, vec![])
    }

    fn write_py(path: &str, content: &str) {
        let mut f = File::create(path).unwrap();
        write!(f, "{}", content).unwrap();
    }

    #[test]
    fn test_scan_empty_dir() {
        let (dir, _) = setup_test_dir("empty");
        let result = scan_dir_inner(&dir, 30);
        assert_eq!(result.status, "BLOCKED");
        assert_eq!(result.py_count, 0);
        assert!(result.warnings.contains(&"no python files found".to_string()));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_scan_single_py() {
        let (dir, _) = setup_test_dir("single");
        write_py(&format!("{}/hello.py", dir), "print('hello')\n");
        let result = scan_dir_inner(&dir, 30);
        assert_eq!(result.status, "PASS");
        assert_eq!(result.py_count, 1);
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_scan_skip_dirs() {
        let (dir, _) = setup_test_dir("skip");
        fs::create_dir_all(format!("{}/.venv", dir)).unwrap();
        write_py(&format!("{}/.venv/skip_me.py", dir), "x=1\n");
        write_py(&format!("{}/keep.py", dir), "y=2\n");
        let result = scan_dir_inner(&dir, 30);
        assert_eq!(result.py_count, 1);
        assert_eq!(result.findings[0].file.contains("keep.py"), true);
        assert!(result.skipped_dirs.iter().any(|d| d.contains(".venv")));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_scan_max_files() {
        let (dir, _) = setup_test_dir("maxfiles");
        for i in 0..5 {
            write_py(&format!("{}/a{}.py", dir, i), "x=1\n");
        }
        let result = scan_dir_inner(&dir, 3);
        assert_eq!(result.py_count, 3);
        assert_eq!(result.status, "WATCH");
        assert!(result.warnings[0].contains("max_files"));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_scan_nonexistent_root() {
        let result = scan_dir_inner("/tmp/does_not_exist_xyz", 30);
        assert_eq!(result.status, "BLOCKED");
    }

    #[test]
    fn test_scan_negative_max_files() {
        let result = scan_dir_inner("/tmp", 0);
        assert_eq!(result.status, "BLOCKED");
        assert_eq!(result.py_count, 0);
    }

    #[test]
    fn test_scan_large_file_detection() {
        let (dir, _) = setup_test_dir("large");
        let mut content = String::with_capacity(600);
        for _ in 0..600 {
            content.push_str("x = 1\n");
        }
        write_py(&format!("{}/big.py", dir), &content);
        let result = scan_dir_inner(&dir, 30);
        assert_eq!(result.py_count, 1);
        assert!(result.findings[0].notes.contains(&"large_file".to_string()));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_scan_eval_detection() {
        let (dir, _) = setup_test_dir("evaltest");
        write_py(&format!("{}/danger.py", dir), "eval('1+1')\n");
        let result = scan_dir_inner(&dir, 30);
        assert_eq!(result.py_count, 1);
        assert!(result.findings[0].notes.contains(&"dynamic_exec_watch".to_string()));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_scan_simulation_detection() {
        let (dir, _) = setup_test_dir("sim");
        write_py(&format!("{}/sim.py", dir), "def mock_response(): return None\n");
        let result = scan_dir_inner(&dir, 30);
        assert_eq!(result.py_count, 1);
        assert!(result.findings[0].notes.contains(&"simulation_marker_watch".to_string()));
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_scan_only_py_files() {
        let (dir, _) = setup_test_dir("onlypy");
        write_py(&format!("{}/a.py", dir), "x=1\n");
        write_py(&format!("{}/b.txt", dir), "not python\n");
        write_py(&format!("{}/c.md", dir), "# doc\n");
        let result = scan_dir_inner(&dir, 30);
        assert_eq!(result.py_count, 1);
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_scan_multiple_files() {
        let (dir, _) = setup_test_dir("multi");
        for i in 0..10 {
            write_py(&format!("{}/file_{}.py", dir, i), "x=1\n");
        }
        let result = scan_dir_inner(&dir, 30);
        assert_eq!(result.py_count, 10);
        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn test_full_pgg_agent_dir() {
        // Scan the real agent/ dir but limit to something reasonable
        let agent_dir = "/Users/appleoppa/.hermes/hermes-agent/agent";
        let result = scan_dir_inner(agent_dir, 30);
        assert_eq!(result.status, "WATCH"); // will hit max_files limit
        assert!(result.py_count >= 20); // at least 20 pgg_archon_* files
        assert!(result.warnings[0].contains("max_files"));
    }

    // ─── Helper: Rust-only scanner (no Python) ───

    struct ScanResult {
        status: String,
        py_count: usize,
        findings: Vec<Finding>,
        skipped_dirs: Vec<String>,
        warnings: Vec<String>,
    }

    fn scan_dir_inner(root: &str, max_files: i32) -> ScanResult {
        let root_path = Path::new(root);

        if max_files <= 0 {
            return ScanResult {
                status: "BLOCKED".into(),
                py_count: 0,
                findings: vec![],
                skipped_dirs: vec![],
                warnings: vec!["max_files must be positive".into()],
            };
        }

        if !root_path.exists() {
            return ScanResult {
                status: "BLOCKED".into(),
                py_count: 0,
                findings: vec![],
                skipped_dirs: vec![],
                warnings: vec![format!("root not found: {}", root)],
            };
        }

        let skip_set: HashSet<&str> = SKIP_DIRS.iter().copied().collect();
        let mut py_count: usize = 0;
        let mut findings: Vec<Finding> = Vec::new();
        let mut skipped_dirs: Vec<String> = Vec::new();
        let mut warnings: Vec<String> = Vec::new();
        let mut reached_limit = false;

        for entry in WalkDir::new(&root_path)
            .into_iter()
            .filter_entry(|e| {
                if e.file_type().is_dir() {
                    let name = e.file_name().to_string_lossy();
                    if skip_set.contains(name.as_ref()) {
                        skipped_dirs.push(e.path().to_string_lossy().to_string());
                        return false;
                    }
                }
                true
            })
        {
            let entry = match entry {
                Ok(e) => e,
                Err(_) => continue,
            };

            if !entry.file_type().is_file() {
                continue;
            }

            let path = entry.path();
            if path.extension().map(|e| e != "py").unwrap_or(true) {
                continue;
            }

            if py_count >= max_files as usize {
                reached_limit = true;
                break;
            }

            py_count += 1;

            let content = match fs::read_to_string(path) {
                Ok(c) => c,
                Err(e) => {
                    findings.push(Finding {
                        file: path.to_string_lossy().to_string(),
                        lines: 0,
                        bytes: 0,
                        notes: vec![format!("read_error: {}", e)],
                    });
                    continue;
                }
            };

            let lines = content.lines().count();
            let bytes = content.len();
            let mut notes: Vec<String> = Vec::new();

            if lines > 500 {
                notes.push("large_file".to_string());
            }
            if content.contains("eval(") || content.contains("exec(") {
                notes.push("dynamic_exec_watch".to_string());
            }
            let lower = content.to_lowercase();
            for kw in SIMULATION_KEYWORDS {
                if lower.contains(kw) {
                    notes.push("simulation_marker_watch".to_string());
                    break;
                }
            }

            findings.push(Finding {
                file: path.to_string_lossy().to_string(),
                lines,
                bytes,
                notes,
            });
        }

        let status = if py_count == 0 {
            warnings.push("no python files found".to_string());
            "BLOCKED"
        } else if reached_limit {
            warnings.push(format!("max_files limit reached: {}", max_files));
            "WATCH"
        } else {
            "PASS"
        };

        ScanResult {
            status: status.into(),
            py_count,
            findings,
            skipped_dirs,
            warnings,
        }
    }
}

// ─── Module registration ───

#[pymodule]
fn hermes_pgg_codegenesis_scanner(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(scan_code_genesis, m)?)?;
    Ok(())
}