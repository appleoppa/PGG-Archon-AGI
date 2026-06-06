# Hermes Evolution Pipeline Entry

Session-specific note for the evolution stack that was built and verified on 2026-05-23.

## What worked

- A read-only pipeline script can be used as the cron entrypoint:
  - `/Users/appleoppa/.hermes/scripts/hermes_evolution_pipeline.py`
- The script should do the following in order:
  1. run `hermes_digest.py`
  2. build a proposal JSON from the digest output
  3. run `hermes_evolution_apply.py --proposal <proposal.json>` in dry-run mode
  4. export trajectories
  5. score trajectories
  6. pack datasets
  7. train the tiny baseline model
  8. predict from the trained model
  9. write a pipeline report JSON
- The cron job can be created with `hermes cron create --no-agent --script hermes_evolution_pipeline.py ...`
- The resulting job is visible in `hermes cron list` after creation.

## Important pitfall

- `hermes_evolution_apply.py` does **not** accept bare execution. It requires `--proposal`.
- If a pipeline calls apply before creating a proposal file, the run fails immediately.
- Do not wire the cron job directly to `hermes_evolution_apply.py`; wire it to the pipeline script instead.

## Verification pattern

- Run the pipeline script once manually and confirm it exits with status `ok`.
- Read back the generated report file, not just stdout.
- Confirm the cron job exists with `hermes cron list`.
- Keep the job read-only and `no-agent` unless a future task explicitly needs agent-driven behavior.
