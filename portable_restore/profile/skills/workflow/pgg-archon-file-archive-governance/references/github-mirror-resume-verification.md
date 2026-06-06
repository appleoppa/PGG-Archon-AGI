# GitHub mirror resume verification pattern

## Trigger

Use after a background `git clone --bare` / `git push --mirror` / repo mirror batch finishes, especially when the process exit code is 0 but individual repo logs contain `RPC failed`, `curl 56`, `remote end hung up`, `push-failed-*`, or other partial-transfer signals.

## Core lesson

Do not equate process exit code or script summary with mirror correctness. Verify the remote by reading refs back from both source and destination.

## Verification steps

1. Preserve the raw log and status TSV under the job `logs/` directory.
2. For each repository, run readback against both remotes:
   - `git ls-remote --heads --tags <source-url>`
   - `git ls-remote --heads --tags <destination-url>`
3. Compare by ref name and SHA:
   - `missing from destination`: source refs absent on destination.
   - `mismatched SHA`: same ref exists but points to a different commit/tag object.
   - `extra on destination`: destination has refs absent from source.
4. Classify status:
   - `PASS`: source and destination refs exactly match; no missing, mismatch, or extra refs.
   - `PASS_WITH_EXTRA_DEST_REFS`: destination contains every source ref with matching SHA, but also has extra refs. This is complete for backup/source coverage but not an exact mirror-prune state.
   - `FAIL`: any source ref is missing or any shared ref has mismatched SHA.
5. Write a compact verification report with:
   - process exit code;
   - raw log path and SHA256;
   - status TSV path and SHA256;
   - per-repo source/destination ref counts;
   - missing/mismatched/extra counts;
   - clear conclusion distinguishing source coverage from exact mirror cleanliness.

## Pitfalls

- `git push --mirror` can log an RPC disconnect yet still leave the destination containing all source refs; only ref readback decides source coverage.
- Extra destination refs after a failed mirror push mean prune did not complete. Do not call this an exact mirror, but do not falsely call it data loss if missing and mismatched counts are zero.
- Avoid destructive prune cleanup unless the user explicitly wants strict mirror equality and the extra refs have been listed/reviewed.
