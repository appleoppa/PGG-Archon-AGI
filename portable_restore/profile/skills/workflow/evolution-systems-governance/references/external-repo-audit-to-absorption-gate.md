# External Repo Audit → PGG Archon Absorption Gate Pattern

## Trigger

Use after cloning/deploying an external repository and the user asks whether PGG Archon can “吸收/吞噬” it, or asks for GPT/Claude audit before absorption.

## Proven sequence

1. **Local deploy first**
   - Clone to a clean workspace.
   - Install in an isolated environment.
   - Run tests and a minimal runtime smoke test.
   - If low-risk test failures block deployment, fix them and re-run tests before audit.

2. **Generate evidence pack**
   - Inventory: git HEAD, file list, code line counts, key config.
   - Static/runtime checks: pytest, compileall, dependency check, lint/security scanners where available.
   - Pattern scan: dynamic SQL, urlopen/network egress, weak hashes, unsafe deletion, broad exceptions, secret-like strings.
   - Persist evidence under the repo’s own `audit_reports/` directory, not root.

3. **Call real GPT via Responses API**
   - GPT/Claude configured as `codex_responses` must use `/v1/responses`, not `/v1/chat/completions`.
   - Large evidence may cause remote disconnects; compact the evidence JSON and retry with bounded output.
   - Save raw response JSON and extracted Markdown report.

4. **Classify absorption candidates**
   - `READY`: process/test/security rule already verified by real evidence and safe to absorb as a gene/pattern.
   - `READY_WITH_REVIEW`: useful rule, but must be mapped against PGG Archon/Hermes local surfaces before code integration.
   - `CANDIDATE`: architectural idea only; do not claim absorbed until P1/P2 risks are resolved and local integration is verified.

5. **Run PGG Archon gate**
   - Map candidates to lifecycle metadata.
   - Use `build_gene_lifecycle_gate_report` or equivalent read-only gate first.
   - Prefer `PARTIAL_ABSORB` when only some candidates are promotable.
   - Do not write GeneDB unless the item is verified and the write path/readback is part of the task.

6. **Report with side-effect honesty**
   - State whether GeneDB was written or only a read-only gate report was generated.
   - List promotable and non-promotable genes separately.
   - Include evidence file paths and commit/HEAD if pushed.

## Candidate classes observed

- Audit evidence compression + GPT Responses API review chain: usually `READY` as a process gene.
- Weak hash retirement (MD5 → SHA-256 or explicit non-security use): `READY` only after tests and scanner readback confirm the warning disappeared.
- Security test minimum set (SQL/URL/audit/path/hash): `READY` as a test template.
- Dynamic SQL field allowlist: `READY_WITH_REVIEW`; integrate only after checking local SQL construction surfaces.
- URL scheme/host allowlist against SSRF/privacy egress: `READY_WITH_REVIEW`; map provider/plugin/gateway egress points first.
- Broad exception/no silent failure rule: `READY_WITH_REVIEW`; batch fixes must be targeted and tested.
- Audit-log redaction and cross-user history isolation: `CANDIDATE` until local table/schema access boundaries are verified.
- Whole memory/retrieval architecture from a repo with unresolved P1/P2 findings: `CANDIDATE`; absorb patterns, not the package wholesale.

## Pitfalls

- Do not treat a successful clone or private mirror as deployment.
- Do not treat a GPT audit as absorption; it is evidence for the gate.
- Do not turn scanner findings into permanent negative claims; capture the verified fix or gate pattern.
- Do not commit transient raw oversized packs unless they are intentionally part of the audit evidence.
