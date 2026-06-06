# Dynamic LLM audit evidence + GitHub API pattern — 2026-06-06

## Trigger

Use inside `open-source-legal-learning` when refreshing GitHub law/legal repo learning and Rust fusion manifests across sessions.

## Durable lessons

1. **Do not keep LLM audit evidence hardcoded to an old run**
   - The Rust fusion manifest should support injecting the current run's audit records via an evidence JSON path such as `PGG_LAW_LEARNING_AUDITS_JSON`.
   - Keep a safe default audit list only as fallback/backward compatibility.
   - Add a unit test proving the manifest builder loads the injected JSON and preserves truthful statuses such as `OK_HTTP_200` and `ERROR_HTTP_403`.

2. **Use terminal/runtime environment for real provider calls when sandboxed helpers lack secrets**
   - If a helper environment does not expose provider keys, do not treat that as provider failure.
   - Re-run the provider call from the normal terminal/runtime environment and record `key_present`, `provider`, `model`, `api_mode`, `http_status`, `status`, `output_path`, `sha256`, and elapsed time.
   - If Claude/GPT returns a real HTTP error, store that error body and report it honestly rather than role-playing model participation.

3. **GitHub API query shape**
   - `gh api search/repositories?q=topic:law&sort=stars&order=desc&per_page=10` works as a GET endpoint.
   - Avoid `gh api search/repositories -f q=...` without `-X GET`; `-f` can turn the request into an unintended POST and return 404.
   - For robust parsing, save raw stdout to evidence, then parse JSON from stdout only. Keep stderr separate so logs do not corrupt JSON parsing.

4. **Evidence pack shape**
   - Save `repo_cards.json`, per-repo `repo_card.json`, `README.snapshot.md`, `llm_audit_records.json`, `SHA256SUMS.txt`, a human report, and the Rust fusion manifest.
   - The manifest readback should include at least: schema, status, `rust_owned`, `hermes_core_mutation`, readiness score, factor count, LLM audit records, and manifest sha256.

## Rust gate checklist

- `cargo fmt`
- `cargo test` with a specific test for dynamic LLM audit JSON loading
- `cargo build --release`
- Generate manifest with:

```bash
PGG_LAW_LEARNING_AUDITS_JSON="$EVID/llm_audit_records.json" \
  ./target/release/pgg_reasonix_apex <Reasonix path> <APEX-SKILL path> \
  > "$EVID/fusion_manifest_legal_learning.json"
```

## Truth boundary

This pattern proves current-run evidence injection and Rust manifest generation. It does not prove production legal reasoning, official legal benchmark success, full AGI, or that a failed provider participated successfully.
