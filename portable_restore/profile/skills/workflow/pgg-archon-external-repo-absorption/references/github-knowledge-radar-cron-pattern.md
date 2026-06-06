# GitHub Knowledge Radar + Cron Brief Pattern

Use this pattern when the user asks to “call all LLMs”, search GitHub broadly, absorb top projects, build a wiki/knowledge base, parse PDF/images, and keep daily briefings running.

## Class-level workflow

1. **Bound the target corpus**
   - Create a dedicated workspace knowledge directory, not Home/root.
   - Add `wiki/SCHEMA.md`, `wiki/INDEX.md`, `data/`, `audits/`, `gallery/`, `briefs/`, `scripts/`, `sources/`.
   - Treat ambiguous project names (e.g. `pi-main`) as candidates until uniquely verified; do not pretend a search hit is the intended repo.

2. **Search and structure first**
   - Use GitHub search queries across exact target, topic tags, domain keywords, parser/search tooling keywords.
   - Persist raw search evidence and normalized repo cards (`repo`, `url`, stars, category, source_query, HEAD, license, risk_level, absorbed_status).
   - Generate Markdown project cards; classify as candidate/active_review/verified_pattern/block, not “fully absorbed” after metadata only.

3. **Parse assets with honest fallback**
   - Preferred parser may be named by the user (e.g. LiteParse). First check availability.
   - If unavailable, use compatible local fallback (PDF: PyMuPDF/fitz; image: Pillow + Tesseract) and record the fallback fact in metadata.
   - Never claim the preferred parser ran unless the executable/package actually ran.

4. **Real multi-LLM audit**
   - Load configured providers and call each real API once on compact evidence.
   - GPT/Claude configured as `codex_responses` must use `/v1/responses` style payload (`model`, `instructions`, `input`, `max_output_tokens`), not chat completions.
   - Record provider, model, api_mode, HTTP status, output path, response hash; missing key = skipped, not participated.

5. **Automate briefings safely**
   - Create a self-contained script that runs search → card/wiki update → asset parse → LLM audit → manifest update → stdout brief.
   - Schedule morning/evening cron as `no_agent=true` when the script already produces the user-facing brief.
   - Make cron prompt/script self-contained because future runs do not inherit chat context.

6. **APEX/GeneDB boundary**
   - Update `EVOLUTION_MANIFEST.json` after the new workflow is installed.
   - Do not mutate Hermes core scheduler/security boundary for a knowledge radar task.
   - Do not call GitHub stars or external legal repos legal authority; Chinese legal authority remains the local official legal KB.

## Output contract

Report concise evidence fields:

- workspace path
- query count / repo card count / project card count
- top legal/political candidates
- parser status and fallback status
- LLM provider evidence with HTTP statuses and audit paths
- cron job IDs / schedules
- manifest update status
- truthful boundary: “continuous ingestion loop installed” vs “all repos fully understood”
