# GitHub Knowledge Enrichment + Capability Factor Matrix

Session-derived pattern for the second stage after broad GitHub radar ingestion.

## Trigger

Use after a broad GitHub legal/political/parser/search knowledge radar has already created repo cards and a wiki, and the user wants continued autonomous absorption when next-step value is >75%.

## Enrichment workflow

1. **Select bounded top repos by category**
   - Read normalized `data/repo_cards.jsonl`.
   - Select top N per class: `legal`, `political`, `parser`, `search`, `pi-main`/target-specific.
   - Use low N for user-facing morning/evening cron; reserve larger N for a separate deep enrichment job.

2. **Fetch read-only evidence only**
   - GitHub repo API metadata.
   - README snapshots.
   - LICENSE/COPYING snapshots.
   - Bounded recursive tree snapshot.
   - Do not clone-and-run or execute external repo code.

3. **Generate factor matrix**
   - Suggested factors:
     - `legal_benchmark`
     - `legal_workflow`
     - `legal_retrieval`
     - `chinese_law_fit`
     - `governance_factor`
     - `parser_search_tooling`
     - `security_license_risk`
   - Persist both machine JSON and Markdown summary.
   - Generate per-repo factor cards under `wiki/factor_cards/`.

4. **Evidence sufficiency penalty**
   - Do not let a repo with little/no README/LICENSE/tree evidence rank high merely because of noisy keyword matches.
   - Add an `evidence_chars`/`evidence_penalty` or equivalent field.
   - If evidence is below threshold, cap or penalize score and label as low evidence.

5. **Cron split to avoid timeout**
   - Morning/evening briefing should stay bounded and user-facing: ingestion + small enrichment + LLM audit + brief.
   - Larger Top10/full-category enrichment should be a separate `no_agent=true` deep job delivered `local`, so it can run without spamming or timing out the user channel.
   - If the integrated cron times out, reduce per-category N and keep the deep job for the heavy pass.

6. **LLM audit context upgrade**
   - Include the capability factor matrix excerpt in the compact multi-LLM audit context, not just the latest brief and sample repo cards.
   - Record provider/model/api_mode/status/path/hash as before.

## Output contract additions

Report:

- factor matrix path
- structured matrix JSON path
- factor card count
- latest enrichment audit path
- whether evidence penalty was applied
- separate deep enrichment cron job ID if created

## Boundary wording

Use wording like:

> “Stage-2 enrichment/factor extraction is installed and verified; it is not a claim that every external repo's source code has been fully understood or imported.”
