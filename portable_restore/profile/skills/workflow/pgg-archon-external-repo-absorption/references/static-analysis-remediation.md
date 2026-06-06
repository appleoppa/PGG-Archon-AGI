# Static analysis remediation after external repo absorption

Use this when an absorbed external repository has valuable patterns but is blocked by static-analysis findings (for example Bandit B608 dynamic SQL or B310 urllib/urlopen).

## Durable pattern

1. Do not treat a scanner warning as either automatically exploitable or automatically false-positive.
2. Build a bounded evidence pack: exact lines, data source for dynamic fragments, tests, scanner JSON, and relevant upstream docs.
3. Consult real configured LLM providers for the task class; do not role-play providers. Record skipped providers honestly when credentials are absent.
4. Check open-source authoritative references before using suppressions:
   - scanner rule docs;
   - language/library security docs;
   - mature framework implementations for analogous guard patterns.
5. Prefer code fixes first. Only use a precise `# nosec <RULE>` when all are true:
   - the line is individually reviewed;
   - the dynamic part is from an internal fixed set, generated placeholder length, or explicit allowlist;
   - user-controlled values are still parameter-bound or otherwise validated before the sink;
   - regression tests cover the guard;
   - the inline suppression comment states the guard.
6. Re-run tests, compile/syntax checks, and the scanner. Verified means scanner residuals are zero or every residual has a reviewed, documented reason accepted by the governing gate.
7. Write/update a boundary note when a pattern is absorbed without vendoring/core integration. Verified pattern absorption is not the same as core integration.
8. Update GeneDB/readback only after the post-fix evidence exists.

## Examples

- SQL `IN (?, ?, ...)` strings can be acceptable when the placeholder string is generated only from a trusted collection length and values are passed separately through DB-API binding.
- SQL `SET` fragments can be acceptable when assembled only from code-owned fixed fragments and all values are bound.
- `urllib.request.urlopen` calls can be acceptable when every reachable path validates scheme/host/loopback policy before request construction; static tools may not infer that data flow, so suppression must be narrow and commented.

## Pitfalls

- Do not add blanket scanner exclusions.
- Do not promote an architecture pattern to “core integrated” unless core code and tests prove that integration.
- Do not claim all LLMs participated when a provider was skipped for missing credentials or API failure.
