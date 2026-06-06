# Ultimate Evolution Formula Phase 8 — Chain Integrity Gate

## Trigger
Use after Phase7 evidence-chain status is verified and the next step is low-risk hardening rather than core mutation.

## Purpose
Phase8 converts Phase3-7 evidence into a deterministic integrity manifest for cron/CI drift detection.

## What it verifies
- Phase7 report status is `evidence_chain_verified`.
- Phase3/4/5/6/7 report files exist and have SHA-256 hashes.
- Phase8 GPT review evidence exists and has `ok=true`.
- PGG DB readback exists for Phase3/4/5/6/7 genes.
- Cron wrapper includes `--phase4 --phase5 --phase6 --phase7`.

## Main files
- `agent/pgg_archon_ultimate_evolution_ars_cycle.py`
  - `build_phase8_chain_integrity_gate()`
  - `write_phase8_report()`
  - `persist_phase8_to_pgg_db()`
  - `run_phase8_cycle()`
- `tools/pgg_archon_tools.py`
  - action: `chain_integrity_status`
- `scripts/run_pgg_ultimate_evolution_ars_cycle.py`
  - flag: `--phase8`
- `~/.hermes/scripts/pgg_ultimate_evolution_phase3_ars_cycle.sh`
  - should run `--persist --phase4 --phase5 --phase6 --phase7 --phase8`

## Verification
Run:

```bash
venv/bin/python -m pytest tests/agent/test_pgg_archon_ultimate_evolution_ars_cycle.py tests/tools/test_pgg_archon_tools.py -q
venv/bin/python scripts/run_pgg_ultimate_evolution_ars_cycle.py --persist --phase8
```

Expected evidence:
- Tests pass.
- `phase8_status=integrity_verified`.
- `phase8_manifest_hash=<sha256-like hash>`.
- PGG DB gene name: `ultimate_evolution_formula_phase8_chain_integrity_gate`.

## Boundary
Read-only sidecar hardening only: no `run_agent.py` mutation, no secret read, no deployment, no git push, no AGI completion claim.
