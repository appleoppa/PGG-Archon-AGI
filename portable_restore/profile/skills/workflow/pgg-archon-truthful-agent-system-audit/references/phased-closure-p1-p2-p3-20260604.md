# P1 → P2 → P3 Phased Closure Pattern (2026-06-04)

## When to use this reference

The user has given the Apple Didi a single-shot "all in" authorization:
"全部都做、做的彻底、不造假 … 要做就做到最好". The agent's job is
to push a long list of P0/P1/P2/P3 items to verifiable closure without
collapsing into "everything is BLOCKED". This reference records the
phased closure pattern that worked on 2026-06-04, plus the pitfalls
that bit during that day.

## The five-phase pattern (what worked)

1. **State-card first, then phased plan, then execute.** Do NOT start
   with LLM audit. Build a compact state card (processes, launchd,
   ports, custom_providers, profile skills + memory hash, cron, rust
   fused-watcher, git HEAD, rust `.so` list, evolution manifest
   headline, gene DB state, env key presence, home/desktop pollution,
   AGENTS.md/SOUL.md/USER.md presence). Hand the state card + outline
   files to multiple LLMs as one STRICT-JSON prompt. Disclose channel
   reality in the report (HTTP 502 / 403 are not silently mapped to
   PASS).
2. **P1 (real system hygiene) before P2 (status surfaces) before P3
   (eval harnesses).** P1 is bounded profile / config bootstrap —
   low/medium risk, high signal, easy rollback. P2 is bounded status
   surfaces with honest gaps. P3 is bounded eval harnesses with
   explicit boundary text. This order is also the order of increasing
   cost and decreasing verifiability, so failure rolls back to the
   last verifiable rung.
3. **Each P-iteration ends with: real tests + git commit + manifest
   readback + ≥2 LLM verify.** Commit, manifest, and verify are the
   same triple every iteration; this is what makes the "all in" push
   safe.
4. **Bounded status surface is honest, fake full module is a lie.** A
   `pgg_archon_research_unified_engine.py` whose state is `SKELETON`
   and whose boundary says "no real L4-L5 research harness" is good
   output. A `pgg_archon_research_unified_engine.py` that claims
   `READY` because all five `ARTIFACT_HINTS` exist on disk is a
   fabricated PASS and must not be emitted.
5. **Manifest `latest_<phase>_apply_<date>` is the single source of
   truth that the next session reads.** Always write the
   `summary.latest_<phase>_apply_<date>` key, always read it back,
   always include the boundary.

## The P1 closure scripts (reusable infrastructure)

- `agent/scripts/seed_profile_agents_md.py` — bounded AGENTS.md
  writer for any profile; idempotent; force-rewrites only with
  `--force`. See umbrella skill `pgg-archon-profile-bootstrap`.
- `agent/scripts/init_profile_memory.py` — bounded MEMORY.md
  initializer; reads SOUL.md first line + counts skills + extracts
  provider list from config.yaml.
- `agent/scripts/sync_profile_skills.py` — bounded skill copier;
  only copies, never deletes; supports `--exclude` substring filter.
- Two templates: `agent/scripts/templates/agents_md_template.md`,
  `agent/scripts/templates/memory_template.md`.

## The P3 eval-harness skeleton (reusable infrastructure)

- `agent/pgg_archon_redteam_harness.py` — 12 prompt-injection /
  jailbreak / overshare probes with conservative refusal heuristic.
  Status surface, not a real red-team campaign. Default probes are
  documented inline. See umbrella skill `pgg-archon-eval-harness-suite`.
- `agent/pgg_archon_multimodal_status.py` — four-modality check
  (text / image / audio / video) over local affordances. No actual
  image / audio / video generation. Honest gap reporting.
- `agent/pgg_archon_benchmark_corpus.py` + `pgg_archon_benchmark_harness.py`
  — 5-item-per-bench MMLU/GSM8K/BigBench corpus. Explicit
  `boundary: "5-item status corpus only; not a real MMLU/GSM8K/BigBench score"`
  is non-negotiable. Future agents must NOT remove the boundary even
  if the corpus grows.

## Pitfalls learned on 2026-06-04

### patch can break a function's call site silently

Adding `def _check_evidence(paths: list[str], home: Path)` while
leaving the only call site `_check_evidence(ev)` produced a runtime
`NameError` even though the test passed at import time. The fix is
mechanical — patch the call site in the same atomic edit — but the
lesson is: when extending a helper signature, grep for its name and
patch every call site in the same edit. Pyright caught the
"Argument missing for parameter home" only after the second patch
landed; a focused grep would have caught it first.

### shell heredoc + Python literal backticks

Heredoc-embedded Python like `re.sub(r"\`", ...)` gets interpreted by
bash before Python ever sees the source. Symptom: `bash: line 66: bad
substitution: no closing "`"`. Fix: write the script to a file with
`write_file` and run it with `python3 /path/to/script.py`. Do not
nest raw backticks inside a shell heredoc.

### shell variable inside heredoc

`$OUT` defined in one `bash -c` block is not visible in the next
`python3 - <<PY` heredoc because they are separate shell processes.
Either pass it on the same line (`python3 - <<PY ... $OUT ... PY`) or
use `os.environ.get` / read it inside Python. The 4-LLM verify
script crashed with `NameError: name 'OUT' is not defined` for this
reason.

### single-gate LLM quorum is not per-gene quorum

`evaluate_all_gene_candidates_promotion_gate` consumes one
`llm_quorum_path` for the whole candidate set. If the user asks
"逐个解决", do not pretend the global quorum applies to each
candidate — build a per-gene evidence pack, run a separate
`evaluate_llm_quorum_gate` with the per-gene evidence files, and feed
that into `promote_gene_transaction` with the right
`trigger_phase=..._per_gene_quorum`.

### top-level model_verdict hidden by nested decision BLOCKED

Any ad-hoc verdict classifier will be fooled by
`{"model_verdict": "PASS", "candidate_decisions": [{"decision":
"BLOCKED"}]}`. Always parse JSON first, then read top-level
`model_verdict` / `feasibility_ok`; never substring-search
"BLOCKED" in the raw text.

### smoke is mandatory before commit, not after

The first `_check_evidence` patch landed before the second patch
that fixed the call site, and the commit happened before pytest
caught the broken smoke. The lesson: run a focused smoke
(`python -m agent.<module> --help` or a one-line import + invoke)
in the same atomic edit as the patch that introduces the new
signature, then commit. Do not let commits race the smoke.

### launchd plist env-var injection must be verified

After `plutil -insert` + `launchctl unload + load`, verify with
`plutil -p` AND `launchctl getenv`. If `getenv` is empty even after
reload, fall back to `launchctl setenv` from a non-sudo shell. Do
not assume `unload + load` is sufficient to re-propagate domain env
vars.

## The honest-gap convention (carry forward)

Every bounded module written under this pattern must end with a
`boundary` field that names what it is NOT. Examples that worked:

- `boundary: "5-item status corpus only; not a real MMLU/GSM8K/BigBench score"`
- `boundary: "status surface only; no actual image/audio/video generation; tools must be invoked separately"`
- `boundary: "this module is a status surface, not an L4-L5 research harness"`
- `boundary: "internal engineering audit only; not external AGI benchmark; not full AGI proof; not legal correctness proof"`

If a future agent removes one of these `boundary` strings in the
name of "cleaning up the doc", that is the moment the bounded status
surface turns into a fabricated PASS. Treat boundary removal as a
red-flag equivalent to a fake-test rewrite.
