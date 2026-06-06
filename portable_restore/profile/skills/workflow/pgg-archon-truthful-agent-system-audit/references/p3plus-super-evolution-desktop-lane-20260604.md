# P3+ Super-Evolution Desktop Audit Lane — 2026-06-04 lessons

When the user asks to "read all 超级进化 files, call all LLMs, advance
evolution by file number, no fabrication", apply this bounded pattern
instead of trying to process all 33 files in one turn.

## 1. 5-step closed loop (canonical, used in 2026-06-04)

1. **Lightweight index first** — list files + size + first line; do not
   read full bodies in round 1. Save to
   `~/.hermes/workspace/audit/super_evolution_index_<ts>.json`.
2. **Priority sort** — build a P0/P1/P2/P3 list based on local evidence
   (what is already implemented, what is honest gap, what is half-done).
3. **One priority per turn, multi-file** — execute every item in the
   priority before moving on; do not leave a priority half-done.
4. **After each priority** — git commit + 4-LLM audit panel + manifest
   readback; never claim completion without evidence.
5. **Next priority** — only after readback is committed.

This produces bounded deliverables (P0 5/5, P1 5/5, P2 5/5, P3 7/7
across multiple turns) instead of a single inflated claim.

## 2. Multi-LLM robustness — single provider failure must not block

When calling N providers in parallel for redteam smoke / corpus gen /
bench:

- **Each provider has its own try/except** — `try: … except: append
  error` per (provider, category). Do NOT abort the loop on first
  failure.
- **Surface failures honestly** — record `{provider, status: "error",
  error: "...", probes: []}`. Do NOT inflate to PASS.
- **Continue with successful providers** — Agnes + DeepSeek alone can
  produce 12/20 expected cells when MiniMax + MiMo return 0 due to
  policy-rejection or reasoning-only content.
- **MiniMax-specific gotcha** — reasoning model returns
  `reasoning_content`; the visible `content` may be empty. Strip
  `` blocks before JSON parse; otherwise every parse returns 0.
- **MiMo specific** — on redteam generation prompts MiMo may return a
  full safety refusal (text is policy language, not JSON). Treat
  `probes: []` as the honest result, not a parser bug.

## 3. Robust JSON parser pattern (`_try_parse_json_obj`)

LLM output for structured tasks is unreliable. Apply a 3-stage parser
before treating the response as failure:

1. `json.loads(raw)` — happy path.
2. `json.loads(raw[a:b+1])` where `a = raw.find('{')` and
   `b = raw.rfind('}')` — strip surrounding prose.
3. Balanced brace scan from left, return the first valid `json.loads`
   window — recovers nested objects.

After all three, if still no valid JSON, run a regex fallback:
`re.findall(r'"prompt"\s*:\s*"([^"]{6,300})"', raw)` to salvage
partially-structured output. This is preferable to silent zero-probe
failure.

Test the parser with 4 unit cases: raw, window, balanced, and None.

## 4. Forbidden idioms discovered in this session

- **`re.sub(r'^...', ..., text)` inside `python3 - <<'PY' ... PY`
  heredoc with shell $-expansion** — the literal `$` in
  `re.sub(r"^```(?:json)?\s*", "", s, flags=re.I)` gets mis-evaluated
  by bash and you get `bad substitution: no closing "`" in $`. **Fix**:
  write the script to a file with `write_file`, then run
  `python3 /tmp/...py`. Never embed `re.sub` regex with `$` in a
  heredoc.
- **`terminal(...)` foreground with `--timeout=600` for 6+ calls** —
  the tool will block for the full 10 minutes. **Fix**: use
  `terminal(background=true, notify_on_complete=true)` for any LLM
  call that may take >60s. Poll `process` later; multiple background
  processes can run in parallel without blocking the turn.
- **`terminal(...)` with shell-level background wrappers (nohup /
  disown / setsid / trailing `&`)** — Hermes refuses the call with
  `Foreground command uses shell-level background wrappers`. **Fix**:
  use `terminal(background=true, ...)` and let Hermes track the
  process. Do NOT add `nohup` / `disown`.
- **Long `write_file`** — if the payload exceeds ~8K tokens, the
  stream times out and the file is NOT written. **Fix**: split into
  multiple `write_file` (one per file) or use `patch` for small edits,
  or `skill_manage(action='write_file')` with the path under
  `references/` / `templates/` / `scripts/`.

## 5. Audit lane state surface (telemetry to keep watching)

`pgg_archon_super_evolution_lane.py` emits a per-run snapshot of
three orthogonal surfaces:

- `tiangong_summary_state`: PARTIAL / READY / ABSENT (4 cores:
  evolver, autoresearch, openhands, superpowers)
- `research_engine_state`: SKELETON / ARMED / READY (3/5 artifact
  hints typically present)
- `multimodal_overall`: READY / PARTIAL / ABSENT (4 modalities:
  text, image, audio, video)

These three numbers are the bounded proxies for "AGI level 1–5"
progress on this machine. Track them per pass; do NOT conflate with
external benchmark scores.

## 6. Reporting rule for this lane

When a per-priority turn is done, the report MUST include:

- Status: 完成 / 部分完成 / BLOCKED
- 已核验: process / launchctl / plist / port / dirs / logs / state card
- 证据: HTTP code / smoke refusal rate / bench accuracy / test
  passed / commit hash / sha256 of evidence file
- 边界: 5-item corpus / heuristic refusal / not production red-team
  / not full AGI / not external benchmark

The boundary string is the one piece that is non-negotiable; every
redteam or benchmark pass must explicitly say "5-item status corpus
only; not a real MMLU/GSM8K/BigBench score nor a production red-team
campaign". This is what keeps the report truthful when the user asks
"are you sure this is real?".
