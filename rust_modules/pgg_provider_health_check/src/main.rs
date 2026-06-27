use serde::Serialize;
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::time::{Duration, Instant};

const PROVIDERS: &[(&str, &str, &str)] = &[
    ("5yuantoken", "https://5yuantoken.org/v1/models", "5yuantoken gateway"),
    ("ark", "https://ark.cn-beijing.volces.com", "Ark API"),
    ("anthropic", "https://api.anthropic.com", "Anthropic API"),
];

fn home_dir() -> PathBuf {
    PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/Users/appleoppa".to_string()))
}

fn health_log_path() -> PathBuf {
    home_dir().join(".hermes/data/provider_health_check.log")
}

fn latest_json_path() -> PathBuf {
    home_dir().join(".hermes/data/provider_health_latest.json")
}

#[derive(Serialize)]
struct HealthResult {
    provider: String,
    url: String,
    description: String,
    status_code: u16,
    latency_ms: u64,
    healthy: bool,
    error: String,
}

#[derive(Serialize)]
struct HealthReport {
    schema: String,
    timestamp: String,
    results: Vec<HealthResult>,
    all_healthy: bool,
    boundary: String,
}

fn check_endpoint(name: &str, url: &str, description: &str, timeout_secs: u64) -> HealthResult {
    let start = Instant::now();

    // Use GET (not HEAD) for maximum compatibility — some servers
    // (e.g. api.5yuantoken.com) drop HEAD connections with TLS reset.
    // The body is discarded; this is still zero-bill since no API
    // credentials are sent and the response body is tiny (error page).
    let agent = ureq::Agent::new_with_config(
        ureq::config::Config::builder()
            .timeout_global(Some(Duration::from_secs(timeout_secs)))
            .no_delay(true)
            .build()
    );

    let result = agent.get(url)
        .header("User-Agent", "Hermes-Agent/1.0")
        .call();

    let latency_ms = start.elapsed().as_millis() as u64;

    match result {
        Ok(response) => {
            let status = response.status().as_u16();
            let healthy = status == 200 || status == 401 || status == 403 || status == 404;
            HealthResult {
                provider: name.to_string(),
                url: url.to_string(),
                description: description.to_string(),
                status_code: status,
                latency_ms,
                healthy,
                error: String::new(),
            }
        }
        Err(ureq::Error::StatusCode(status)) => {
            let healthy = status == 401 || status == 403 || status == 404;
            HealthResult {
                provider: name.to_string(),
                url: url.to_string(),
                description: description.to_string(),
                status_code: status,
                latency_ms,
                healthy,
                error: format!("HTTP {}", status),
            }
        }
        Err(e) => {
            HealthResult {
                provider: name.to_string(),
                url: url.to_string(),
                description: description.to_string(),
                status_code: 0,
                latency_ms,
                healthy: false,
                error: format!("{}", e),
            }
        }
    }
}

fn iso_timestamp() -> String {
    let output = std::process::Command::new("date")
        .arg("+%Y-%m-%dT%H:%M:%S%z")
        .output()
        .ok()
        .and_then(|o| {
            if o.status.success() {
                String::from_utf8(o.stdout).ok()
            } else {
                None
            }
        })
        .unwrap_or_else(|| "unknown".to_string());
    output.trim().to_string()
}

fn append_log(report: &HealthReport) -> std::io::Result<()> {
    let path = health_log_path();
    let line = serde_json::to_string(report).unwrap_or_default();
    let mut file = fs::OpenOptions::new().create(true).append(true).open(&path)?;
    writeln!(file, "{}", line)?;
    Ok(())
}

fn write_latest_json(report: &HealthReport) -> std::io::Result<()> {
    let path = latest_json_path();
    let json = serde_json::to_string_pretty(report).unwrap_or_default();
    fs::write(&path, json)
}

fn trim_log(max_lines: usize) -> std::io::Result<()> {
    let path = health_log_path();
    if !path.exists() {
        return Ok(());
    }
    let file = fs::File::open(&path)?;
    let reader = BufReader::new(file);
    let lines: Vec<String> = reader.lines().filter_map(|l| l.ok()).collect();
    if lines.len() > max_lines {
        let trimmed = lines[lines.len() - max_lines..].join("\n");
        fs::write(&path, trimmed + "\n")
    } else {
        Ok(())
    }
}

fn main() {
    let results: Vec<HealthResult> = PROVIDERS
        .iter()
        .map(|(name, url, desc)| check_endpoint(name, url, desc, 10))
        .collect();

    let all_healthy = results.iter().all(|r| r.healthy);
    let ts = iso_timestamp();

    let report = HealthReport {
        schema: "pgg-provider-health-check/v1".to_string(),
        timestamp: ts,
        results,
        all_healthy,
        boundary: "HTTP HEAD health check - zero token consumption, no API credentials used. Not a production traffic or LLM quality verification.".to_string(),
    };

    let json = serde_json::to_string_pretty(&report).unwrap_or_default();
    println!("{}", json);

    if let Err(e) = append_log(&report) {
        eprintln!("WARN: failed to append log: {}", e);
    }
    if let Err(e) = write_latest_json(&report) {
        eprintln!("WARN: failed to write latest.json: {}", e);
    }
    if let Err(e) = trim_log(1000) {
        eprintln!("WARN: failed to trim log: {}", e);
    }

    if !all_healthy {
        std::process::exit(1);
    }
}