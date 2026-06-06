# Bounded GitHub scout absorption for evolution prompts

Use when the user asks to “continue evolution”, “learn from GitHub/open source”, or resolve a blocked evolution metric by learning from external projects.

## Pattern

1. Treat GitHub as a read-only evidence source unless the user explicitly authorizes clone/run/import.
2. Search bounded query sets aligned to the gap, for example:
   - agent evaluation framework LLM
   - self healing agent code repair
   - LLM agent benchmark evaluation
   - agent memory knowledge graph evaluation
   - multi-agent orchestrator retry fallback router
3. Store:
   - search result JSON;
   - selected README snapshots;
   - metadata: repo full_name, URL, stars, license, updated_at, description.
4. Apply evidence sufficiency penalties. A noisy search hit without README/license/tree evidence cannot be promoted high.
5. Classify only patterns, not code, unless separately audited:
   - observability/evaluation trace graph → reference pattern;
   - deterministic grading/repeated trials → benchmark pattern;
   - self-healing loop → sandbox-only candidate;
   - AGPL/high-risk repo → blocked for code absorption unless separately approved.
6. If this scout is used to refresh a local evolution score, explicitly say: “read-only scout; no external code imported or executed”.

## LLM evidence rule

“All LLMs participated” requires more than HTTP 200. Track `visible_output=true/false`. If a Responses API call returns HTTP 200 but `output=[]` or no visible text, record the transport evidence but do not count it as substantive model advice.

## Output fields

Return source paths, repo count, README count, LLM visible-output count, promoted patterns, blocked claims, and verification commands/results.
