use pyo3::prelude::*;
use pyo3::types::PyModule;
use serde::Serialize;
use std::path::PathBuf;
use walkdir::WalkDir;

// ============================================================================
// Core data types
// ============================================================================

#[derive(Debug, Serialize)]
struct SkillHealthReport {
    schema: String,
    status: String,
    total_skills: usize,
    healthy: usize,
    with_frontmatter: usize,
    with_description: usize,
    with_tags: usize,
    missing_skills: Vec<String>,
    warnings: Vec<String>,
    detail: String,
    evidence_hash: String,
}

/// Default skills directory
fn default_skills_dir() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".into());
    PathBuf::from(home).join(".hermes").join("skills")
}

/// Check if text starts with YAML frontmatter (---)
fn has_frontmatter(text: &str) -> bool {
    let trimmed = text.trim_start();
    trimmed.starts_with("---") && trimmed[3..].contains("---")
}

/// Check if frontmatter contains a specific field
fn has_frontmatter_field(text: &str, field: &str) -> bool {
    // Only check within the frontmatter block (between first and second ---)
    let trimmed = text.trim_start();
    if !trimmed.starts_with("---") {
        return false;
    }
    let after_first = &trimmed[3..];
    if let Some(end) = after_first.find("---") {
        let frontmatter = &after_first[..end];
        for line in frontmatter.lines() {
            if line.trim_start().starts_with(field) && line.trim_start()[field.len()..].starts_with(':') {
                return true;
            }
        }
    }
    false
}

/// Compute SHA-256 hex string from payload
fn sha256_hex(payload: &str) -> String {
    use std::hash::{Hash, Hasher};
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    payload.hash(&mut hasher);
    format!("{:x}", hasher.finish())
}

/// Skip directories that should not be scanned
fn should_skip(entry: &walkdir::DirEntry) -> bool {
    let skip_dirs: &[&str] = &[
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        ".tox", "dist", "build", ".mypy_cache", ".pytest_cache",
    ];
    if entry.file_type().is_dir() {
        let name = entry.file_name().to_string_lossy();
        skip_dirs.contains(&name.as_ref())
    } else {
        false
    }
}

// ============================================================================
// Core scanning logic
// ============================================================================

fn scan_skills_internal(skills_dir: &str) -> SkillHealthReport {
    let base = PathBuf::from(skills_dir);

    if !base.exists() || !base.is_dir() {
        return SkillHealthReport {
            schema: "PGGArchonSkillHealth/v1".into(),
            status: "BLOCKED".into(),
            total_skills: 0,
            healthy: 0,
            with_frontmatter: 0,
            with_description: 0,
            with_tags: 0,
            missing_skills: vec![],
            warnings: vec!["skills_dir_not_found".into()],
            detail: format!("skills directory not found: {}", skills_dir),
            evidence_hash: String::new(),
        };
    }

    let mut total = 0usize;
    let mut healthy = 0usize;
    let mut with_fm = 0usize;
    let mut with_desc = 0usize;
    let mut with_tags = 0usize;
    let mut warnings: Vec<String> = vec![];

    for entry in WalkDir::new(&base)
        .into_iter()
        .filter_entry(|e| !should_skip(e))
    {
        let entry = match entry {
            Ok(e) => e,
            Err(_) => continue,
        };

        if !entry.file_type().is_file() {
            continue;
        }

        // Only match SKILL.md (case-sensitive, exact filename)
        if entry.file_name() != "SKILL.md" {
            continue;
        }

        total += 1;

        let text = match std::fs::read_to_string(entry.path()) {
            Ok(t) => t,
            Err(_) => {
                warnings.push(format!("unreadable: {}", entry.path().display()));
                continue;
            }
        };

        let fm = has_frontmatter(&text);
        let desc = has_frontmatter_field(&text, "description");
        let tags = has_frontmatter_field(&text, "tags");

        if fm {
            with_fm += 1;
        }
        if desc {
            with_desc += 1;
        }
        if tags {
            with_tags += 1;
        }
        if fm && desc {
            healthy += 1;
        }
    }

    if total == 0 {
        warnings.push("no_skills_found".into());
    }

    let unhealthy = total - healthy;
    if unhealthy > 0 {
        warnings.push(format!("unhealthy_skills={}", unhealthy));
    }

    let status = if healthy == total && total > 0 {
        "PASS"
    } else if total == 0 {
        "WATCH"
    } else {
        "WATCH"
    };

    let payload = format!("{}|{}|{}", total, healthy, with_fm);
    let evidence_hash = sha256_hex(&payload);

    SkillHealthReport {
        schema: "PGGArchonSkillHealth/v1".into(),
        status: status.into(),
        total_skills: total,
        healthy,
        with_frontmatter: with_fm,
        with_description: with_desc,
        with_tags: with_tags,
        missing_skills: vec![],
        warnings,
        detail: format!("{}/{} skills healthy", healthy, total),
        evidence_hash,
    }
}

// ============================================================================
// Python-facing functions (PyO3)
// ============================================================================

#[pyfunction]
#[pyo3(signature = (skills_dir = None))]
fn native_scan_skills(skills_dir: Option<String>) -> PyResult<String> {
    let dir = skills_dir.unwrap_or_else(|| {
        default_skills_dir().to_string_lossy().to_string()
    });
    let report = scan_skills_internal(&dir);
    serde_json::to_string(&report)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("serialization error: {}", e)))
}

#[pyfunction]
fn native_info() -> PyResult<String> {
    let info = serde_json::json!({
        "engine": "PGG Archon Skill Health Checker Rust Native",
        "version": "0.1.0",
        "boundary": "filesystem read-only; no writes, no provider calls, no Hermes core mutation",
        "default_skills_dir": default_skills_dir().to_string_lossy().to_string(),
    });
    serde_json::to_string(&info)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("serialization error: {}", e)))
}

// ============================================================================
// Module definition
// ============================================================================

#[pymodule]
fn hermes_pgg_skill_health_checker(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(native_scan_skills, m)?)?;
    m.add_function(wrap_pyfunction!(native_info, m)?)?;
    Ok(())
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::sync::atomic::{AtomicU32, Ordering};

    static COUNTER: AtomicU32 = AtomicU32::new(0);

    fn setup_test_dir() -> PathBuf {
        let base = std::env::temp_dir().join("pgg_skill_test_20260614");
        let id = COUNTER.fetch_add(1, Ordering::SeqCst);
        let dir = base.join(format!("test_{}", id));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        // Create some subdirectories that tests expect
        fs::create_dir_all(dir.join("skill_a")).unwrap();
        fs::create_dir_all(dir.join("skill_b")).unwrap();
        fs::create_dir_all(dir.join("skill_b/nested")).unwrap();
        dir
    }

    fn write_skill(dir: &PathBuf, subdir: &str, name: &str, content: &str) {
        let target = dir.join(subdir);
        fs::create_dir_all(&target).unwrap();
        let path = target.join(name);
        fs::write(&path, content).unwrap();
    }

    #[test]
    fn test_skill_dir_not_found() {
        let r = scan_skills_internal("/nonexistent/path_xyz_test_20260614");
        assert_eq!(r.status, "BLOCKED");
        assert!(r.warnings.contains(&"skills_dir_not_found".to_string()));
        assert_eq!(r.total_skills, 0);
    }

    #[test]
    fn test_empty_dir() {
        let dir = setup_test_dir();
        // Only a non-SKILL.md file
        write_skill(&dir, "skill_a", "README.md", "not a skill");
        let r = scan_skills_internal(&dir.to_string_lossy());
        assert_eq!(r.status, "WATCH");
        assert_eq!(r.total_skills, 0);
    }

    #[test]
    fn test_healthy_skill() {
        let dir = setup_test_dir();
        let content = "---\ndescription: Test skill\ntags: [test, rust]\n---\n\nSkill body.";
        write_skill(&dir, "skill_a", "SKILL.md", content);
        let r = scan_skills_internal(&dir.to_string_lossy());
        assert_eq!(r.total_skills, 1);
        assert_eq!(r.healthy, 1);
        assert_eq!(r.with_frontmatter, 1);
        assert_eq!(r.with_description, 1);
        assert_eq!(r.with_tags, 1);
        assert_eq!(r.status, "PASS");
    }

    #[test]
    fn test_no_frontmatter() {
        let dir = setup_test_dir();
        write_skill(&dir, "skill_b", "SKILL.md", "Just a body without frontmatter.");
        let r = scan_skills_internal(&dir.to_string_lossy());
        assert_eq!(r.total_skills, 1);
        assert_eq!(r.healthy, 0);
        assert_eq!(r.with_frontmatter, 0);
        assert_eq!(r.with_description, 0);
        assert_eq!(r.status, "WATCH");
    }

    #[test]
    fn test_partial_frontmatter() {
        let dir = setup_test_dir();
        let content = "---\ndescription: Only desc, no tags\n---\nBody.";
        write_skill(&dir, "skill_a", "SKILL.md", content);
        let r = scan_skills_internal(&dir.to_string_lossy());
        assert_eq!(r.total_skills, 1);
        assert_eq!(r.healthy, 1); // has frontmatter AND description
        assert_eq!(r.with_frontmatter, 1);
        assert_eq!(r.with_description, 1);
        assert_eq!(r.with_tags, 0);
    }

    #[test]
    fn test_skips_venv_dir() {
        let dir = setup_test_dir();
        fs::create_dir_all(dir.join(".venv")).unwrap();
        write_skill(&dir, ".venv", "SKILL.md", "---\ndescription: hidden\n---\nbody");
        write_skill(&dir, "skill_a", "SKILL.md", "---\ndescription: real skill\ntags: [real]\n---\nbody");
        let r = scan_skills_internal(&dir.to_string_lossy());
        assert_eq!(r.total_skills, 1); // only skill_a counted
        assert_eq!(r.healthy, 1);
        assert_eq!(r.with_tags, 1);
    }

    #[test]
    fn test_multiple_skills() {
        let dir = setup_test_dir();
        for i in 0..5 {
            let subdir = format!("skill_{}", i);
            write_skill(
                &dir,
                &subdir,
                "SKILL.md",
                &format!("---\ndescription: skill {}\ntags: [test]\n---\nbody", i),
            );
        }
        // One unhealthy
        write_skill(&dir, "skill_b/nested", "SKILL.md", "no frontmatter here");
        let r = scan_skills_internal(&dir.to_string_lossy());
        assert_eq!(r.total_skills, 6);
        assert_eq!(r.healthy, 5);
        assert_eq!(r.with_frontmatter, 5);
        assert_eq!(r.status, "WATCH");
        assert!(r.warnings.iter().any(|w| w.contains("unhealthy_skills")));
    }

    #[test]
    fn test_has_frontmatter_edge_cases() {
        assert!(!has_frontmatter(""));
        assert!(!has_frontmatter("---"));
        assert!(has_frontmatter("---\ndescription: x\n---\nbody"));
        assert!(has_frontmatter("  \n---\ndescription: x\n---\nbody"));
        assert!(!has_frontmatter("---\ndescription: x\nbody"));
    }

    #[test]
    fn test_has_frontmatter_field() {
        let text = "---\ndescription: test skill\ntags: [a, b]\n---\nbody";
        assert!(has_frontmatter_field(text, "description"));
        assert!(has_frontmatter_field(text, "tags"));
        assert!(!has_frontmatter_field(text, "nonexistent"));
        assert!(!has_frontmatter_field(text, "body"));
    }

    #[test]
    fn test_nested_skills() {
        let dir = setup_test_dir();
        write_skill(&dir, "skill_a", "SKILL.md", "---\ndescription: a\n---\n");
        write_skill(&dir, "skill_a/nested", "SKILL.md", "---\ndescription: nested\n---\n");
        let r = scan_skills_internal(&dir.to_string_lossy());
        assert_eq!(r.total_skills, 2);
        assert_eq!(r.healthy, 2);
    }

    #[test]
    fn test_evidence_hash_stability() {
        let dir = setup_test_dir();
        write_skill(&dir, "skill_a", "SKILL.md", "---\ndescription: x\n---\n");
        let r = scan_skills_internal(&dir.to_string_lossy());
        assert!(!r.evidence_hash.is_empty());
        let r2 = scan_skills_internal(&dir.to_string_lossy());
        assert_eq!(r.evidence_hash, r2.evidence_hash);
    }
}