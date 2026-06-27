use std::env;
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone)]
struct NativeProject {
    id: String,
    slug: String,
    name: String,
    primary_path: String,
    folders: Vec<String>,
}

fn usage() -> ! {
    eprintln!("Usage:\n  project-session-settle --project <id-or-slug> --title <title> --summary <summary> [--evidence <text>] [--status active|paused|completed|blocked] [--phase <phase>] [--root <projects_root>] [--native-home <hermes_home>] [--dry-run] [--no-native-check]\n  project-session-settle --project <id-or-slug> --show [--root <projects_root>] [--native-home <hermes_home>]\n\nHermes 0.17 mode: native ~/.hermes/projects.db is validated first; PGG overlay is auto-created when native project exists.");
    std::process::exit(2);
}

fn arg_value(args: &[String], key: &str) -> Option<String> {
    args.windows(2).find(|w| w[0] == key).map(|w| w[1].clone())
}

fn has_flag(args: &[String], key: &str) -> bool {
    args.iter().any(|a| a == key)
}

fn home_dir() -> String {
    env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string())
}

fn default_hermes_home() -> String {
    env::var("HERMES_HOME").unwrap_or_else(|_| format!("{}/.hermes", home_dir()))
}

fn shell_date_stamp() -> String {
    if let Ok(out) = Command::new("date").arg("+%Y%m%d-%H%M%S").output() {
        if out.status.success() {
            let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if !s.is_empty() {
                return s;
            }
        }
    }
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();
    format!("unix-{}", secs)
}

fn shell_iso_time() -> String {
    if let Ok(out) = Command::new("date").arg("+%Y-%m-%dT%H:%M:%S%z").output() {
        if out.status.success() {
            let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if !s.is_empty() {
                return s;
            }
        }
    }
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();
    format!("unix:{}", secs)
}

fn slugify(s: &str) -> String {
    let mut out = String::new();
    for ch in s.chars() {
        if ch.is_ascii_alphanumeric() {
            out.push(ch.to_ascii_lowercase());
        } else if ch.is_whitespace() || ch == '-' || ch == '_' {
            out.push('-');
        } else if ('\u{4e00}'..='\u{9fff}').contains(&ch) {
            out.push(ch);
        }
    }
    while out.contains("--") {
        out = out.replace("--", "-");
    }
    out.trim_matches('-').chars().take(64).collect::<String>()
}

fn json_escape(s: &str) -> String {
    let mut out = String::new();
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            _ => out.push(c),
        }
    }
    out
}

fn sql_quote(s: &str) -> String {
    format!("'{}'", s.replace('\'', "''"))
}

fn run_sqlite(db: &Path, sql: &str) -> io::Result<String> {
    let out = Command::new("sqlite3")
        .arg("-tabs")
        .arg(db)
        .arg(sql)
        .output()?;
    if !out.status.success() {
        let err = String::from_utf8_lossy(&out.stderr);
        return Err(io::Error::new(
            io::ErrorKind::Other,
            format!("sqlite3 failed: {}", err.trim()),
        ));
    }
    Ok(String::from_utf8_lossy(&out.stdout).to_string())
}

fn native_lookup(hermes_home: &str, token: &str) -> io::Result<Option<NativeProject>> {
    let db = PathBuf::from(hermes_home).join("projects.db");
    if !db.exists() {
        return Ok(None);
    }
    let q = sql_quote(token);
    let sql = format!(
        "SELECT id, slug, name, COALESCE(primary_path,'') FROM projects WHERE archived=0 AND (slug={q} OR id={q} OR name={q}) LIMIT 1;"
    );
    let out = run_sqlite(&db, &sql)?;
    let line = out.lines().next().unwrap_or("");
    if line.trim().is_empty() {
        return Ok(None);
    }
    let parts: Vec<&str> = line.split('\t').collect();
    if parts.len() < 4 {
        return Ok(None);
    }
    let pid = parts[0].to_string();
    let folder_sql = format!(
        "SELECT path FROM project_folders WHERE project_id={} ORDER BY is_primary DESC, added_at ASC, path ASC;",
        sql_quote(&pid)
    );
    let folders = run_sqlite(&db, &folder_sql)?
        .lines()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>();
    Ok(Some(NativeProject {
        id: pid,
        slug: parts[1].to_string(),
        name: parts[2].to_string(),
        primary_path: parts[3].to_string(),
        folders,
    }))
}

fn extract_json_string(text: &str, key: &str) -> Option<String> {
    let needle = format!("\"{}\"", key);
    let i = text.find(&needle)?;
    let after = &text[i + needle.len()..];
    let colon = after.find(':')?;
    let mut rest = after[colon + 1..].trim_start();
    if !rest.starts_with('"') {
        return None;
    }
    rest = &rest[1..];
    let mut out = String::new();
    let mut esc = false;
    for ch in rest.chars() {
        if esc {
            out.push(ch);
            esc = false;
            continue;
        }
        if ch == '\\' {
            esc = true;
            continue;
        }
        if ch == '"' {
            return Some(out);
        }
        out.push(ch);
    }
    None
}

fn extract_json_string_array(text: &str, key: &str) -> Vec<String> {
    let needle = format!("\"{}\"", key);
    let Some(i) = text.find(&needle) else {
        return Vec::new();
    };
    let after = &text[i + needle.len()..];
    let Some(colon) = after.find(':') else {
        return Vec::new();
    };
    let rest = after[colon + 1..].trim_start();
    if !rest.starts_with('[') {
        return Vec::new();
    }
    let mut values = Vec::new();
    let mut in_str = false;
    let mut esc = false;
    let mut cur = String::new();
    for ch in rest[1..].chars() {
        if in_str {
            if esc {
                cur.push(ch);
                esc = false;
            } else if ch == '\\' {
                esc = true;
            } else if ch == '"' {
                values.push(cur.clone());
                cur.clear();
                in_str = false;
            } else {
                cur.push(ch);
            }
        } else if ch == '"' {
            in_str = true;
        } else if ch == ']' {
            break;
        }
    }
    values
}

fn json_string_array(items: &[String], indent: &str) -> String {
    if items.is_empty() {
        return "[]".to_string();
    }
    let body = items
        .iter()
        .map(|s| format!("{}\"{}\"", indent, json_escape(s)))
        .collect::<Vec<_>>()
        .join(",\n");
    format!("[\n{}\n  ]", body)
}

fn push_unique(items: &mut Vec<String>, value: String) {
    if !items.iter().any(|x| x == &value) {
        items.push(value);
    }
}

fn ensure_overlay(
    project_dir: &Path,
    project_slug: &str,
    native: Option<&NativeProject>,
    dry_run: bool,
) -> io::Result<()> {
    if project_dir.join("project.json").exists() {
        return Ok(());
    }
    let Some(n) = native else {
        return Err(io::Error::new(
            io::ErrorKind::NotFound,
            format!(
                "missing overlay project.json and no native project available: {}",
                project_dir.display()
            ),
        ));
    };
    if dry_run {
        return Ok(());
    }
    fs::create_dir_all(project_dir.join("context"))?;
    fs::create_dir_all(project_dir.join("progress"))?;
    fs::create_dir_all(project_dir.join("decisions"))?;
    fs::create_dir_all(project_dir.join("sessions"))?;
    fs::create_dir_all(project_dir.join("sources"))?;
    fs::create_dir_all(project_dir.join("evidence"))?;
    fs::create_dir_all(project_dir.join("outputs"))?;
    fs::create_dir_all(project_dir.join("subprojects"))?;
    let iso = shell_iso_time();
    let folders_json = n
        .folders
        .iter()
        .map(|f| format!("    \"{}\"", json_escape(f)))
        .collect::<Vec<_>>()
        .join(",\n");
    let project_json = format!(
        "{{\n  \"id\": \"{}\",\n  \"name\": \"{}\",\n  \"status\": \"active\",\n  \"profile\": \"default\",\n  \"project_root\": \"{}\",\n  \"native_hermes_project_id\": \"{}\",\n  \"native_hermes_slug\": \"{}\",\n  \"primary_path\": \"{}\",\n  \"canonical_existing_paths\": [\n{}\n  ],\n  \"created_at\": \"{}\",\n  \"updated_at\": \"{}\",\n  \"context_policy\": {{\n    \"default_session_start\": \"先 hermes project show，再读 project.json、context/current.md、progress/status.json。\",\n    \"session_settlement\": \"重要 session 结束后使用 project-session-settle 写入 sessions 和 progress/status.json。\"\n  }}\n}}\n",
        json_escape(project_slug), json_escape(&n.name), json_escape(&project_dir.to_string_lossy()), json_escape(&n.id), json_escape(&n.slug), json_escape(&n.primary_path), folders_json, json_escape(&iso), json_escape(&iso)
    );
    fs::write(project_dir.join("project.json"), project_json)?;
    fs::write(
        project_dir.join("context/current.md"),
        format!(
            "# {}\n\n由 Hermes 0.17 原生 Projects 自动生成 overlay。\n",
            n.name
        ),
    )?;
    fs::write(
        project_dir.join("decisions/decisions.md"),
        "# Decisions\n\n- PGG overlay follows Hermes 0.17 native Projects as source of truth.\n",
    )?;
    fs::write(
        project_dir.join("README.md"),
        format!("# {}\n\nNative Hermes project id: `{}`.\n", n.name, n.id),
    )?;
    Ok(())
}

fn show_project(
    project_dir: &Path,
    project: &str,
    native: Option<&NativeProject>,
) -> io::Result<()> {
    println!("project={}", project);
    if let Some(n) = native {
        println!("native=OK id={} slug={} name={}", n.id, n.slug, n.name);
        println!("primary_path={}", n.primary_path);
        for f in &n.folders {
            println!("folder={}", f);
        }
    } else {
        println!("native=MISSING");
    }
    let pj = project_dir.join("project.json");
    println!(
        "overlay_project_json={} exists={}",
        pj.display(),
        pj.exists()
    );
    let status = project_dir.join("progress/status.json");
    println!(
        "overlay_status={} exists={}",
        status.display(),
        status.exists()
    );
    if status.exists() {
        let txt = fs::read_to_string(&status).unwrap_or_default();
        if let Some(updated) = extract_json_string(&txt, "updated_at") {
            println!("updated_at={}", updated);
        }
        if let Some(phase) = extract_json_string(&txt, "phase") {
            println!("phase={}", phase);
        }
    }
    Ok(())
}

fn main() -> io::Result<()> {
    let args: Vec<String> = env::args().collect();
    if args.len() == 1 || has_flag(&args, "--help") {
        usage();
    }
    let root = arg_value(&args, "--root")
        .unwrap_or_else(|| format!("{}/.hermes/workspace/projects", home_dir()));
    let hermes_home = arg_value(&args, "--native-home").unwrap_or_else(default_hermes_home);
    let project_arg = arg_value(&args, "--project").unwrap_or_else(|| usage());
    let dry_run = has_flag(&args, "--dry-run");
    let show = has_flag(&args, "--show");
    let no_native_check = has_flag(&args, "--no-native-check");

    let native = if no_native_check {
        None
    } else {
        native_lookup(&hermes_home, &project_arg)?
    };
    if !no_native_check && native.is_none() {
        eprintln!(
            "Native Hermes project not found in {}/projects.db: {}",
            hermes_home, project_arg
        );
        eprintln!(
            "Create it first with: hermes project create <name> <folders...> --slug {}",
            project_arg
        );
        std::process::exit(4);
    }
    let project_slug = native
        .as_ref()
        .map(|n| n.slug.clone())
        .unwrap_or(project_arg.clone());
    let project_dir = PathBuf::from(&root).join(&project_slug);
    ensure_overlay(&project_dir, &project_slug, native.as_ref(), dry_run)?;

    if show {
        return show_project(&project_dir, &project_slug, native.as_ref());
    }

    let title = arg_value(&args, "--title").unwrap_or_else(|| usage());
    let summary = arg_value(&args, "--summary").unwrap_or_else(|| usage());
    let evidence = arg_value(&args, "--evidence").unwrap_or_default();
    let status = arg_value(&args, "--status").unwrap_or_else(|| "active".to_string());
    let phase = arg_value(&args, "--phase").unwrap_or_else(|| "session-settled".to_string());

    let sessions_dir = project_dir.join("sessions");
    let progress_dir = project_dir.join("progress");
    let stamp = shell_date_stamp();
    let iso = shell_iso_time();
    let slug = slugify(&title);
    let session_file = sessions_dir.join(format!(
        "{}-{}.md",
        stamp,
        if slug.is_empty() {
            "session".to_string()
        } else {
            slug
        }
    ));
    let project_json = fs::read_to_string(project_dir.join("project.json")).unwrap_or_default();
    let overlay_name =
        extract_json_string(&project_json, "name").unwrap_or_else(|| project_slug.clone());
    let native_id = native.as_ref().map(|n| n.id.as_str()).unwrap_or("");
    let native_name = native
        .as_ref()
        .map(|n| n.name.as_str())
        .unwrap_or(&overlay_name);

    let native_block = if let Some(n) = native.as_ref() {
        format!(
            "- native_project_id: `{}`\n- native_slug: `{}`\n- native_primary_path: `{}`\n",
            n.id, n.slug, n.primary_path
        )
    } else {
        "- native_project_id: `SKIPPED_BY_NO_NATIVE_CHECK`\n".to_string()
    };
    let md = format!("# {}\n\n- project_id: `{}`\n- project_name: `{}`\n{}- settled_at: `{}`\n- status: `{}`\n- phase: `{}`\n\n## Summary\n\n{}\n\n## Evidence / Readback\n\n{}\n\n## Boundary\n\n- Native Hermes 0.17 Projects is the project identity/folder source of truth.\n- This receipt is the PGG overlay settlement layer, not a full transcript dump.\n- No provider/credential/security changes are implied by this receipt.\n", title, project_slug, native_name, native_block, iso, status, phase, summary, if evidence.is_empty(){"- 未提供额外证据。".to_string()}else{evidence.clone()});

    let previous_status = fs::read_to_string(progress_dir.join("status.json")).unwrap_or_default();
    let mut completed = extract_json_string_array(&previous_status, "completed");
    let in_progress = extract_json_string_array(&previous_status, "in_progress");
    let watch = extract_json_string_array(&previous_status, "watch");
    let blocked = extract_json_string_array(&previous_status, "blocked");
    push_unique(&mut completed, title.clone());

    let status_json = format!("{{\n  \"project_id\": \"{}\",\n  \"native_hermes_project_id\": \"{}\",\n  \"name\": \"{}\",\n  \"status\": \"{}\",\n  \"phase\": \"{}\",\n  \"updated_at\": \"{}\",\n  \"last_session\": {{\n    \"title\": \"{}\",\n    \"summary\": \"{}\",\n    \"evidence\": \"{}\",\n    \"session_file\": \"{}\"\n  }},\n  \"completed\": {},\n  \"in_progress\": {},\n  \"watch\": {},\n  \"blocked\": {}\n}}\n",
        json_escape(&project_slug), json_escape(native_id), json_escape(native_name), json_escape(&status), json_escape(&phase), json_escape(&iso), json_escape(&title), json_escape(&summary), json_escape(&evidence), json_escape(&session_file.to_string_lossy()), json_string_array(&completed, "    "), json_string_array(&in_progress, "    "), json_string_array(&watch, "    "), json_string_array(&blocked, "    ")
    );

    if dry_run {
        println!(
            "DRY_RUN project={} native_id={} session_file={} progress_file={}",
            project_slug,
            native_id,
            session_file.display(),
            progress_dir.join("status.json").display()
        );
        println!("---SESSION_MD_PREVIEW---\n{}", md);
        return Ok(());
    }

    fs::create_dir_all(&sessions_dir)?;
    fs::create_dir_all(&progress_dir)?;
    if progress_dir.join("status.json").exists() {
        let backup = progress_dir.join(format!("status.json.bak.{}", stamp));
        fs::copy(progress_dir.join("status.json"), backup)?;
    }
    fs::write(&session_file, md)?;
    fs::write(progress_dir.join("status.json"), status_json)?;

    let mut stdout = io::stdout();
    writeln!(
        stdout,
        "OK project={} native_id={}",
        project_slug, native_id
    )?;
    writeln!(stdout, "session_file={}", session_file.display())?;
    writeln!(
        stdout,
        "progress_file={}",
        progress_dir.join("status.json").display()
    )?;
    Ok(())
}
