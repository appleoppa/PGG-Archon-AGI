# Multi-LLM Parallel Smoke on a Tight Tool Budget (2026-06-04)

Reference notes for `full-toolcall-integration` when the task is "run the
same N-item smoke against M providers and consolidate".

## Hard rules learned this session

1. **Always background for N×M > 50.** With the foreground cap at 600s and
   typical 5–8s/probe on chat_completions, 4 providers × 30 probes = ~120
   probes × 6s = 720s. Background it from round 1. Use
   `terminal(background=true, notify_on_complete=true)`.

2. **Don't `process(action="poll")` more than ~3 times per background
   session.** Each poll is a tool call. A 240s run at 5s polls = 48 calls
   of pure noise. Pattern:
   - 1 call: `ls -la OUT/`
   - 1 call: `ps -axo pid,etime,args | egrep harness`
   - 1 call: `process(action="wait")` at end
   - 1 call: read final JSON

3. **Use a single bash file for "fire all providers in background" only
   if you can keep shell-level background wrappers out.** In Hermes CLI
   you cannot (`nohup`/`disown` rejected). Spawn 4 background terminals
   in parallel instead.

4. **Heredoc + regex with backticks is fragile.** Put multi-line Python
   in `/tmp/foo.py` via `write_file` and run it.

5. **Verdict classifier fix is now upstream.** The `pgg_archon_llm_quorum_gate`
   patch landed in this session. Future sessions inherit it; do not
   re-implement the substring `BLOCKED` rule.

## The 1-round "ideal" trajectory for 4-LLM × 30-probe redteam

```
tool 1: write_file agent/pgg_archon_redteam_extended_probes.py
tool 2: patch redteam_harness.py to import EXTENDED + add --extended
tool 3: write_file tests/test_pgg_archon_redteam_extended.py
tool 4: terminal  (pytest + commit)
tool 5: terminal(background=true, notify_on_complete=true)  -- DS 30
tool 6: terminal(background=true, notify_on_complete=true)  -- MiMo 30
tool 7: terminal(background=true, notify_on_complete=true)  -- Agnes 30
tool 8: terminal  -- file-poll + ps-poll (after ~120s wall, NOT 24 polls)
tool 9: terminal  -- file-poll (after ~260s wall, slowest)
tool 10: write_file /tmp/p3_verify_4llm.py
tool 11: terminal  -- 4-LLM verify (one shot, parallel)
tool 12: terminal  -- update manifest
```

Total: 12 tool calls. This session used ~30 because of polling + 2 re-tries
of the harness patch and the heredoc backtick collapse.

## Channel reality disclosure (always record)

For each provider, record: `http_status`, `visible_output_chars`,
`classified_verdict`, `refused_count` (for redteam) or `accuracy`
(for bench), and a 1-line `note`. Do not let any of these be silently
filled in by a stub. If a provider fails (GPT 502, Claude 403), record
it as `ERROR` and exclude from median score calculations. See
`pgg-archon-truthful-agent-system-audit` rule 8.

## Common failure modes vs. fix

| Symptom | Likely cause | Fix |
|---|---|---|
| `NameError: name 'field' is not defined` after dataclass patch | patch dropped `asdict`, `field` etc. | re-emit the full `from dataclasses import ...` line in one patch |
| heredoc backtick error | unquoted heredoc + `\s*` | `write_file` to `/tmp/foo.py` and `python3 /tmp/foo.py` |
| `ModuleNotFoundError: No module named 'agent'` from ad-hoc import | wrong cwd | `python -m agent.foo` with `cwd=hermes-agent/` |
| `nohup` rejected | shell-level wrapper | `terminal(background=true)` |
| `process(action="poll")` for 240s uses 24 calls | polling | file-poll + ps-poll + 1 final wait |
| LLM returns top-level `model_verdict: PASS` but `candidate_decisions[*].decision: BLOCKED` → naive classifier says BLOCKED | substring rule | already fixed upstream; do not reintroduce |
