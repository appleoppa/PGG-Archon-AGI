# 2026-06-05 — 0006 case WATCH boundary pattern

## Trigger

Use when reviewing an existing case archive that has process outputs, LLM collaboration logs, and a final-looking document, especially when the ledger claims P0-P7 completion but guard/audit gaps remain.

## Lesson

A case can have a complete-looking P0-P7 workflow and still be only WATCH-grade evidence. The 0006 case demonstrated this:

- Positive evidence:
  - P0-P7 ledger exists.
  - FINAL v2 document exists.
  - v1 fact-error correction is documented and obsolete files are marked.
  - FINAL v2 self-check records 15/15 true facts and 0/8 known false facts.
- Remaining gaps:
  - `cms_case_guard_validate.json` status was `BLOCKED`.
  - Stage directory/layout mismatch remained unresolved.
  - Constructed case examples were explicitly non-real and must be replaced by real cases.
  - Party details were pending.
  - Specific grassroots court was pending.

## CMS rule

Do not equate:

```text
P0-P7 files exist + FINAL v2 exists
```

with:

```text
case externally file-ready / fully verified / PASS
```

If guard status is BLOCKED or material legal submission fields remain pending, classify as `WATCH` and state the exact open gaps.

## Reporting pattern

When asked to review such a case, report:

1. positive evidence;
2. open blockers/gaps;
3. whether it is usable as internal work product, external filing draft, or final filing-ready product;
4. what must close before PASS.

## Boundary

Programmatic self-check is useful but not a substitute for legal source verification, real case-law replacement, party/court information completion, CMS guard PASS, and lawyer review.
