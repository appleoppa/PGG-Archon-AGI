# Phase4 ARS Trend Replay + Gene Dedup Gate

## When this applies

Use this pattern when a periodic/no-agent cron sidecar writes PGG Archon experiment/gene records and repeated ticks may insert semantically identical genes.

## Durable lesson

A cron run that is healthy can still pollute the PGG gene DB by inserting the same capability summary every tick. Treat repeated stable scores and repeated gene names as a governance issue, not just harmless history.

## Pattern

1. Keep the existing periodic sidecar bounded and observable.
2. Add a read-only trend replay function that scans:
   - latest workspace report JSON;
   - recent `genes` rows for the same capability name;
   - recent `experiments` rows for the same cycle name.
3. Build a semantic fingerprint from stable fields only, for example:
   - schema;
   - status;
   - rounded score;
   - decision;
   - boundary.
4. Persist the recurring gene idempotently:
   - if a recent gene has the same fingerprint, skip insertion and return `deduped=True` with the existing `gene_id`;
   - if new semantics appear, insert and store the fingerprint in `code_snippet`.
5. Add a separate Phase/round gene for the dedup gate itself so the governance improvement is recorded once.
6. Update the no-agent cron wrapper to use the project venv when present and print compact non-empty stdout containing status, score, report path, gene id, and `deduped`.
7. Verify with:
   - py_compile;
   - targeted pytest;
   - direct cron wrapper invocation;
   - DB readback showing the recurring gene is skipped on the second invocation.

## Reporting rule

When reporting this class of fix, distinguish:

- previous duplicate rows found;
- new gate inserted once;
- subsequent cron writes skipped by fingerprint;
- old duplicates not deleted unless separately authorized.

## Safety boundary

This is a sidecar/database governance pattern. It does not require modifying `run_agent.py`, reading secrets, deploying services, pushing git, or deleting old DB rows.
