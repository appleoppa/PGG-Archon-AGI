# SE20 / APEX-MEM / egress continuation notes

Use when continuing PGG Archon / SE20 local evolution from an already-modified working tree.

## Durable workflow lessons

1. Inspect pre-existing diffs before adding work.
   - A clean start can still become dirty from sibling/background evolution work.
   - Treat untracked modules as possible valuable artifacts, but verify them before staging.

2. Do not preserve unverified audit-score claims.
   - Manifest or report updates that add GPT/Claude/MIMO audit scores require real provider traces.
   - If the evidence is not present, remove or downgrade the claim before commit.

3. Sidecar bridges must be loopback-only by default.
   - APEX-MEM client/tool bridges should reject non-loopback URLs.
   - Tool output should summarize large hit records and strip embeddings or other high-volume fields.
   - Register sidecar tools deliberately in the intended toolset; do not rely only on auto-discovery.

4. Network/bypass probes must be safe by default.
   - Default CLI path should produce a static assessment or dry-run plan.
   - Live external network probes require an explicit flag such as `--live`.
   - Tests must validate safe defaults and avoid live network calls.

5. Egress guard tests should cover more than domain blocking.
   - Test resolved-IP blocking.
   - Test urllib3/requests compatibility.
   - Preserve `timeout` and `source_address`; strip only urllib3-only kwargs such as `socket_options` and `server_hostname`.

6. Readback parsing should isolate stdout/stderr.
   - Health/bootstrap commands may emit log noise like fail-closed warnings.
   - Capture stdout and stderr separately, then parse structured JSON from stdout robustly.

## Verification pattern

- Run targeted tests for the edited modules.
- Run a smoke readback for health/bootstrap/tool bridge.
- Run `git diff --check` before commit.
- Stage only the files verified in this round.
- Local commit is allowed for this repository; push/PR/official submission remains forbidden without explicit user instruction.
