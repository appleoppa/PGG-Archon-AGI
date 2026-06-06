# GitHub topic:law Top3 → Reasonix/APEX Rust law-core factor fusion

## Trigger

Use when the user asks to learn from top GitHub law/legal repos and merge them into PGG Archon / Reasonix / APEX-SKILL / Rust-owned fusion core factors.

## Proven workflow (2026-06-06)

1. Use `gh api 'search/repositories?q=topic:law&sort=stars&order=desc&per_page=10'` rather than broad `law in:name,description,readme`; broad search is polluted by unrelated high-star projects.
2. For Top3 evidence, fetch repo metadata and README via `gh api repos/<repo>/readme --jq .content | base64 --decode`; Python `json.loads` on raw `gh api` output can fail on control characters/truncation.
3. Write repo cards and README snapshots under the Reasonix/APEX evidence directory, including `readme_sha256`.
4. Call GPT/Claude through `/responses` (`codex_responses`) when available; record provider/model/status/output_path/sha256. If Claude returns 403, mark `ERROR_HTTP_403` truthfully and do not role-play Claude.
5. Convert patterns into bounded factors, not legal conclusions:
   - `LAW-RAG-SOURCE-CONTEXT`: jurisdiction/source_hash/version/citation/doc_chunk gate.
   - `LAW-RISK-CASE-TAXONOMY`: category/risk_signal/statute_hint/evidence_gap matrix.
   - `LAW-LICENSE-OBLIGATION-MATRIX`: obligations/permissions/limitations license gate.
6. Add Rust structs such as `LegalCoreFactor` and `LlmAuditEvidence`; include factors and LLM evidence in `FusionManifest`.
7. Add tests for factor count, weight sum ≈ 1.0, factor IDs, truthful LLM evidence, and anti-overclaim boundaries.
8. Run `cargo fmt`, `cargo test`, `cargo build --release`, generate the fusion manifest, and update `~/.hermes/data/EVOLUTION_MANIFEST.json` only after readback.

## Pitfalls

- Do not include literal overclaim terms in `safety_boundary` strings if tests assert anti-overclaim; phrase as “必须由专业人工复核” rather than “不替代律师”.
- `execute_code` may not inherit provider secrets even when `terminal` does; use terminal Python for real provider calls if needed.
- A GitHub Top3/topic result is popularity evidence, not legal authority. The absorbed artifact is a bounded process factor.

## Evidence contract

Report: repo cards path, README hashes, GPT/Claude call evidence, Rust test/build output, generated manifest path/hash, EVOLUTION_MANIFEST readback, remaining provider blockers.
