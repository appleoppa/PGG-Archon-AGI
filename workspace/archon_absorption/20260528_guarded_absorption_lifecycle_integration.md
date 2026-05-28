# PGG Archon guarded absorption lifecycle integration evidence

Generated: 2026-05-28

## Integration target

- `agent/apex_archon_absorption.py`
- `agent/apex_gene_lifecycle.py`
- `runtime/quality/evidence_bundle.py` and `runtime/quality/gate_runner.py` integration path

## What changed

- Guarded absorption reports can now produce schema-valid `ApexRuntimeOSQualityEvidenceBundle/v1` bundles.
- Guarded absorption reports can now be evaluated by the existing CMMI-style quality gate.
- Guarded absorption gene candidates can now enter `build_gene_lifecycle_gate_from_runtimeos_status` through `archon_absorption_gene_candidate`.
- Lifecycle mapping remains read-only and does not write the gene library.

## Gate behavior

- Without test evidence: quality gate blocks on `test_report`.
- With test evidence: quality gate passes when requirements, rollback plan, security review, audit log, and documentation evidence are present.
- READY absorption candidates are mapped to lifecycle `verified` metadata.
- HOLD absorption candidates are mapped to lifecycle `active` metadata and are not promotable.

## Verification

Command:

```text
python -m pytest tests/agent/test_apex_archon_absorption.py tests/agent/test_apex_gene_lifecycle.py tests/runtime/test_quality_evidence_bundle_cli.py -q
```

Result:

```text
28 passed in 0.31s
```

Manual readback:

```text
candidate=READY
lifecycle=PASS
quality_gate=PASS
archon_absorption_gene_candidate.present=True
archon_absorption_gene_candidate.eligible=True
archon_absorption_gene_candidate.gene_library_written=False
```

## Boundary

This integrates the guarded absorption gene into formal lifecycle visibility and quality evidence gates. It still does not auto-promote, write the gene database, mutate memory/skills, or claim complete AGI capability.
