# Sidecar Phase CLI and Cron Wrapper Extension Pattern

## Context

For bounded PGG Archon / Hermes sidecar chains, adding a new phase is not complete if only the builder/persistence function exists. The operational entry points also need to know how to run and report the phase.

## Pattern

When adding `phaseN`:

1. Add `run_phaseN_cycle()` and include it in `__all__`.
2. Extend the CLI imports and argparse flag, e.g. `--phaseN`.
3. Ensure higher phases auto-run prerequisite lower phases when missing.
4. Extend compact stdout suffix so the phase status/report/gene_id appear in cron logs.
5. Update the cron wrapper to run the highest safe phase, not an obsolete earlier phase.
6. Run both:
   - targeted pytest for the sidecar module;
   - the CLI or wrapper script itself.
7. Read back generated report and GeneDB row before claiming completion.

## Pitfall

A cron wrapper that still runs only an older phase makes later reports look incomplete (`cron_wrapper_has_phaseX=false`) even if the Python implementation exists. Treat the wrapper as part of the evidence chain.
