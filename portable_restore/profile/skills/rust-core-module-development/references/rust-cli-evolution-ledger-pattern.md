# Rust CLI Evolution Ledger Pattern

Use this when a Rust CLI / daemon has an evolution, benchmark, or multi-LLM pipeline that currently produces output but does not leave a durable, queryable execution record.

## Trigger

- The pipeline calls real models or performs real analysis, but results disappear after stdout/logs.
- The user asks to make an evolution pipeline into a real closed loop.
- You need evidence that a run happened without scraping terminal output.

## Minimal durable closure

Add an append/query store before adding auto-patching or promotion automation:

1. Create a dedicated SQLite ledger module, e.g. `src/evolution/store.rs`.
2. Record each run with at least:
   - `id`
   - `timestamp`
   - `input`
   - `main_result`
   - `aux_results_json`
   - `final_output`
   - `score`
   - `status`
   - `error`
3. Default DB path order:
   - explicit env override such as `NANOGPT_CLAW_EVOLUTION_DB`
   - app data dir such as `$NANOGPT_CLAW_DATA_DIR/evolution_runs.db`
   - local fallback such as `nanoGPT-claw.evolution.db`
4. Add CLI commands:
   - `evolve run <prompt>` — run the real pipeline and record it
   - `evolve recent [limit]` — list recent runs
   - `evolve stats` — show count, completed/failed, average score, latest timestamp, DB path
5. Persist both success and failure records. Failure records should set `status='failed'`, `score=0`, and store `error`.
6. Add unit tests using `tempfile` for store write/read/stats. Do not call external providers in unit tests.
7. Verify with both source gates and installed runtime gates:
   - `cargo fmt`
   - `cargo check --all-targets --message-format=short`
   - `cargo test`
   - `cargo build --release`
   - copy to target binary path
   - `codesign --remove-signature ... || true && codesign --force --sign - ...`
   - service restart / health check
   - one real `evolve run` smoke test via the service wrapper so provider env is loaded
   - SQLite readback from the real DB path
8. Commit only source/config/test files. Revert `target/.rustc_info.json` and keep runtime DBs ignored.

## Pitfalls

- Do not treat model stdout as persistence. A run is not closed until it is queryable after process exit.
- Do not use bare shell env for provider completeness when the service wrapper sources secrets; validate through the wrapper when possible.
- Do not let runtime DBs enter git. Add `*.db`, `*.db-shm`, `*.db-wal` to `.gitignore` if needed.
- A simple score is acceptable for the first closure, but report it honestly as a lightweight heuristic, not a benchmark.
- SQLite JSON functions differ by query shape: if `aux_results_json` is stored as an object, use `json_each`/application parsing rather than `json_array_length`.

## Next stage after minimal closure

After the ledger exists and is verified, promote the pipeline toward execution closure:

```text
evolve run
→ generate candidate improvement
→ write candidate table
→ score candidate
→ promote queue when score >= threshold
→ low-risk patch
→ cargo test
→ record promoted/rejected result
```
