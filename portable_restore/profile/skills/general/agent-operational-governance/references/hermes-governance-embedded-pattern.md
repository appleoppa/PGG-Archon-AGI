# Hermes Governance Embedded Pattern

## Session takeaway

When adding governance around `~/.hermes` or `~/.hermes/workspace`, do not stop at writing policy files. The policy must be embedded into the live rule chain and a deterministic checker.

## What worked

1. Create a small cluster of governance docs rather than one giant note.
2. Add explicit references from `AGENTS.md` and `TOOLS.md` to the governance docs.
3. Add a runnable audit script that checks existence, references, and permissions.
4. Add a DB/path whitelist so current authority is explicit.
5. Tighten permissions on high-sensitivity state files.
6. Re-run the audit script and treat warnings as real follow-up work.

## Files produced in this session

- `workspace/治理/ACTIVE_MANIFEST.md`
- `workspace/治理/ARCHIVE_INDEX.md`
- `workspace/治理/SESSION_REPAIR_RUNBOOK.md`
- `workspace/治理/CACHE_POLICY.md`
- `workspace/治理/SOURCE_BOUNDARY.md`
- `workspace/治理/DB_BOUNDARY_AUDIT.md`
- `workspace/scripts/governance_audit.py`
- `workspace/治理/db_whitelist.json`

## Failure mode to avoid

A governance file cluster that is not referenced by active rules is an island. It may be correct, but it is not operational.

## Reusable checklist

- Are the governance files linked from the active entry files?
- Is there a script that checks them?
- Is there a whitelist/manifest naming the current authority?
- Are permissions on sensitive DB/config files tightened?
- Does the audit exit green after the changes?
