use std::env;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug)]
struct Report {
    root: PathBuf,
    preferred: PathBuf,
    legacy: PathBuf,
    preferred_python: Option<PathBuf>,
    action: String,
    ok: bool,
}

fn home_dir() -> PathBuf {
    env::var_os("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("/Users/appleoppa"))
}

fn default_root() -> PathBuf {
    env::var_os("HERMES_AGENT_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|| home_dir().join(".hermes/hermes-agent"))
}

fn is_executable_file(path: &Path) -> bool {
    path.is_file()
}

fn find_python(preferred: &Path) -> Option<PathBuf> {
    for name in ["python3", "python"] {
        let p = preferred.join("bin").join(name);
        if is_executable_file(&p) {
            return Some(p);
        }
    }
    None
}

#[cfg(unix)]
fn symlink_dir(src: &Path, dst: &Path) -> io::Result<()> {
    std::os::unix::fs::symlink(src, dst)
}

#[cfg(not(unix))]
fn symlink_dir(src: &Path, dst: &Path) -> io::Result<()> {
    std::os::windows::fs::symlink_dir(src, dst)
}

fn ensure(root: &Path, fix: bool) -> Result<Report, String> {
    let preferred = root.join(".venv");
    let legacy = root.join("venv");
    let preferred_python = find_python(&preferred);
    if preferred_python.is_none() {
        return Ok(Report {
            root: root.to_path_buf(),
            preferred,
            legacy,
            preferred_python,
            action: "preferred_missing_or_no_python".to_string(),
            ok: false,
        });
    }

    let action: String;
    let meta = fs::symlink_metadata(&legacy);
    match meta {
        Ok(m) if m.file_type().is_symlink() => {
            let target = fs::read_link(&legacy).map_err(|e| format!("readlink failed: {e}"))?;
            if target == PathBuf::from(".venv") || target == preferred {
                action = "legacy_symlink_ok".to_string();
            } else if fix {
                fs::remove_file(&legacy)
                    .map_err(|e| format!("remove bad legacy symlink failed: {e}"))?;
                symlink_dir(Path::new(".venv"), &legacy)
                    .map_err(|e| format!("create legacy symlink failed: {e}"))?;
                action = format!("repaired_bad_symlink_from_{}", target.display());
            } else {
                action = format!("bad_legacy_symlink_to_{}", target.display());
                return Ok(Report {
                    root: root.to_path_buf(),
                    preferred,
                    legacy,
                    preferred_python,
                    action,
                    ok: false,
                });
            }
        }
        Ok(m) if m.file_type().is_dir() => {
            action = "legacy_is_real_directory_leave_untouched".to_string();
            return Ok(Report {
                root: root.to_path_buf(),
                preferred,
                legacy,
                preferred_python,
                action,
                ok: false,
            });
        }
        Ok(_) => {
            action = "legacy_exists_non_directory_leave_untouched".to_string();
            return Ok(Report {
                root: root.to_path_buf(),
                preferred,
                legacy,
                preferred_python,
                action,
                ok: false,
            });
        }
        Err(e) if e.kind() == io::ErrorKind::NotFound => {
            if fix {
                symlink_dir(Path::new(".venv"), &legacy)
                    .map_err(|e| format!("create legacy symlink failed: {e}"))?;
                action = "created_legacy_symlink".to_string();
            } else {
                action = "legacy_missing".to_string();
                return Ok(Report {
                    root: root.to_path_buf(),
                    preferred,
                    legacy,
                    preferred_python,
                    action,
                    ok: false,
                });
            }
        }
        Err(e) => return Err(format!("stat legacy path failed: {e}")),
    }

    Ok(Report {
        root: root.to_path_buf(),
        preferred,
        legacy,
        preferred_python,
        action,
        ok: true,
    })
}

fn verify_import(py: &Path) -> bool {
    let code = "import sys, certifi; print(sys.executable); print(certifi.where())";
    Command::new(py)
        .args(["-c", code])
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

fn json_escape(s: &str) -> String {
    s.replace('\\', "\\\\").replace('"', "\\\"")
}

fn print_report(report: &Report, json: bool, import_ok: Option<bool>) {
    if json {
        println!(
            "{{\"ok\":{},\"action\":\"{}\",\"root\":\"{}\",\"preferred\":\"{}\",\"legacy\":\"{}\",\"preferred_python\":{},\"import_ok\":{}}}",
            report.ok,
            json_escape(&report.action),
            json_escape(&report.root.display().to_string()),
            json_escape(&report.preferred.display().to_string()),
            json_escape(&report.legacy.display().to_string()),
            report.preferred_python.as_ref().map(|p| format!("\"{}\"", json_escape(&p.display().to_string()))).unwrap_or_else(|| "null".to_string()),
            import_ok.map(|v| v.to_string()).unwrap_or_else(|| "null".to_string())
        );
    } else {
        println!("ok={}", report.ok);
        println!("action={}", report.action);
        println!("root={}", report.root.display());
        println!("preferred={}", report.preferred.display());
        println!("legacy={}", report.legacy.display());
        if let Some(py) = &report.preferred_python {
            println!("preferred_python={}", py.display());
        }
        if let Some(v) = import_ok {
            println!("import_ok={v}");
        }
    }
}

fn main() {
    let mut fix = true;
    let mut json = false;
    let mut do_import = false;
    let mut root = default_root();
    let mut args = env::args().skip(1).peekable();
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--check" => fix = false,
            "--fix" => fix = true,
            "--json" => json = true,
            "--verify-import" => do_import = true,
            "--root" => {
                if let Some(v) = args.next() {
                    root = PathBuf::from(v);
                }
            }
            "--help" | "-h" => {
                println!("pgg_hermes_venv_guard [--fix|--check] [--json] [--verify-import] [--root PATH]");
                return;
            }
            _ => {
                eprintln!("unknown arg: {arg}");
                std::process::exit(2);
            }
        }
    }

    match ensure(&root, fix) {
        Ok(report) => {
            let import_ok = if do_import && report.ok {
                report.preferred_python.as_ref().map(|py| verify_import(py))
            } else {
                None
            };
            print_report(&report, json, import_ok);
            if !report.ok || import_ok == Some(false) {
                std::process::exit(1);
            }
        }
        Err(e) => {
            if json {
                println!("{{\"ok\":false,\"error\":\"{}\"}}", json_escape(&e));
            } else {
                eprintln!("ERROR: {e}");
            }
            std::process::exit(1);
        }
    }
}
